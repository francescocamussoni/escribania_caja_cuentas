# Skill: Discovery — Bounded Contexts

## Purpose
Group modules into business-meaningful bounded contexts.

## Input
- `.spec-kitti/discovery/modules.md`
- `.spec-kitti/discovery/architecture.md`
- `.spec-kitti/discovery/graph.json`

## Output
- `.spec-kitti/discovery/bounded-contexts.md`

---

## Instructions

### 1. Identify bounded contexts (2–5 max)
A bounded context groups modules that share a single business domain.
Use module responsibilities from `modules.md` to group them.

Rules:
- A module belongs to exactly ONE context
- `shared` / `common` / `utils` modules go in an **Infrastructure** context
- Name each context with a business term, not a technical one
  - ✅ `Translation`, `Retrieval`, `Evaluation`, `Infrastructure`
  - ❌ `Services`, `Utils`, `Misc`

### 2. For each context document
- **Name**: business domain name
- **Modules**: list of modules
- **Responsibility**: what business capability it owns
- **Interfaces**: how it communicates with other contexts (which edges in graph.json cross context boundaries)

### Output Format

```markdown
# Bounded Contexts — [project name]

> Discovery generated: [date]

## Context Map Overview
[ASCII diagram showing contexts and their relationships]

---

## Context: [Name]

**Modules:** `module-a`, `module-b`
**Responsibility:** [one sentence]
**Interfaces:**
- → [Other Context]: via [mechanism]
- ← [Other Context]: via [mechanism]

---
[repeat per context]
```

## Constraints
- Do NOT read source code
- Contexts must use business language
- Maximum 5 contexts — merge small ones if needed
- Be concise — bullet points only, no prose paragraphs
