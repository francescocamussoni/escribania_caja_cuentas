# Skill: Implement — Figma UI Guide

## Purpose

Provide the Executor with a precise, step-by-step protocol for extracting design specifications from Figma via MCP and translating them into production-ready UI code aligned with the project's conventions.

> This guide is invoked automatically by the Executor whenever a Work Unit involves UI files (`.tsx`, `.jsx`, `.vue`, `.svelte`, `.css`, `.scss`, etc.). Read it **before** writing any style or layout code.

---

## Phase 1: Figma Reference Gatekeeper (HARD STOP)

> **This is the first and most critical step. Read it before anything else.**
> If this check fails, the executor MUST stop immediately. No exceptions.

### 1.0 — Check for Figma Reference

Search in this exact order:

1. Work Unit JSON → fields `figma_url` or `figma_node_id`
2. `.spec-kitti/spec.md` → design section or task metadata
3. `.spec-kitti/tasks.md` → `figma:` field on the task line

**Decision table:**

| Result | Action |
|--------|--------|
| Found: full Figma URL (`figma.com/design/...?node-id=...`) | Proceed to 1.1 |
| Found: bare node-id in format `NNNN:NNNN` | Proceed to 1.1 |
| Not found anywhere | **STOP. Emit blocking error below. Do NOT write any code.** |

### 1.0-ERR — Blocking Error Message

When no Figma reference is found, emit this message **verbatim** and halt:

```
🚫 FIGMA REFERENCE REQUIRED — UI TASK BLOCKED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Task   : [task-id or WU-ID]
File   : [file_path]
Status : BLOCKED — no Figma reference found.

This task involves UI code. Spec-Kitti requires an exact Figma
node reference before generating any design-related code.

Please provide ONE of the following:

  Option A — Full Figma frame URL (preferred):
    https://www.figma.com/design/<fileKey>/<fileName>?node-id=<nodeId>

  Option B — Node ID only (if fileKey is already known):
    node-id: <NNNN:NNNN>

How to get it in Figma:
  1. Select the frame or component
  2. Right-click → "Copy link to selection"
     — or —
  3. Copy the full URL from the browser bar (includes ?node-id=...)

⚠️  No code will be generated until a valid Figma reference is provided.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

After emitting this error: **stop all processing for this Work Unit**. Do not generate placeholder code, do not generate a partial file, do not add TODO comments. Wait for the developer to provide the reference and re-invoke the command.

### 1.1 — Confirm CSS Convention

(Only reached after 1.0 passes.)

- Scan `plan.md` and `constitution.md` for: CSS Variables, Tailwind, Styled Components, Emotion, CSS Modules, plain CSS
- Confirm: Is there a design token file (e.g. `tokens.ts`, `theme.ts`, `variables.css`)?

### 1.2 — Check for Reusable Components

- Check `.spec-kitti/discovery/modules.md` (if it exists) for a UI / components module
- Reuse existing components before creating new ones

---

## Phase 2: Figma MCP Extraction

### 2.1 Parse the Figma URL

```
https://www.figma.com/design/:fileKey/:fileName?node-id=:nodeId
```

- `fileKey` — the unique identifier in the URL path segment after `/design/`
- `nodeId` — the value of `node-id` query param; replace `-` with `:`

### 2.2 Call `get_design_context`

```json
{
  "fileKey": "<fileKey>",
  "nodeId": "<nodeId>"
}
```

**What this returns:**
- `reference_code` — React+Tailwind snippet (structural guide only, not final code)
- `screenshot` — visual reference of the node
- `hints` — Code Connect mappings, design tokens as CSS vars, designer annotations

**Priority of hints:**
1. Code Connect snippets → use the mapped codebase component directly
2. Component documentation links → follow for usage guidelines
3. Designer annotations → hard constraints (do not deviate)
4. Design tokens as CSS variables → map to project's token system
5. Raw hex / absolute px → loosely structured; validate with screenshot

### 2.3 Build the Token Extraction Table

After receiving the MCP response, construct an internal extraction table (do not output to file, keep in working memory):

```
COMPONENT: <Figma node name>
FIGMA NODE ID: <nodeId>

── COLORS ──────────────────────────────────────────────────────
  background:        #RRGGBB  | rgba(R,G,B,A)  | token: <name>
  text-primary:      #RRGGBB                   | token: <name>
  text-secondary:    #RRGGBB                   | token: <name>
  border:            rgba(R,G,B,A)             | token: <name>
  shadow-color:      rgba(R,G,B,A)
  gradient:          [stop1: #X at N%, stop2: #Y at N%]

── TYPOGRAPHY ──────────────────────────────────────────────────
  <textNode1>:
    font-family:    <value>
    font-size:      <px> → <rem>
    font-weight:    <number>
    line-height:    <px or ratio>
    letter-spacing: <px or em>
    text-transform: <value>

── LAYOUT ──────────────────────────────────────────────────────
  <frameName>:
    auto-layout:    <HORIZONTAL | VERTICAL | GRID | NONE>
    flex-direction: <row | column>
    gap:            <px>
    padding:        <T R B L in px>
    justify-content:<flex-start | center | flex-end | space-between>
    align-items:    <flex-start | center | flex-end>
    flex-wrap:      <wrap | nowrap>

── SIZES ───────────────────────────────────────────────────────
  width:     <px | fill(→100%) | hug(→fit-content)>
  height:    <px | fill(→100%) | hug(→fit-content)>
  min-width: <px if constrained>
  max-width: <px if constrained>

── EFFECTS ─────────────────────────────────────────────────────
  border-radius:    <value: uniform or TL TR BR BL>
  box-shadow:       <offset-x offset-y blur spread rgba()>
  border:           <width style rgba()>
  opacity:          <0..1>
  backdrop-filter:  <blur(Npx) if present>
```

### 2.4 Call `get_screenshot` (validation only)

```json
{
  "fileKey": "<fileKey>",
  "nodeId": "<nodeId>"
}
```

Store the screenshot URL for visual validation at the end. Do not use it as the source of any token value.

---

## Phase 3: Token → Code Mapping

### 3.1 CSS Variables (`:root` convention)

Map extracted tokens to existing CSS variables in the project:

```css
/* Step 1: Check if the token already exists */
/* → search in tokens.css / variables.css / theme files */

/* Step 2: If it exists, use the variable */
background-color: var(--color-surface);

/* Step 3: If it doesn't exist, add it to the token file */
/* and use the variable */
--color-surface-elevated: #F9FAFB;  /* Figma: Neutral/50 */
```

**Naming convention for new variables:**
```
--{category}-{semantic-name}: value;
/* Examples: */
--color-primary-default
--color-text-muted
--font-size-heading-md
--spacing-card-padding
--radius-button
--shadow-card-elevated
```

### 3.2 Tailwind CSS Mapping

Priority order:

| Scenario | Approach | Example |
|----------|----------|---------|
| Exact semantic class in config | Use it | `bg-primary-500` |
| Standard Tailwind scale match | Use utility | `p-4` for 16px |
| Close scale value (±2px) | Use nearest | `gap-3` for 11px → `gap-3` (12px) |
| Non-standard value (no close match) | Arbitrary value | `gap-[18px]` |
| Custom color not in palette | Arbitrary value | `text-[#3B82F6]` |

**Spacing scale reference:**
```
p-1 = 4px  |  p-2 = 8px  |  p-3 = 12px  |  p-4 = 16px
p-5 = 20px |  p-6 = 24px |  p-8 = 32px  |  p-10 = 40px
p-12 = 48px | p-16 = 64px
```

**Border radius reference:**
```
rounded-sm = 2px  |  rounded = 4px    |  rounded-md = 6px
rounded-lg = 8px  |  rounded-xl = 12px | rounded-2xl = 16px
rounded-full = 9999px
```

### 3.3 CSS-in-JS (Styled Components / Emotion)

```ts
// Always reference the project theme — never hardcode
import { theme } from '@/styles/theme';

const StyledButton = styled.button`
  background-color: ${({ theme }) => theme.colors.primary[500]};
  font-size: ${({ theme }) => theme.fontSizes.sm};
  font-weight: ${({ theme }) => theme.fontWeights.medium};
  border-radius: ${({ theme }) => theme.radii.md};
  padding: ${({ theme }) => `${theme.spacing[2]} ${theme.spacing[4]}`};
`;
```

If a token doesn't exist in the theme, add it — don't hardcode the value inline.

### 3.4 CSS Modules

```css
/* ComponentName.module.css */
.container {
  /* Reference CSS variables from the global token file */
  background-color: var(--color-surface);
  padding: var(--spacing-md) var(--spacing-lg);
  border-radius: var(--radius-card);
  box-shadow: var(--shadow-card-elevated);
}

.title {
  font-family: var(--font-family-base);
  font-size: var(--font-size-heading-md);
  font-weight: var(--font-weight-bold);
  color: var(--color-text-primary);
  line-height: var(--line-height-tight);
}
```

---

## Phase 4: Component Naming and Semantics

### 4.1 Derive Component Name from Figma Node

```
Figma node name     → Component / Class name
──────────────────────────────────────────────────────
Button/Primary/Default → <PrimaryButton> or .btn--primary
Card/Elevated          → <ElevatedCard> or .card--elevated
Input/Text/Default     → <TextInput> or .input--text
Modal/Overlay          → <ModalOverlay> or .modal__overlay
Navigation/TopBar      → <TopBar> or .nav-topbar
```

Rules:
- Use PascalCase for React component names
- Use BEM or kebab-case for CSS class names (follow project convention)
- Preserve the hierarchy: `Group/Variant/State`
- Add a JSDoc comment referencing the Figma node name:

```tsx
/**
 * Figma: Button/Primary/Default
 * Node: 123:456
 */
export const PrimaryButton: React.FC<PrimaryButtonProps> = ({ ... }) => {
```

### 4.2 Variant Mapping

When a Figma component has variants (e.g. `size=sm|md|lg`, `state=default|hover|disabled`):

```tsx
// Map each variant to a prop
interface ButtonProps {
  size?: 'sm' | 'md' | 'lg';        // Figma: size property
  variant?: 'primary' | 'secondary'; // Figma: variant property
  disabled?: boolean;                 // Figma: state=disabled
}
```

---

## Phase 5: Accessibility (A11y) Requirements

Always add these when building UI components — they are non-negotiable:

```tsx
// Interactive elements
<button
  aria-label="<descriptive label>"
  aria-disabled={disabled}
  role="button"
>

// Images
<img alt="<descriptive alt text>" />

// Icons (decorative)
<SomeIcon aria-hidden="true" />

// Form inputs
<input
  id="<id>"
  aria-label="<label>"
  aria-required={required}
  aria-invalid={hasError}
/>
```

Color contrast: verify that text/background pairs from extracted tokens meet WCAG AA (4.5:1 for normal text, 3:1 for large text).

---

## Phase 6: Final Validation Checklist

Before marking the Work Unit complete, verify:

- [ ] All colors sourced from `get_design_context` — no invented hex values
- [ ] All font properties (family, size, weight, line-height) extracted from MCP
- [ ] Auto Layout translated to correct Flexbox/Grid properties
- [ ] Spacing matches extracted padding/gap values (or nearest scale token)
- [ ] Border radius, shadows, and borders match MCP output
- [ ] Component name matches Figma node semantic hierarchy
- [ ] CSS convention of the project honored (vars / Tailwind / CSS-in-JS)
- [ ] Accessibility attributes present on all interactive elements
- [ ] `get_screenshot` referenced to visually validate layout fidelity
- [ ] No hardcoded values that bypass the project's token/theme system

---

## Executor Summary Extension (UI tasks)

```
⚙️ Executor Summary
  Figma node:        <nodeName> [<nodeId>]
  Tokens extracted:  <N> colors · <N> text styles · <N> auto layouts · <N> effects
  CSS convention:    <CSS Variables | Tailwind | Styled Components | CSS Modules>
  New tokens added:  <list any new variables/theme entries added>
  A11y:              <aria attributes added: yes | partial | N/A>
  Skills applied:    <frontend-expert | react-patterns | ...>
  Conflicts resolved:<if any token conflict with constitution or plan>
```
