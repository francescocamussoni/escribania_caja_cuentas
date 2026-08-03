# Skill: Discovery — Analyze Modules

## Purpose
Analyze `raw_index.json` and produce a human-readable `modules.md` that documents every detected module.

## Input
- `.spec-kitti/discovery/raw_index.json`

## Output
- `.spec-kitti/discovery/modules.md`

## Instructions

Read `raw_index.json` and for each entry in `modules[]`:

### 1. Identify module responsibility
Infer the module's single responsibility from:
- Directory name (`src/api`, `src/retrieval`, `src/shared`, etc.)
- File `type` distribution in `file_tree[]` (controller, service, entity, config, entry_point)
- Top imports in `import_aggregation` scoped to files in that module path

### 2. List key files
From `file_tree[]`, filter files whose `dir` starts with the module path.
For each file with a non-`unknown` type, or files with ≥ 100 lines, document:
- File name and type
- Purpose (infer from name: `*_service` = business logic, `*_router` = HTTP, `*_client` = external call, etc.)

### 3. External dependencies
From `import_aggregation`, list the top third-party packages used by files in this module.
Exclude stdlib (os, sys, re, json, typing, etc.).

### 4. Internal coupling
From `imports[]`, identify which OTHER modules this module depends on.
(imports whose string matches another module's path prefix)

## Output Format

```markdown
# Modules — [project name]

> Discovery generated: [date]
> Tech stack: [from meta.tech_stack]

---

## Module Inventory

| Module | Path | Files | Role |
|--------|------|-------|------|
| ...    | ...  | ...   | ...  |

---

## Module: `[name]`

**Role:** [single sentence]

**Key files:**
- `file.py` — [purpose]

**External deps:** [package list]

**Depends on:** [other modules]

---
[repeat per module]
```

## Constraints
- Do NOT read any source code file — use only `raw_index.json`
- Module role must be inferred from structure, not invented
- Keep each module description under 10 lines
- Be concise — bullet points only, no prose paragraphs

