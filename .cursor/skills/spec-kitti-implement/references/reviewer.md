# Skill: Implement — Reviewer

## Purpose
Validate generated code against Work Unit requirements, project principles, developer's standards, and quality standards. Emit a structured review report with a final verdict.

## Input

**Mode A — Work Unit file (structured)**
- Generated code file (path from Work Unit `file_path`)
- `.spec-kitti/work-units/[WU-ID].json` — source of truth for subtasks, BR###, EP###
- `.spec-kitti/memory/constitution.md` (if exists)
- `.spec-kitti/discovery/architecture.md` (only if `.spec-kitti/discovery/` exists)
- `.spec-kitti/plan.md`

**Mode B — Direct task (conversational)**
- Generated code file
- `.spec-kitti/tasks.md` — use as reference for the task being reviewed
- Dev's description from the chat — source of truth for expected behavior
- `.spec-kitti/memory/constitution.md` (if exists)
- `.spec-kitti/discovery/architecture.md` (only if `.spec-kitti/discovery/` exists)
- `.spec-kitti/plan.md`

> In Mode B: Level 1 validates against the dev's description and `tasks.md` instead of a `.json` file. BR### and EP### checks are skipped if not mentioned by the dev.

### Developer's Review Standards (auto-discover and apply)

Scan for review/quality skills:
- `~/.cursor/skills/*/SKILL.md` (global)
- `.cursor/skills/*/SKILL.md` (project)

**Look for skills with these keywords in their description:**
- "review", "code review", "quality"
- "standards", "checklist", "audit"
- "best practices", "patterns"

**Read and apply** any review criteria defined in those skills.

---

## Review Levels

### Level 0 — Developer's Custom Standards (if present)

If skills like `my-code-reviewer`, `code-standards`, `review-checklist` exist:
- [ ] Apply ALL checks defined in those skills
- [ ] Use their severity levels

**Fail condition**: Map the dev's skill result to a standard verdict:
- Dev skill marks issue as blocking / critical → `REJECTED`
- Dev skill marks issue as error / must-fix → `NEEDS_REVISION`
- Dev skill marks issue as warning / suggestion → `APPROVED` with warnings
- If the dev's skill doesn't specify severity → treat as `NEEDS_REVISION`

### Level 1 — Requirements Compliance (CRITICAL · 40%)
- [ ] Every subtask in Work Unit has corresponding implementation (no stubs/TODOs)
- [ ] Every `BR###` has an enforcement point with `# BR###` comment
- [ ] Every `EP###` is addressed with `# EP###` comment (if applicable)
- [ ] File path, class name, and action match the Work Unit exactly

**Fail condition**: Any missing subtask or business rule → status: `REJECTED`

### Level 2 — Architecture Compliance (ERROR · 25%)

**If `.spec-kitti/discovery/` exists (legacy/modernization):**
Cross-check against `architecture.md`, `modules.md`, and `plan.md`:
- [ ] File lives in the correct module/layer per `modules.md`
- [ ] No layer violations (controller importing DB, service importing HTTP router, etc.)
- [ ] Follows the patterns documented in `plan.md` (DI, decorators, base classes)
- [ ] Naming matches module conventions from `modules.md`

**If `.spec-kitti/discovery/` does NOT exist (greenfield):**
Cross-check against `plan.md` only:
- [ ] File path matches the structure defined in `plan.md`
- [ ] No layer violations based on patterns in `plan.md`
- [ ] Follows the patterns documented in `plan.md`

**Fail condition**: Layer violation or pattern mismatch → status: `NEEDS_REVISION`

### Level 3 — Constitution Compliance (ERROR · 20%)
Cross-check against `constitution.md` principles:
- [ ] All stated principles are respected
- [ ] No constraint violations
- [ ] Follows the defined workflow rules

**Fail condition**: Constitution violation → status: `NEEDS_REVISION`

### Level 4 — Code Quality (ERROR · 10%)
Apply checks from:
- Dev's quality skills (if present)
- `spec-kitti-implement/references/code-quality.md` (baseline)

- [ ] Type annotations present on all functions
- [ ] Async error handling: try/except on all external calls
- [ ] No secrets/credentials hardcoded
- [ ] Input validation at entry points
- [ ] No PII or passwords in logs

**Fail condition**: Security issue → status: `REJECTED`; quality issue → `NEEDS_REVISION`

### Level 5 — Maintainability (WARNING · 5%)
- [ ] Functions ≤ 50 lines
- [ ] No obvious code duplication
- [ ] Clear variable and function names

**Fail condition**: Only → status: `APPROVED` with warnings

---

## Verdict Rules

| Condition | Status |
|-----------|--------|
| Level 0 blocking/critical failure | `REJECTED` |
| Level 0 error/must-fix failure | `NEEDS_REVISION` |
| Level 0 warning/suggestion | `APPROVED` with warnings |
| Level 1 or Level 4 security failure | `REJECTED` |
| Level 2, 3, or 4 quality failure | `NEEDS_REVISION` |
| All levels pass (warnings allowed) | `APPROVED` |

---

## Output Format

Write to `.spec-kitti/implementation/[WU-ID]-review-N.md`:

```markdown
# Review Report — [WU-ID] · Iteration N
**Status**: APPROVED | NEEDS_REVISION | REJECTED
**Score**: [0-100]%

## Summary
[One paragraph overall assessment]

## Developer's Standards Applied
[List any dev skills that were used in the review]

## Issues
| Level | Severity | Issue | Line |
|-------|----------|-------|------|
| L0    | CUSTOM   | [Dev's custom check] | 42 |
| L1    | CRITICAL | Missing BR004 enforcement | - |

## Required Changes (for NEEDS_REVISION / REJECTED)
1. [Specific actionable fix #1]
2. [Specific actionable fix #2]

## Warnings (non-blocking)
- [Warning if any]
```

Exit code: `0` = APPROVED, `1` = NEEDS_REVISION, `2` = REJECTED

