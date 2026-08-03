---
description: Focused refactor on existing code — no architecture changes, no strategic planning. Can work from spec.md pending items (bugs, stories, subtasks) or from direct user input. Reads constitution.md, scopes the change, proposes a solution for confirmation, then executes with the Executor→Reviewer loop.
---

## User Input

```text
$ARGUMENTS
```

## Purpose

This command handles **bounded, tactical changes** on existing code: bug fixes, simple stories, subtasks, renames, test improvements, dependency updates, or targeted implementation swaps.

It never touches architecture and never requires strategic planning. The constitution is treated as read-only — principles are inherited, not re-negotiated.

Internally the command runs the same Executor→Reviewer loop as `/spec-kitti.implement`, but without the ceremony of `/specify → /plan → /tasks`. All of that happens inline.

---

## ⚠️ Scope Guard

**This command MUST NOT be used when:**

- The change requires adding new business logic not already present
- The change crosses bounded-context boundaries
- The change modifies the public API surface (new endpoints, changed contracts)
- Architecture decisions need to be made
- Story points > 3 or the item description implies significant complexity

If any of the above is true, stop and redirect to `/spec-kitti.specify`.

---

## Execution Flow

### Step 0a — Load Constitution (read-only)

```
If .spec-kitti/memory/constitution.md exists:
    Read it silently.
    Do NOT modify it.
    All decisions in this command must respect it.

If it does not exist:
    Continue — no constitution constraint applies.
```

Print: `✅ Constitution loaded (read-only)` or `⚠️ No constitution found — proceeding unconstrained`

---

### Step 0b — Detect Pending Items in spec.md

Scan all `specs/*/spec.md` files for pending items — unchecked entries tagged as `[BUG]`, `[STORY]`, or `[TASK]`.

**If pending items are found AND `$ARGUMENTS` is empty:**

Present them to the user:

```
┌─────────────────────────────────────────────────────────────────┐
│  Ítems pendientes en spec.md                                    │
├──────┬────────┬──────────────────────────────────────┬──────────┤
│  #   │  Tipo  │  Título                              │  Points  │
├──────┼────────┼──────────────────────────────────────┼──────────┤
│  1   │  BUG   │  PROJ-456 — Modal no cierra con ESC  │  1pt     │
│  2   │  STORY │  PROJ-458 — Agregar tooltip en botón │  2pt     │
│  3   │  TASK  │  PROJ-461 — Actualizar copy del form │  1pt     │
└──────┴────────┴──────────────────────────────────────┴──────────┘

¿Sobre cuál querés trabajar? (1/2/3 o describí uno nuevo)
```

Wait for user selection before continuing.

**If the user selects an item from spec.md:**
→ Pre-load scope from the spec item (skip Step 1 questions — scope is already defined).

**If `$ARGUMENTS` is provided:**
→ Skip this step and go directly to Step 1.

**If no `spec.md` files exist and `$ARGUMENTS` is empty:**

Print the following and stop — do not proceed:

```
No se encontraron archivos spec.md en el proyecto.

  Sincronizar desde Jira:   /spec-kitti.sync --epic-key PROJ-123
  Planificar algo nuevo:    /spec-kitti.specify [descripción]
  Cambio directo:           /spec-kitti.refactor [descripción del cambio]
```

**If no pending items are found (spec.md exists but has no unchecked items) and `$ARGUMENTS` is empty:**
→ Go to Step 1 and ask the user to describe the change.

---

### Step 1 — Scope Definition

**If scope was pre-loaded from spec.md (Step 0b):**

Extract from the selected spec item:

| Field | Source in spec.md |
|-------|-------------------|
| `item_type` | Tag: `BUG`, `STORY`, or `TASK` |
| `jira_key` | Jira reference (e.g. `PROJ-456`) if present |
| `description` | Title + description of the item |
| `acceptance_criteria` | Checklist items under the spec entry |
| `restrictions` | Inferred from acceptance criteria (what must NOT change) |

**If scope comes from `$ARGUMENTS`:**

Parse and extract:

| Field | Description |
|-------|-------------|
| `change_type` | One of: `bug-fix`, `rename`, `test-improvement`, `implementation-swap`, `dependency-update`, `other` |
| `target` | File(s), function(s), class(es), or dependency name(s) affected |
| `description` | What exactly changes and why |
| `restrictions` | What MUST NOT change (interfaces, signatures, behavior, etc.) |

If `$ARGUMENTS` is empty or ambiguous and no spec items exist, ask:

```
Necesito un poco más de contexto para acotar el cambio de forma segura:

1. ¿Qué cambia exactamente? (ej: rename `getUserById` → `findUserById` en users.service.ts)
2. ¿Qué NO debe cambiar? (ej: interfaz pública, tipos de retorno, tests)
3. ¿Por qué se hace este cambio? (opcional — ayuda al Reviewer a validar la intención)
```

Do not proceed until scope is clear.

---

### Step 2 — Impact Map (diff-first planning)

Before writing any code, produce a compact impact map:

```
╔══════════════════════════════════════════════════════╗
║  REFACTOR SCOPE                                      ║
╚══════════════════════════════════════════════════════╝

  Tipo:          [item_type / change_type]
  Ítem:          [jira_key — description]
  Descripción:   [what changes and why]

  Archivos afectados:
    MODIFY  [file_path_1]  — [what changes]
    MODIFY  [file_path_2]  — [what changes]
    (SKIP   [file_path_3]  — [why untouched])

  Restricciones:
    • [restriction_1]
    • [restriction_2]

  Criterios de aceptación:
    • [acceptance_criterion_1]
    • [acceptance_criterion_2]

  Constraints de constitution:
    • [principle from constitution.md, if any]
```

List ONLY files that will be touched. If uncertain, err on the side of fewer files and flag it.

---

### Step 2b — Solution Proposal (requires explicit confirmation)

Before executing any code, present the proposed solution in natural language and **wait for explicit user confirmation**:

```
╔══════════════════════════════════════════════════════╗
║  PROPUESTA DE SOLUCIÓN — [jira_key / change_type]   ║
╚══════════════════════════════════════════════════════╝

  Ítem:   [description]

  Causa probable / Razón del cambio:
    [Diagnosis or rationale — what is wrong or why the change is needed]

  Solución propuesta:
    1. [First concrete action]
    2. [Second concrete action]
    3. [...]

  Archivos:
    MODIFY  [file_path_1]  — [specific change]
    MODIFY  [file_path_2]  — [specific change]

  Restricciones respetadas:
    • [restriction_1]
    • [restriction_2]

  ¿Procedemos con esta solución? [s/n o describí ajustes]
```

**User response handling:**

- `s` / enter → proceed to Step 3 with this proposal
- `n [feedback]` → revise the proposal and show Step 2b again (do not execute)
- `[custom description]` → incorporate the user's correction, show updated Step 2b, wait again

Do NOT proceed to Step 3 until the user explicitly confirms.

---

### Step 3 — Implementation (Spec-Kitti Implementation Orchestrator)

Invoke the same orchestrator used by `/spec-kitti.implement`, following the skill at `.cursor/skills/spec-kitti-implement/references/executor.md` and `.cursor/skills/spec-kitti-implement/references/reviewer.md`.

The refactor scope (impact map + confirmed solution proposal) acts as the Work Unit. There is no `work-units.json` — the scope defined in Steps 1–2b replaces it entirely.

```
Confirmed solution proposal
         ↓
┌──────────────────────────────────────────────────┐
│  Spec-Kitti Implementation Orchestrator          │
│  (Autonomous Correction Loop)                    │
└──────────────────────────────────────────────────┘
         ↓
   [ITERATION 1]
         ↓
    Executor Agent
    (Applies change from confirmed proposal)
         ↓
    Reviewer Agent
    (Validates against scope, restrictions, acceptance criteria, constitution)
         ↓
    APPROVED / NEEDS_REVISION / REJECTED
```

#### Agent 1: Executor Agent

**Skill**: `.cursor/skills/spec-kitti-implement/references/executor.md`

**Reads before every iteration:**
- `.spec-kitti/memory/constitution.md` (architectural context — read-only)
- `.spec-kitti/discovery/architecture.md` (if exists — layer compliance)
- Current state of each file in the impact map
- Confirmed solution proposal from Step 2b
- Review feedback from previous iteration (iteration > 1)

**Applies:**
- Only the changes described in the confirmed proposal
- Only to files listed in the impact map
- Respects all listed restrictions
- Follows constitution principles

#### Agent 2: Reviewer Agent

**Skill**: `.cursor/skills/spec-kitti-implement/references/reviewer.md`

**Review Levels:**

| Level | Check | Severity | Weight |
|-------|-------|----------|--------|
| 1 | Scope compliance — only files in impact map were touched | CRITICAL | 35% |
| 2 | Restriction compliance — nothing in restrictions list changed | CRITICAL | 25% |
| 3 | Acceptance criteria — all spec item criteria met (if from spec.md) | CRITICAL | 20% |
| 4 | Constitution compliance — principles not violated | ERROR | 15% |
| 5 | Code quality — no regressions, no new smells | WARNING | 5% |

**Outputs:**
- Review report at `.spec-kitti/implementation/[ITEM-ID]-review-N.md`
- Status: `APPROVED` | `NEEDS_REVISION` | `REJECTED`

#### Loop Behavior

```
APPROVED      → done
NEEDS_REVISION → Executor reads review report and corrects (max 5 iterations)
REJECTED       → stop, report to user, ask to re-scope
```

#### Real-Time Progress

```
╔════════════════════════════════════════════════════════════════════════╗
║                  SPEC-KITTI IMPLEMENTATION ORCHESTRATOR                ║
║                         Refactor Execution                             ║
╚════════════════════════════════════════════════════════════════════════╝

Item:             [PROJ-456 / change_type]
Files:            [list]
Max Iterations:   5

─────────────────────────────────────────────────────────────────────────

═══════════════════════════════════════════════════════════════════════
  ITERATION 1 of 5
═══════════════════════════════════════════════════════════════════════

[ORCHESTRATOR] STEP 1: Executor Agent - Applying change...

[Executor Agent] Loading constitution: .spec-kitti/memory/constitution.md
[Executor Agent] Loading architecture: .spec-kitti/discovery/architecture.md
[Executor Agent] Loading confirmed proposal from Step 2b
[Executor Agent] Applying: [change description]
[Executor Agent] Files modified: [list]

─────────────────────────────────────────────────────────────────────────

[ORCHESTRATOR] STEP 2: Reviewer Agent - Validating...

[Reviewer Agent] Level 1: Scope Compliance
[Reviewer Agent] Level 2: Restriction Compliance
[Reviewer Agent] Level 3: Acceptance Criteria
[Reviewer Agent] Level 4: Constitution Compliance
[Reviewer Agent] Level 5: Code Quality
[Reviewer Agent] Output: .spec-kitti/implementation/[ITEM-ID]-review-1.md

─────────────────────────────────────────────────────────────────────────

[ORCHESTRATOR] STATUS: APPROVED
[ORCHESTRATOR] All checks passed!

╔════════════════════════════════════════════════════════════════════════╗
║                          CODE APPROVED                                 ║
╚════════════════════════════════════════════════════════════════════════╝

[ORCHESTRATOR] Total Iterations: 1
[ORCHESTRATOR] Review Report: .spec-kitti/implementation/[ITEM-ID]-review-1.md
```

#### Generated Files

```
.spec-kitti/implementation/
├── [ITEM-ID]-review-1.md     ← review report
├── [ITEM-ID]-review-N.md     ← final review (if multiple iterations)
└── [ITEM-ID]-execution.log   ← full execution log
```

#### On APPROVED — mark item done in spec.md

If the item came from spec.md, locate its line and mark the checkbox:

```markdown
- [x] [BUG] PROJ-456 — Modal no cierra con ESC  ← marked done
```

---

## Error Cases

| Condition | Action |
|-----------|--------|
| Item has story points > 3 or implies architectural change | STOP — redirect to `/spec-kitti.specify` |
| Change requires new business logic | STOP — redirect to `/spec-kitti.specify` |
| User rejects proposal repeatedly (3+ times) | STOP — ask user to describe the solution directly or redirect to `/spec-kitti.specify` |
| Restriction violated after MAX_ITERATIONS | STOP — report last review, ask user to re-scope |
| Out-of-scope file modified by Executor | REVIEWER rejects — Executor must revert |
| Constitution principle violated | REVIEWER rejects — Executor must comply |
| `constitution.md` not found | Continue without constraint — warn user |
