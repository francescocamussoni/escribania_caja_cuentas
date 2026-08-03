---
description: Legacy codebase discovery — generates modules.md, architecture.md, bounded-contexts.md, graph.json, and bootstraps memory/constitution.md
scripts:
  sh: .cursor/skills/spec-kitti-discovery/scripts/spec-kitti-discovery-orchestrator.sh
  ps: .cursor/skills/spec-kitti-discovery/scripts/spec-kitti-discovery-orchestrator.ps1
---

## User Input

```text
$ARGUMENTS
```

## ⚠️ Scope Constraint

Do **not** read, create, or modify any application source code (`.ts`, `.py`, `.java`, `.js`, `.go`, `.cs`, etc.).

**Be concise.** No long explanations while working — only print progress markers and the final summary.

---

## Execution Flow

Execute **all phases in order**. Do not skip any phase.

---

### Phase 1 — Shell: Indexer (zero AI tokens)

```bash
bash .cursor/skills/spec-kitti-discovery/scripts/spec-kitti-discovery-orchestrator.sh --legacy "$ARGUMENTS" --step index
```

Verify `.spec-kitti/discovery/raw_index.json` exists before continuing.

---

### Phase 2 — Shell: Graph Builder (zero AI tokens)

```bash
bash .cursor/skills/spec-kitti-discovery/scripts/spec-kitti-discovery-orchestrator.sh --legacy "$ARGUMENTS" --step graph
```

Verify `.spec-kitti/discovery/graph.json` exists before continuing.

---

### Phase 3 — AI Analysis

Execute in order. Each step depends on the previous output.

#### Step 1 — Modules
Follow `.cursor/skills/spec-kitti-discovery/references/modules-analysis.md`
→ Output: `.spec-kitti/discovery/modules.md`

#### Step 2 — Architecture
Follow `.cursor/skills/spec-kitti-discovery/references/architecture-analysis.md`
→ Output: `.spec-kitti/discovery/architecture.md`

#### Step 3 — Bounded Contexts
Follow `.cursor/skills/spec-kitti-discovery/references/contexts-analysis.md`
→ Output: `.spec-kitti/discovery/bounded-contexts.md`

#### Step 4 — Constitution
Follow `.cursor/skills/spec-kitti-discovery/references/constitution-bootstrap.md`
→ Output: `.spec-kitti/memory/constitution.md` (create if not exists, update `## Codebase` section if exists)

---

### Phase 4 — Summary

```
╔══════════════════════════════════════════════════════════╗
║  ✅ Discovery Complete                                   ║
╚══════════════════════════════════════════════════════════╝

  discovery/raw_index.json      ✅
  discovery/graph.json          ✅
  discovery/modules.md          ✅
  discovery/architecture.md     ✅
  discovery/bounded-contexts.md ✅
  memory/constitution.md        ✅

Next:
  /spec-kitti.specify   — write a feature spec
  /spec-kitti.plan      — plan the implementation
```

---

## Error Handling

- Phase 1 or 2 fails → stop, report error, do not continue.
- Any output file empty or malformed → re-execute that step.
- `raw_index.json` has 0 files → warn that the legacy path may be empty or incorrect.
