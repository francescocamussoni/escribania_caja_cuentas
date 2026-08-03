# Skill: Implement — Executor

## Purpose
Generate production-ready code for a single Work Unit file, consistent with the project's existing architecture and principles.

## Input (read ALL before writing any code)

### 1. Project context (always)
- `.spec-kitti/memory/constitution.md` — principles and constraints that MUST be respected (if exists)
- `.spec-kitti/discovery/architecture.md` — architectural pattern and layers **(only if `.spec-kitti/discovery/` exists)**
- `.spec-kitti/discovery/modules.md` — module responsibilities **(only if `.spec-kitti/discovery/` exists)**
- `.spec-kitti/plan.md` — tech stack, patterns, project-specific decisions

> **Greenfield projects** (new codebase from scratch): `.spec-kitti/discovery/` won't exist — skip those files and derive structure entirely from `plan.md` and the Work Unit.
> **Legacy/modernization projects**: `.spec-kitti/discovery/` exists — always read it before writing any code.

### 2. Developer's Skills (auto-discover and read)

Scan for skills in these locations (both, if they exist):
- `.cursor/skills/*/SKILL.md` (project-level)
- `~/.cursor/skills/*/SKILL.md` (global)

**Exclude:** any skill whose folder name starts with `spec-kitti-`
Reason: those are Spec-Kitti's own internals — reading them as dev preferences would cause the executor to instruct itself, leading to unpredictable behavior.

**Read all found skills** and apply their guidance when relevant to the Work Unit.

Common skill names to look for:
- `backend-expert`, `backend-patterns`, `api-design`
- `frontend-expert`, `react-patterns`, `vue-patterns`
- `database-expert`, `sql-patterns`
- `testing-patterns`, `test-generator`
- `security-patterns`, `auth-patterns`
- Domain-specific: `payments-domain`, `user-management`, etc.

### 3. Spec-Kitti Core Guides (fallback/complement)

If the dev's skills don't cover a topic, use these. Look for them in order — use whichever exists:
1. `.cursor/skills/spec-kitti-implement/references/` (project-level install)
2. `~/.cursor/skills/spec-kitti-implement/references/` (global install)

Available guides:
- `testing-guide.md`
- `code-quality.md`
- `refactoring-guide.md`
- `debugging-guide.md`
- `documentation-guide.md`

### 4. Work Unit (the task)

There are two valid modes — adapt based on what the dev provides:

**Mode A — Work Unit file (structured)**
The dev runs `/spec-kitti.implement WU-005`. Read:
- `.spec-kitti/work-units/[WU-ID].json` containing:
  - `file_path` — file to create or modify
  - `action` — CREATE | MODIFY | DELETE
  - `subtasks` — specific implementation tasks
  - `business_rules` — rules to enforce (BR###)
  - `parity_anchors` — legacy endpoints to maintain parity with (EP###, if applicable)
  - `dependencies` — files/imports required

**Mode B — Direct task (conversational)**
The dev describes the task directly in the chat without a `.json` file. Read:
- `.spec-kitti/tasks.md` — to understand the full task list and locate the specific task being requested
- Derive `file_path`, `action`, and `subtasks` from the dev's description + `tasks.md` context.
Apply the same code generation rules as Mode A — no shortcuts.

### 5. Figma Design Context (UI tasks only)

**Trigger:** Apply this step whenever the Work Unit `file_path` targets a UI file (`.tsx`, `.jsx`, `.vue`, `.svelte`, `.css`, `.scss`, `.html`) or the `subtasks` mention components, layouts, styles, or design tokens.

**Action:** Before writing any UI code, read and follow:

```
references/figma-ui-guide.md   (project-level install)
~/.cursor/skills/spec-kitti-implement/references/figma-ui-guide.md  (global install)
```

#### HARD STOP — Figma Reference Gatekeeper

The very first action when processing a UI task is to verify a Figma reference exists.

**Search in order:**
1. Work Unit JSON → `figma_url` or `figma_node_id`
2. `.spec-kitti/spec.md` → design section
3. `.spec-kitti/tasks.md` → `figma:` field on the task

**If no reference is found:**
- **STOP immediately**
- Do NOT generate any code, stubs, placeholders, or partial files
- Emit the blocking error message (defined verbatim in `figma-ui-guide.md` § 1.0-ERR)
- Wait for the developer to re-invoke the command with a valid Figma reference

**If a reference is found:** proceed with the extraction protocol in `figma-ui-guide.md`.

**Skip this step only if:** the Work Unit explicitly sets `figma_required: false` AND the task has zero design requirements of any kind.

### 6. Feedback (only in correction mode)
- `.spec-kitti/implementation/[WU-ID]-review-N.md` — reviewer's feedback to address

---

## Code Generation Rules

### Priority Order (when conflicts arise)
1. **Constitution** — non-negotiable project principles
2. **Developer's Skills** — their established patterns and preferences
3. **Spec-Kitti Guides** — best practices for gaps
4. **Work Unit** — specific requirements

### Example Scenarios

**Scenario 1: Testing**
- If `testing-patterns/SKILL.md` exists → use dev's testing approach
- Else → use `spec-kitti-implement/references/testing-guide.md`

**Scenario 2: Backend API**
- If `backend-expert/SKILL.md` exists → follow dev's API patterns
- If `api-design/SKILL.md` exists → follow dev's API design rules
- Complement with `spec-kitti-implement/references/code-quality.md`

**Scenario 3: Domain Logic (Payments)**
- If `payments-domain/SKILL.md` exists → apply domain rules
- Constitution → apply project-wide constraints

### Before writing
1. Read `constitution.md` — apply all principles, if it exists (no secrets in logs, validation at entry, etc.)
2. **If `.spec-kitti/discovery/` exists** → read `modules.md` (confirm module) and `architecture.md` (confirm layer)
3. **If `.spec-kitti/discovery/` does NOT exist** → derive module and layer from `plan.md` and the Work Unit `file_path`
4. Read `plan.md` — apply the exact patterns for this layer (dependency injection, decorators, error handling)
5. **Read all relevant dev skills** — apply their patterns and preferences
6. **For UI tasks** → complete the Figma MCP extraction protocol in `references/figma-ui-guide.md` before writing any style or layout code

### While writing
- Implement ALL subtasks — no stubs, no TODOs
- Enforce ALL business rules with inline comment `# BR###` at the enforcement point
- Reference ALL parity anchors with inline comment `# EP###` where relevant
- **Apply patterns from dev's skills** when relevant
- Use the exact naming conventions observed in the module (from `modules.md`)
- Match the abstraction level of the layer (controllers don't touch DB, services don't import HTTP)

### Code quality (non-negotiable)
- Type annotations on all functions
- Error handling: try/catch on all async and external calls
- No hardcoded secrets, credentials, or connection strings
- Input validation at all entry points
- Structured logging — never log passwords, tokens, or PII
- Functions ≤ 50 lines; extract helpers if needed

---

## Output

### 1. Generated file
The complete file at `file_path`. No explanations, no markdown fences — just the file content.

### 2. Execution summary (in chat, not in the file)
After generating the file, print in chat:
```
⚙️ Executor Summary
  Skills applied: [e.g. backend-expert, payments-domain]
  Conflicts resolved: [e.g. backend-expert§async vs constitution§sync → constitution won]
                      (omit if no conflicts)
```

If correction mode: address every issue in the feedback before generating, then print:
```
⚙️ Executor Summary — Correction [WU-ID] iteration N
  Issues addressed: [list from feedback]
  Skills applied: [list]
```

