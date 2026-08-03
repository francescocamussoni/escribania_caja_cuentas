#!/usr/bin/env python3
"""
Discovery Graph Builder — Transforms raw_index.json into graph.json.

Produces two graph levels:
  file_level   — nodes are source files, edges are import relationships
  module_level — nodes are directory modules, edges are aggregated dependencies

No external dependencies required.
"""

import json
import sys
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timezone

# ── Helpers ───────────────────────────────────────────────────────────────────

def assign_module(file_path: str, modules: list[dict]) -> str:
    """Return the module name whose path is a prefix of file_path."""
    # Sort by path length descending → most-specific match first
    for module in sorted(modules, key=lambda m: -len(m["path"])):
        prefix = module["path"]
        if file_path.startswith(prefix + "/") or file_path == prefix:
            return module["name"]
    # Fallback: first directory component
    parts = Path(file_path).parts
    return parts[0] if len(parts) > 1 else "root"


def is_relative_import(import_str: str) -> bool:
    return import_str.startswith(".") or import_str.startswith("/")


def resolve_relative(from_file: str, import_str: str, file_set: set) -> str | None:
    """
    Attempt to resolve a relative import to an actual file in file_set.
    Returns the matching path or None.
    """
    from_dir = str(Path(from_file).parent)
    # Normalize: strip ./ prefix
    stripped = import_str.lstrip("./")

    # Try direct match with common extensions
    for ext in ("", ".ts", ".tsx", ".js", ".jsx", ".py", ".java", ".go", ".cs", ".rb"):
        candidate = stripped + ext
        # Try as absolute path from root
        if candidate in file_set:
            return candidate
        # Try relative from from_dir
        joined = str(Path(from_dir) / candidate)
        # Normalize path
        try:
            normalized = str(Path(joined))
        except Exception:
            continue
        if normalized in file_set:
            return normalized

    # Last resort: basename match
    basename = Path(stripped).name
    for candidate in file_set:
        if Path(candidate).stem == Path(basename).stem:
            return candidate

    return None


def infer_module_from_import(import_str: str, modules: list[dict]) -> str | None:
    """Try to match a non-relative import string to a module by name."""
    import_lower = import_str.lower().replace("/", ".").replace("\\", ".")
    for module in modules:
        if module["name"].lower() in import_lower:
            return module["name"]
    return None


# ── Build ─────────────────────────────────────────────────────────────────────

def build_graph(raw_index: dict) -> dict:
    file_tree: list[dict] = raw_index.get("file_tree", [])
    imports: list[dict] = raw_index.get("imports", [])
    modules: list[dict] = raw_index.get("modules", [])
    import_agg: dict = raw_index.get("import_aggregation", {})
    meta: dict = raw_index.get("meta", {})

    file_set = {f["path"] for f in file_tree}

    # ── File-level nodes ──────────────────────────────────────────────────────
    file_nodes = []
    for f in file_tree:
        file_nodes.append({
            "id": f["path"],
            "name": Path(f["path"]).stem,
            "module": assign_module(f["path"], modules),
            "type": f.get("type", "unknown"),
            "ext": f.get("ext", ""),
            "lines": f.get("lines", 0),
        })

    # ── File-level edges ──────────────────────────────────────────────────────
    file_edges: list[dict] = []
    seen_file_edges: set[tuple] = set()

    for imp in imports:
        from_file = imp["from"]
        import_str = imp["import"]

        if from_file not in file_set:
            continue

        target = None
        if is_relative_import(import_str):
            target = resolve_relative(from_file, import_str, file_set)
        # else: absolute imports rarely resolve to internal files without
        # a full module resolver — skip to keep the graph clean

        if target and target != from_file:
            key = (from_file, target)
            if key not in seen_file_edges:
                seen_file_edges.add(key)
                file_edges.append({
                    "from": from_file,
                    "to": target,
                    "type": "imports",
                })

    # ── Module-level nodes ────────────────────────────────────────────────────
    module_nodes = []
    module_name_set = {m["name"] for m in modules}

    for m in modules:
        # Type breakdown from file_tree
        type_counts: dict[str, int] = defaultdict(int)
        for f in file_tree:
            if assign_module(f["path"], modules) == m["name"]:
                type_counts[f.get("type", "unknown")] += 1

        module_nodes.append({
            "id": m["name"],
            "path": m["path"],
            "file_count": m.get("file_count", 0),
            "dominant_ext": m.get("dominant_ext", ""),
            "type_breakdown": dict(type_counts),
        })

    # ── Module-level edges ────────────────────────────────────────────────────
    # Source 1: aggregated from resolved file-level edges
    mod_edge_weight: dict[tuple, int] = defaultdict(int)

    for edge in file_edges:
        from_mod = assign_module(edge["from"], modules)
        to_mod = assign_module(edge["to"], modules)
        if from_mod != to_mod:
            mod_edge_weight[(from_mod, to_mod)] += 1

    # Source 2: non-relative imports matched to module names via import_agg
    # We know the import package but not the "from" module, so we add
    # semantic edges only when we can match both sides.
    for imp in imports:
        from_file = imp["from"]
        import_str = imp["import"]
        if is_relative_import(import_str):
            continue
        target_mod = infer_module_from_import(import_str, modules)
        if target_mod is None:
            continue
        from_mod = assign_module(from_file, modules)
        if from_mod != target_mod and from_mod in module_name_set and target_mod in module_name_set:
            mod_edge_weight[(from_mod, target_mod)] += 1

    module_edges = [
        {
            "from": from_mod,
            "to": to_mod,
            "weight": weight,
            "type": "depends_on",
        }
        for (from_mod, to_mod), weight
        in sorted(mod_edge_weight.items(), key=lambda x: -x[1])
        if from_mod in module_name_set and to_mod in module_name_set
    ]

    # ── External dependencies ─────────────────────────────────────────────────
    # Top entries from import_agg that don't match any internal module
    external_deps = []
    for pkg, count in list(import_agg.items())[:30]:
        pkg_lower = pkg.lower()
        if not any(m["name"].lower() in pkg_lower for m in modules):
            external_deps.append({"package": pkg, "usage_count": count})
        if len(external_deps) >= 20:
            break

    return {
        "meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "legacy_path": meta.get("legacy_path", ""),
            "graph_builder_version": "2.0.0",
            "source": "raw_index.json",
        },
        "file_level": {
            "nodes": file_nodes,
            "edges": file_edges,
            "stats": {
                "nodes": len(file_nodes),
                "edges": len(file_edges),
            },
        },
        "module_level": {
            "nodes": module_nodes,
            "edges": module_edges,
            "stats": {
                "nodes": len(module_nodes),
                "edges": len(module_edges),
            },
        },
        "external_dependencies": external_deps,
    }


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Discovery Graph Builder — builds file + module dependency graph"
    )
    parser.add_argument("--input", required=True, help="Path to raw_index.json")
    parser.add_argument("--output", required=True, help="Output path for graph.json")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        print(f"Error: input not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    with open(input_path, encoding="utf-8") as f:
        raw_index = json.load(f)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"  Input:  {input_path}")
    print(f"  Output: {output_path}")
    print()
    print("  Building graph...", flush=True)

    graph = build_graph(raw_index)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(graph, f, indent=2, ensure_ascii=False)

    fl = graph["file_level"]["stats"]
    ml = graph["module_level"]["stats"]

    print(
        f"  ✅ Done — "
        f"file level: {fl['nodes']} nodes / {fl['edges']} edges | "
        f"module level: {ml['nodes']} nodes / {ml['edges']} edges"
    )
    print(f"  Output: {output_path}")


if __name__ == "__main__":
    main()

