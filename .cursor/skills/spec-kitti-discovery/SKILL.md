---
name: spec-kitti-discovery
description: Legacy codebase discovery — runs indexer and graph builder (zero AI tokens), then generates modules.md, architecture.md, bounded-contexts.md, and bootstraps constitution.md. Use when starting a new project or analyzing a legacy codebase.
disable-model-invocation: false
---

# Spec-Kitti Discovery

Analyze a legacy codebase and generate architectural documentation.

## When to Use
- When you start working on a legacy project for the first time
- When `constitution.md` doesn't exist yet
- Invoked by `/spec-kitti.discovery`

## Constraints
- Do NOT read or modify application source code
- Be concise — no long explanations while working, only progress markers

## Instructions

Execute all phases in order.

### Phase 1 — Shell: Indexer (zero AI tokens)

```bash
bash scripts/spec-kitti-discovery-orchestrator.sh --legacy "$ARGUMENTS" --step index
```
Verify `.spec-kitti/discovery/raw_index.json` exists before continuing.

### Phase 2 — Shell: Graph Builder (zero AI tokens)

```bash
bash scripts/spec-kitti-discovery-orchestrator.sh --legacy "$ARGUMENTS" --step graph
```
Verify `.spec-kitti/discovery/graph.json` exists before continuing.

### Phase 3 — AI Analysis (in order)

1. Follow `references/modules-analysis.md` → `.spec-kitti/discovery/modules.md`
2. Follow `references/architecture-analysis.md` → `.spec-kitti/discovery/architecture.md`
3. Follow `references/contexts-analysis.md` → `.spec-kitti/discovery/bounded-contexts.md`
4. Follow `references/constitution-bootstrap.md` → `.spec-kitti/memory/constitution.md`

### Phase 4 — Done

```
✅ Discovery Complete
  raw_index.json       ✅
  graph.json           ✅
  modules.md           ✅
  architecture.md      ✅
  bounded-contexts.md  ✅
  memory/constitution.md ✅

Next: /spec-kitti.specify or /spec-kitti.plan
```
