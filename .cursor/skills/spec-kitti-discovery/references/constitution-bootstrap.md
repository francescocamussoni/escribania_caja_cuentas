# Skill: Discovery — Bootstrap Constitution

## Purpose
Create or update `.spec-kitti/memory/constitution.md` using the discovery artifacts as source of truth.

## Input
- `.spec-kitti/discovery/modules.md`
- `.spec-kitti/discovery/architecture.md`
- `.spec-kitti/discovery/bounded-contexts.md`
- `.spec-kitti/memory/constitution.md` (may or may not exist)

## Output
- `.spec-kitti/memory/constitution.md` (created or updated)

---

## Decision Logic

### Case A — constitution.md does NOT exist
Create `.spec-kitti/memory/` folder if needed, then create the file from the template below.

### Case B — constitution.md EXISTS
**Only update** the `## Codebase` section.  
**Do NOT touch**: Core Principles, Governance, any human-written content.  
Replace only the block between `<!-- DISCOVERY:START -->` and `<!-- DISCOVERY:END -->`.

---

## Template (Case A — new constitution)

```markdown
# [Project Name] Constitution
<!-- Auto-bootstrapped by spec-kitti.discovery on [date] -->
<!-- Complete the TODO sections with your team -->

## Codebase
<!-- DISCOVERY:START — auto-updated by /spec-kitti.discovery, do not edit manually -->

**Analyzed:** [date]  
**Tech stack:** [from architecture.md]  
**Pattern:** [architectural pattern from architecture.md]

### Module Map
| Module | Responsibility |
|--------|----------------|
[one row per module from modules.md]

### Bounded Contexts
[list contexts from bounded-contexts.md with one-line description each]

### Key Artifacts
- Architecture: `.spec-kitti/discovery/architecture.md`
- Modules: `.spec-kitti/discovery/modules.md`
- Contexts: `.spec-kitti/discovery/bounded-contexts.md`

<!-- DISCOVERY:END -->

---

## Core Principles

### I. [TODO: Add Principle]
<!-- Example: "Library-First — every feature starts as a standalone module" -->
[PRINCIPLE_DESCRIPTION]

### II. [TODO: Add Principle]
[PRINCIPLE_DESCRIPTION]

### III. [TODO: Add Principle]
[PRINCIPLE_DESCRIPTION]

---

## Constraints
<!-- TODO: Add project-specific constraints -->
<!-- Example: No direct DB access from controllers, all external calls must be async -->

---

## Development Workflow
<!-- TODO: Add workflow rules -->
<!-- Example: TDD mandatory, PRs require 2 reviews, no secrets in code -->

---

## Governance
Constitution supersedes all other practices.  
`## Codebase` section is auto-managed by `/spec-kitti.discovery` — do not edit manually.  
All other sections require team agreement to amend.

**Version**: 1.0.0 | **Bootstrapped**: [date] | **Last Amended**: [date]
```

---

## Constraints
- In Case B: ONLY replace content between the `<!-- DISCOVERY:START -->` and `<!-- DISCOVERY:END -->` markers
- Never modify principles or governance sections
- Use exact module names and descriptions from discovery artifacts — do not paraphrase
- Project name: infer from the directory name of the legacy path, or use `[Project Name]` if unknown
- Be concise — bullet points only, no prose paragraphs
