#!/usr/bin/env python3
"""
Discovery Indexer — Zero-AI structural scan of a legacy codebase.

Outputs raw_index.json with:
  - tech_stack  (languages, manifests, framework hints, confidence)
  - file_tree   (path, ext, lines, size_kb, type, dir)
  - imports     (from → import_str, capped at MAX_IMPORTS)
  - import_aggregation  (root package → usage count, top 100)
  - modules     (directory-based detection)
  - naming_patterns (type → count)
  - stats

No external dependencies required.
"""

import os
import sys
import re
import json
import subprocess
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timezone

# ── Constants ─────────────────────────────────────────────────────────────────

MAX_IMPORTS = 10_000   # cap to avoid huge files on massive repos
MAX_FILE_TREE = 50_000

EXCLUDE_DIRS = {
    "node_modules", ".git", ".svn", "target", "build", "dist", "out",
    "__pycache__", ".venv", "venv", "env", "vendor", "coverage",
    ".nyc_output", ".next", ".nuxt", ".pytest_cache", ".eggs",
    "htmlcov", ".tox", "bower_components", ".gradle", ".mvn",
    ".idea", ".vscode", ".DS_Store",
}

# Language → (extensions, import_regex, root_depth)
# root_depth: how many segments to keep for aggregation key
LANG_IMPORT_RULES = {
    "java": {
        "extensions": {".java", ".kt", ".scala"},
        "pattern": re.compile(r"^import\s+([\w.]+)\s*;", re.MULTILINE),
        "root_depth": 3,
    },
    "python": {
        "extensions": {".py"},
        "pattern": re.compile(r"^(?:from\s+(\S+)\s+import|import\s+(\S+))", re.MULTILINE),
        "root_depth": 2,
    },
    "typescript": {
        "extensions": {".ts", ".tsx"},
        "pattern": re.compile(r"""(?:from|import)\s+['"]([^'"]+)['"]|require\s*\(\s*['"]([^'"]+)['"]\s*\)"""),
        "root_depth": 1,
    },
    "javascript": {
        "extensions": {".js", ".jsx", ".mjs"},
        "pattern": re.compile(r"""(?:from|import)\s+['"]([^'"]+)['"]|require\s*\(\s*['"]([^'"]+)['"]\s*\)"""),
        "root_depth": 1,
    },
    "go": {
        "extensions": {".go"},
        "pattern": re.compile(r'"([\w./\-]+)"'),
        "root_depth": 2,
    },
    "csharp": {
        "extensions": {".cs"},
        "pattern": re.compile(r"^using\s+([\w.]+)\s*;", re.MULTILINE),
        "root_depth": 2,
    },
    "php": {
        "extensions": {".php"},
        "pattern": re.compile(r"^use\s+([\w\\]+)\s*;", re.MULTILINE),
        "root_depth": 2,
    },
    "ruby": {
        "extensions": {".rb"},
        "pattern": re.compile(r"""require(?:_relative)?\s+['"]([^'"]+)['"]"""),
        "root_depth": 1,
    },
}

# Extension → language name (for counting)
EXT_TO_LANG = {
    ".java": "java", ".kt": "kotlin", ".scala": "scala",
    ".py": "python",
    ".ts": "typescript", ".tsx": "typescript",
    ".js": "javascript", ".jsx": "javascript", ".mjs": "javascript",
    ".go": "go",
    ".cs": "csharp",
    ".php": "php",
    ".rb": "ruby",
    ".rs": "rust",
    ".swift": "swift",
    ".cpp": "cpp", ".cc": "cpp", ".cxx": "cpp",
    ".c": "c", ".h": "c",
}

ALL_CODE_EXTENSIONS = set(EXT_TO_LANG.keys())

MANIFEST_NAMES = [
    "package.json", "pom.xml", "build.gradle", "build.gradle.kts",
    "requirements.txt", "pyproject.toml", "setup.py", "go.mod",
    "Gemfile", "composer.json", "Cargo.toml", "build.sbt",
    "mix.exs", "go.sum",
]

# Naming conventions → node type
NAMING_TYPE_RULES = [
    (re.compile(r"(?:controller|router|resource|handler|endpoint)", re.IGNORECASE), "controller"),
    (re.compile(r"(?:service|usecase|use_case|interactor|business)", re.IGNORECASE), "service"),
    (re.compile(r"(?:repository|repo|dao|store|gateway|persistence)", re.IGNORECASE), "repository"),
    (re.compile(r"(?:entity|model|domain|schema|dto|record)", re.IGNORECASE), "entity"),
    (re.compile(r"(?:config|configuration|settings|properties)", re.IGNORECASE), "config"),
    (re.compile(r"(?:test|spec|_test|test_)", re.IGNORECASE), "test"),
]
ENTRY_POINT_NAMES = {"main", "index", "app", "application", "bootstrap", "server", "startup"}

FRAMEWORK_SIGNATURES = {
    "spring-boot":  ["org.springframework"],
    "hibernate":    ["org.hibernate"],
    "jakarta-ee":   ["jakarta.", "javax."],
    "django":       ["django"],
    "flask":        ["flask"],
    "fastapi":      ["fastapi"],
    "express":      ["express"],
    "nestjs":       ["@nestjs"],
    "react":        ["react"],
    "angular":      ["@angular"],
    "vue":          ["vue"],
    "gin":          ["github.com/gin-gonic"],
    "echo":         ["github.com/labstack/echo"],
    "sqlalchemy":   ["sqlalchemy"],
    "typeorm":      ["typeorm"],
    "prisma":       ["@prisma"],
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def should_exclude(path: Path, base: Path) -> bool:
    try:
        rel = path.relative_to(base)
        return any(part in EXCLUDE_DIRS or part.startswith(".") for part in rel.parts)
    except ValueError:
        return True


def detect_node_type(stem: str) -> str:
    stem_lower = stem.lower()
    if stem_lower in ENTRY_POINT_NAMES:
        return "entry_point"
    for pattern, type_name in NAMING_TYPE_RULES:
        if pattern.search(stem):
            return type_name
    return "unknown"


def get_root_key(import_str: str, depth: int) -> str:
    """Keep only the first `depth` segments of a dotted/slashed import."""
    normalized = import_str.replace("\\", "/").replace("/", ".")
    parts = [p for p in normalized.split(".") if p]
    return ".".join(parts[:depth]) if parts else import_str


def count_lines_fast(path: Path) -> int:
    try:
        with open(path, "rb") as f:
            return f.read().count(b"\n")
    except Exception:
        return 0


def rg_available() -> bool:
    return subprocess.run(["which", "rg"], capture_output=True).returncode == 0


# ── Main scan ─────────────────────────────────────────────────────────────────

def scan(legacy_path: Path, verbose: bool = False) -> dict:

    # ── 1. Walk the whole tree once ──────────────────────────────────────────
    print("  [1/6] Walking file tree...", flush=True)

    lang_counts: dict[str, int] = defaultdict(int)
    all_files: list[Path] = []

    for root, dirs, files in os.walk(legacy_path):
        root_p = Path(root)
        # Prune excluded dirs in-place
        dirs[:] = [
            d for d in dirs
            if d not in EXCLUDE_DIRS and not d.startswith(".")
        ]
        for fname in files:
            fp = root_p / fname
            ext = fp.suffix.lower()
            if ext in EXT_TO_LANG:
                lang_counts[EXT_TO_LANG[ext]] += 1
            all_files.append(fp)

    languages = [
        {"lang": lang, "files": count}
        for lang, count in sorted(lang_counts.items(), key=lambda x: -x[1])
        if count >= 3
    ]
    detected_langs = {l["lang"] for l in languages}

    print(f"     ✓ Languages: {', '.join(l['lang'] for l in languages) or 'none detected'}", flush=True)

    # ── 2. Manifest files ────────────────────────────────────────────────────
    print("  [2/6] Finding manifests...", flush=True)

    manifests = []
    manifest_set = set(MANIFEST_NAMES)
    for fp in all_files:
        if fp.name in manifest_set and not should_exclude(fp, legacy_path):
            manifests.append({"name": fp.name, "path": str(fp)})
            manifest_set.discard(fp.name)   # one per manifest type

    print(f"     ✓ Manifests: {len(manifests)} found", flush=True)

    # ── 3. File tree ─────────────────────────────────────────────────────────
    print("  [3/6] Building file tree...", flush=True)

    file_tree = []
    for fp in all_files:
        if len(file_tree) >= MAX_FILE_TREE:
            break
        if fp.suffix.lower() not in ALL_CODE_EXTENSIONS:
            continue
        if should_exclude(fp, legacy_path):
            continue
        try:
            rel = str(fp.relative_to(legacy_path))
            lines = count_lines_fast(fp)
            size_kb = fp.stat().st_size // 1024
            node_type = detect_node_type(fp.stem)
            dir_path = str(fp.parent.relative_to(legacy_path)) if fp.parent != legacy_path else "."
            file_tree.append({
                "path": rel,
                "ext": fp.suffix.lstrip(".").lower(),
                "lines": lines,
                "size_kb": size_kb,
                "type": node_type,
                "dir": dir_path,
            })
        except Exception:
            pass

    print(f"     ✓ Files: {len(file_tree)}", flush=True)

    # ── 4. Import extraction ─────────────────────────────────────────────────
    print("  [4/6] Extracting imports...", flush=True)

    # Build a lookup: extension → lang rule
    ext_to_rule: dict[str, dict] = {}
    for lang_name, rule in LANG_IMPORT_RULES.items():
        for ext in rule["extensions"]:
            # Only process languages actually detected (or all if none detected)
            lang_family = lang_name
            if lang_name in ("typescript", "javascript"):
                lang_family = "typescript" if "typescript" in detected_langs else "javascript"
            if detected_langs and lang_family not in detected_langs:
                # Also handle java covering kotlin/scala
                if lang_name == "java" and not any(
                    l in detected_langs for l in ("java", "kotlin", "scala")
                ):
                    continue
                elif lang_name not in ("java",):
                    continue
            ext_to_rule[ext] = rule

    imports: list[dict] = []
    import_agg: dict[str, int] = defaultdict(int)

    for file_info in file_tree:
        if len(imports) >= MAX_IMPORTS:
            break
        ext = "." + file_info["ext"]
        rule = ext_to_rule.get(ext)
        if rule is None:
            continue

        fp = legacy_path / file_info["path"]
        try:
            content = fp.read_text(encoding="utf-8", errors="ignore")
            for match in rule["pattern"].finditer(content):
                import_str = next((g for g in match.groups() if g), None)
                if not import_str or len(import_str) <= 1:
                    continue
                imports.append({"from": file_info["path"], "import": import_str})
                root_key = get_root_key(import_str, rule["root_depth"])
                import_agg[root_key] += 1
                if len(imports) >= MAX_IMPORTS:
                    break
        except Exception:
            pass

    # Top 100 by frequency
    top_agg = dict(sorted(import_agg.items(), key=lambda x: -x[1])[:100])

    print(f"     ✓ Import relationships: {len(imports)}", flush=True)

    # ── 5. Module detection (directory-based) ─────────────────────────────────
    print("  [5/6] Detecting modules...", flush=True)

    src_roots = []
    for candidate in ("src", "app", "lib", "source", "main"):
        candidate_path = legacy_path / candidate
        if candidate_path.is_dir():
            cnt = sum(1 for _ in candidate_path.rglob("*") if _.is_file())
            if cnt > 5:
                src_roots.append(candidate)
    if not src_roots:
        src_roots = ["."]

    modules = []
    seen_module_names: set[str] = set()

    for src_root in src_roots:
        base = legacy_path / src_root if src_root != "." else legacy_path
        try:
            children = sorted(base.iterdir())
        except Exception:
            continue
        for child in children:
            if not child.is_dir():
                continue
            if child.name in EXCLUDE_DIRS or child.name.startswith("."):
                continue
            if child.name in seen_module_names:
                continue
            seen_module_names.add(child.name)

            file_count = sum(1 for _ in child.rglob("*") if _.is_file())
            rel_path = str(child.relative_to(legacy_path))

            # Dominant extension
            sub_ext_counts: dict[str, int] = defaultdict(int)
            for f in child.rglob("*"):
                if f.is_file():
                    sub_ext_counts[f.suffix.lower()] += 1
            dominant_ext = (
                max(sub_ext_counts, key=sub_ext_counts.get).lstrip(".")
                if sub_ext_counts else ""
            )

            modules.append({
                "name": child.name,
                "path": rel_path,
                "file_count": file_count,
                "dominant_ext": dominant_ext,
            })

    print(f"     ✓ Modules: {len(modules)}", flush=True)

    # ── 6. Naming patterns & framework hints ──────────────────────────────────
    print("  [6/6] Analyzing patterns...", flush=True)

    naming_patterns: dict[str, int] = defaultdict(int)
    for f in file_tree:
        naming_patterns[f["type"]] += 1

    framework_hints = []
    for framework, signatures in FRAMEWORK_SIGNATURES.items():
        for sig in signatures:
            if any(sig in k for k in top_agg):
                framework_hints.append(framework)
                break

    confidence = "declared" if manifests else "inferred"

    # ── Assemble output ───────────────────────────────────────────────────────
    return {
        "meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "legacy_path": str(legacy_path),
            "indexer_version": "2.0.0",
            "tech_stack": {
                "languages": languages,
                "framework_hints": framework_hints,
                "manifest_files": manifests,
                "confidence": confidence,
            },
        },
        "file_tree": file_tree,
        "imports": imports,
        "import_aggregation": top_agg,
        "modules": modules,
        "naming_patterns": dict(naming_patterns),
        "stats": {
            "total_files": len(file_tree),
            "total_imports": len(imports),
            "total_modules": len(modules),
        },
    }


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(
        description="Discovery Indexer — zero-AI structural scan"
    )
    parser.add_argument("--legacy", required=True, help="Path to legacy codebase root")
    parser.add_argument("--output", required=True, help="Output path for raw_index.json")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    legacy_path = Path(args.legacy).resolve()
    output_path = Path(args.output)

    if not legacy_path.is_dir():
        print(f"Error: legacy path not found: {legacy_path}", file=sys.stderr)
        sys.exit(1)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"  Legacy: {legacy_path}")
    print(f"  Output: {output_path}")
    print()

    result = scan(legacy_path, verbose=args.verbose)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    s = result["stats"]
    print()
    print(
        f"  ✅ Done — {s['total_files']} files · "
        f"{s['total_modules']} modules · "
        f"{s['total_imports']} imports"
    )
    print(f"  Output: {output_path}")


if __name__ == "__main__":
    main()

