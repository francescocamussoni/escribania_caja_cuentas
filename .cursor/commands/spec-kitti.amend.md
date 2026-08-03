---
description: Cascade synchronizer that propagates a new RFC / scope change across constitution, spec, plan and tasks without destroying executed work.
scripts:
  sh: .spec-kitti/scripts/bash/check-prerequisites.sh --json
  ps: scripts/powershell/check-prerequisites.ps1 -Json
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty). The input is either:

- A natural-language description of new requirements / scope changes, **or**
- A path to an updated RFC document (e.g. `docs/rfcs/RFC-014-orders-v2.md`).

If the input is empty: ERROR `"No amend payload provided. Pass new requirements text or a path to an updated RFC."`

## ⚠️ Scope Constraint

**This command ONLY produces planning / specification artifacts (`constitution.md`, `spec.md`, `plan.md`, `data-model.md`, `quickstart.md`, `research.md`, `tasks.md`, `task-status.json`). It MUST NOT generate, create, or modify any application source code files (e.g. `.ts`, `.py`, `.js`, `.java`, etc.). Source code changes derived from the amend are exclusively the responsibility of `/spec-kitti.implement` over the new/refactor tasks produced here.**

## What is `/spec-kitti.amend`?

A maintenance / evolutionary agent that runs on a feature **already initialized** with `constitution.md`, `spec.md`, `plan.md`, `tasks.md` and `task-status.json` (and optionally `data-model.md`, `quickstart.md`, `research.md`, `contracts/`). It analyzes a new requirement or RFC and updates **in cascade** every Spec-Driven Development document, guaranteeing total coherence **without destroying the work already executed by the team** (`done` / `in_progress` tasks are preserved).

It is **not** a replacement for `/spec-kitti.specify`, `/spec-kitti.plan` or `/spec-kitti.tasks`. Use it when the feature folder already exists and the scope changed.

## Outline

1. **Setup**: Run `{SCRIPT}` from repo root and parse `FEATURE_DIR` and `AVAILABLE_DOCS` list. All paths must be absolute. For single quotes in args like "I'm Groot", use escape syntax: e.g. `'I'\''m Groot'` (or double-quote if possible: `"I'm Groot"`).

2. **Pre-flight check** — abort if the feature is not initialized:
   - `FEATURE_DIR/spec.md` MUST exist → otherwise instruct user to run `/spec-kitti.specify` first.
   - `FEATURE_DIR/plan.md` MUST exist → otherwise instruct user to run `/spec-kitti.plan` first.
   - `FEATURE_DIR/tasks.md` MUST exist → otherwise instruct user to run `/spec-kitti.tasks` first.
   - If `FEATURE_DIR/task-status.json` does **not** exist, treat all tasks listed in `tasks.md` as `pending` for reconciliation purposes (and create the file at the end with the new state).

3. **Resolve the amend payload**:
   - If `$ARGUMENTS` is a filesystem path that exists, read it as the RFC source of truth.
   - Otherwise treat `$ARGUMENTS` as the inline new requirements text.

4. **Execute the three-phase cascade workflow described below**, in strict order: Phase 1 (Impact Analysis) → Phase 2 (Cascade Update) → Phase 3 (Smart Task Sync).

5. **Report**: Emit an **Amend Report** (see "Expected Output" below). Do **not** dump the full content of the modified files — only summarize what changed and where.

---

## Phase 1 — Impact Analysis (Internal Discovery)

1. Read carefully the user input (the new requirements or the updated RFC).
2. Read the current state of the following files (only the ones that exist):
   - `/memory/constitution.md`
   - `FEATURE_DIR/spec.md`
   - `FEATURE_DIR/plan.md`
   - `FEATURE_DIR/data-model.md` (if present)
   - `FEATURE_DIR/quickstart.md` (if present)
   - `FEATURE_DIR/research.md` (if present)
   - `FEATURE_DIR/contracts/` (if present)
   - `FEATURE_DIR/tasks.md`
   - `FEATURE_DIR/task-status.json` (if present)
3. Determine **exactly which layers are affected**, classifying impact into these buckets (a single amend may hit several):

   | Layer | Trigger | Target file(s) |
   |-------|---------|----------------|
   | Constitution | Change in global stack, conventions, non-negotiable principles | `/memory/constitution.md` |
   | Spec | Change in business rules, use cases, acceptance criteria, NFRs | `FEATURE_DIR/spec.md` |
   | Plan | Change in architecture, DB schema, API contracts, tech decisions | `FEATURE_DIR/plan.md` (+ `data-model.md`, `quickstart.md`, `research.md`, `contracts/`) |
   | Tasks | Any of the above produces new / modified / obsolete tasks | `FEATURE_DIR/tasks.md` (+ `task-status.json`) |

4. Produce an internal **Impact Matrix** (kept in working memory, surfaced in the final report) listing for each affected layer the specific deltas (added / modified / removed concepts).

> **CRITICAL:** Only modify the layers that the impact analysis flagged. Do not "refresh" untouched documents. Coherence is preserved by surgical edits, not by regeneration.

---

## Phase 2 — Cascade Update

Apply the changes **sequentially** to the affected files only, respecting these rules:

### 2.1 Constitution (`/memory/constitution.md`)

- Update **only** if the amend changes conventions, standards or the base technology stack.
- When updated, bump `CONSTITUTION_VERSION` per semver (MAJOR/MINOR/PATCH) and prepend a Sync Impact Report HTML comment, exactly as `/spec-kitti.constitution` does.
- **Never** silently rewrite principles unrelated to the amend.

### 2.2 Spec (`FEATURE_DIR/spec.md`)

- Integrate the amend into use cases, acceptance criteria and non-functional requirements.
- **DO NOT delete functionality that was not mentioned in the amend** — only integrate the changes.
- For new / modified user stories, preserve the existing priority labeling (P1, P2, P3...) and add new stories at the next available priority slot if the RFC explicitly introduces them.
- If the amend introduces ambiguity, mark with `[NEEDS CLARIFICATION: ...]` (max 3 markers, same rule as `/spec-kitti.specify`).
- Update the `## Assumptions` and `## Success Criteria` sections if the RFC moves the goalposts.

### 2.3 Plan (`FEATURE_DIR/plan.md` + sibling artifacts)

- Adjust architecture, DB schema and API contracts to match the new spec.
- Maintain coherence end-to-end. **Examples of mandatory propagation:**
  - If the amend adds a field on the spec → it MUST appear in `data-model.md` and (if applicable) in `contracts/`.
  - If the amend changes a tech choice → reflect it in plan's Technical Context **and** in `research.md` (with Decision / Rationale / Alternatives considered).
  - If the amend adds an endpoint → reflect it in `contracts/` and in `quickstart.md` walkthroughs.
- Re-evaluate the **Constitution Check** gate. If the amend introduces a violation, either justify it explicitly in plan.md's "Complexity Tracking" section or block with an `ERROR` instructing the user to revisit the RFC.

---

## Phase 3 — Smart Task Sync — ⚠️ CRITICAL

You MUST update `tasks.md` and `task-status.json` under these **non-negotiable rules**:

### 3.1 Read first, mutate second

- Read `tasks.md` and `task-status.json` **completely** before writing anything.
- Build an in-memory map: `{ taskId → { status, description, file_paths } }` using `task-status.json` as the source of truth for status; if status is missing, infer `done` from `- [x]` checkboxes in `tasks.md`, otherwise `pending`.

### 3.2 Do NOT destroy history

- Tasks with status `done` or `in_progress` MUST NOT be deleted nor destructively modified in `tasks.md`.
- Their checkbox state (`- [x]` / `- [ ]`), ID, label and description must remain intact.
- Their entry in `task-status.json` must remain intact (status, timestamps, executor metadata).

### 3.3 Pending tasks

- If a `pending` task is **affected** by the amend → modify its description / file paths to reflect the new requirements (keep the same ID).
- If a `pending` task is rendered **obsolete** by the amend → remove it from `tasks.md` AND from `task-status.json`. Log it in the Amend Report under "Eliminated".

### 3.4 New tasks

- Add new tasks to cover the new requirements introduced by the amend.
- **Numbering rule:** continue from the highest existing task ID. If the last task is `T028`, new tasks start at `T029`. **Never** reuse a retired ID.
- Place new tasks inside the correct phase (Setup / Foundational / per User Story / Polish) and respect the Checklist Format documented in `/spec-kitti.tasks`:
  ```text
  - [ ] [TaskID] [P?] [Story?] Description with file path
  ```
- Mirror them in `task-status.json` with status `pending`.

### 3.5 Refactors (the complex case)

- If the amend alters functionality covered by a task already in status `done`:
  - **DO NOT modify** the original task. Its history is sacred.
  - **Create a NEW task** describing the refactor, with the prefix `[Refactor]` in its description and an explicit reference to the amended RFC and to the original task ID. Example:
    ```text
    - [ ] T030 [US1] [Refactor] Update user lookup logic per RFC-014 amend (modifies T012)
    ```
  - Numbering follows the same continuation rule (3.4).
  - Mirror in `task-status.json` with status `pending` and a `refactor_of: "T012"` field.

### 3.6 Coherence after writing

- After writing, re-read `tasks.md` and `task-status.json` and validate:
  - All IDs are unique and monotonically ordered.
  - Every task in `tasks.md` has a row in `task-status.json` and vice-versa.
  - No `done` / `in_progress` task was rewritten.
  - Phase headers, dependency section and parallel execution examples still reflect reality.

---

## Expected Output — "Amend Report"

When you finish, **DO NOT** return the full content of the modified files. Return a **Markdown report** with this exact shape:

```markdown
# 📜 Amend Report — `<feature-id>`

**Source of amend:** <inline text | path to RFC>
**Date:** <YYYY-MM-DD>

## 📝 Modified files

- `/memory/constitution.md` (if applicable, with version bump X.Y.Z → X'.Y'.Z')
- `specs/<feature>/spec.md`
- `specs/<feature>/plan.md`
- `specs/<feature>/data-model.md` (if applicable)
- `specs/<feature>/contracts/<file>` (if applicable)
- `specs/<feature>/tasks.md`
- `specs/<feature>/task-status.json`

## 🎯 Business / Architecture decisions

- **Spec:** <summary of changes integrated into spec.md>
- **Plan:** <summary of changes integrated into plan.md / data-model / contracts>
- **Constitution (if touched):** <what convention or stack rule changed>

## ✅ Task impact

- 🆕 New tasks added: **N** (IDs: Txxx, Txxx, ...)
- ✏️  Pending tasks modified: **N** (IDs: Txxx, Txxx, ...)
- 🗑️  Obsolete pending tasks removed: **N** (IDs: Txxx, Txxx, ...)
- 🛠️  Refactor tasks created (against `done` work): **N** (IDs: Txxx → refactor_of Txxx, ...)
- 🔒 Preserved untouched (`done` / `in_progress`): **N**

## ⚠️ Open items

- <Any [NEEDS CLARIFICATION] markers remaining in spec.md>
- <Any constitution gate violations the user must resolve>
- <Suggested next command (typically `/spec-kitti.implement <next-task-id>`)>
```

The report **MUST** be the only thing the user sees as response. Do not paste full file contents.

---

## Non-negotiable rules

- **Never** regenerate `tasks.md` from scratch. Mutate it surgically.
- **Never** rewrite tasks whose status is `done` or `in_progress`. Use `[Refactor]` tasks instead.
- **Never** silently change constitution principles unrelated to the amend.
- **Never** drop spec functionality that the amend did not explicitly remove.
- **Always** keep `tasks.md` and `task-status.json` in lockstep (1:1 mapping by ID).
- **Always** continue task numbering from the highest existing ID — IDs are immutable identifiers, not slots.
- **Always** emit an Amend Report; never dump full files.
