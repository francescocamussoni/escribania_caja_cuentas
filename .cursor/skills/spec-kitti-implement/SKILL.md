---
name: spec-kitti-implement
description: Execute autonomous code generation for a Work Unit using an Executor-Reviewer feedback loop until the code meets all quality standards. Use when implementing a specific Work Unit (e.g. WU-005).
disable-model-invocation: true
---

# Spec-Kitti Implement

Autonomous code generation with self-correction loop for a single Work Unit.

## When to Use

**Mode A — Work Unit (structured)**
- When you have a Work Unit ready in `.spec-kitti/work-units/[WU-ID].json`
- Invoke explicitly: `/spec-kitti-implement WU-005`

**Mode B — Direct task (conversational)**
- When the dev describes a task directly in the chat without a `.json` file
- Uses `.spec-kitti/tasks.md` as reference for context
- Same quality standards as Mode A — no shortcuts

## Instructions

### Before starting

Read in order:
1. `.spec-kitti/memory/constitution.md` — project principles (if exists)
2. `.spec-kitti/discovery/architecture.md` — layers and patterns **(only if `.spec-kitti/discovery/` exists — legacy/modernization projects)**
3. `.spec-kitti/discovery/modules.md` — module responsibilities **(only if `.spec-kitti/discovery/` exists — legacy/modernization projects)**
4. `.spec-kitti/plan.md` — tech stack and coding patterns
5. **For UI tasks** → `references/figma-ui-guide.md` — Figma MCP extraction and token mapping protocol

> **Greenfield projects** (new codebase): `.spec-kitti/discovery/` won't exist. Skip steps 2 and 3 — derive structure from `plan.md` and the Work Unit itself.

> **UI tasks**: A task is "UI" when its `file_path` targets `.tsx/.jsx/.vue/.svelte/.css/.scss` or subtasks mention components/layouts/styles. In that case, step 5 is mandatory.

> The detailed reading order for the executor is defined in `references/executor.md` — this is just the high-level checklist.

### Autonomous Loop (max 5 iterations)

1. **Executor** — follow `references/executor.md` to generate the code file
2. **Reviewer** — follow `references/reviewer.md` to validate the code
3. **Decision:**
   - `APPROVED` → go to **Mark Complete** step
   - `NEEDS_REVISION` → pass reviewer feedback to Executor, repeat
   - `REJECTED` → pass reviewer feedback to Executor, repeat
   - Max iterations reached → stop, report last review, do NOT mark complete

### Mark Complete (only on APPROVED)

1. Open `.spec-kitti/tasks.md`
2. Find the line containing the WU-ID (e.g. `WU-005`)
3. Replace `- [ ]` with `- [x]` on that line
4. Save the file

### Output

```
✅ [WU-ID] APPROVED — [file_path]
   Iterations: N
   tasks.md updated: [task description] marked as complete
```
