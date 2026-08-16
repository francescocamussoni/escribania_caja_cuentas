# Tasks: Adaptación Responsive Mobile

**Input**: Design documents from `/specs/007-responsive-mobile/`  
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/ui-presentation.yaml, quickstart.md  
**Testing**: Hybrid (spec.md → Testing Strategy): unit tests de lógica de adaptación (menú y `data-label`); **no** TDD estricto de CSS

**Organization**: Tareas agrupadas por user story. Tests de lógica core en US1 (navbar) y US3 (listados); el resto es paridad de tests existentes + quickstart visual.

## Design Reference (UI)

Este proyecto **no usa Figma** para esta feature (no hay URL ni node-id en spec/plan). La constitución (principio III) define `registro_de_caja.drawio` y `consulta_de_caja.drawio` como referencia de escritorio. El pedido de negocio es conservar esa experiencia de PC y reflow en móvil según `contracts/ui-presentation.yaml`. Las tareas UI usan campo `wireframe:` (patrón features 001–006).

| Pantalla / pieza | Wireframe / fuente de verdad |
|------------------|------------------------------|
| Layout desktop | `registro_de_caja.drawio`, `consulta_de_caja.drawio`, UI actual en `frontend/src/` |
| Comportamiento móvil | `specs/007-responsive-mobile/contracts/ui-presentation.yaml` |
| Navbar | `frontend/src/components/layout/Navbar.tsx` |
| Listados | `MovimientoTable.tsx`, `PlazoFijoTable.tsx`, tabla inline `ConsultaCajaPage.tsx`, tabla `ConfiguracionCajasPage.tsx` |

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Paralelizable (archivos distintos, sin dependencias incompletas)
- **[USn]**: User story del spec.md

## Path Conventions

- Frontend: `frontend/src/`, tests en `frontend/tests/`
- Sin cambios backend

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Baseline y contrato de presentación alineado antes de tocar CSS/componentes.

- [x] T001 Verify branch `007-responsive-mobile` and baseline `npm test` in `frontend/` passes
- [x] T002 Confirm viewport `width=device-width, initial-scale=1.0` without `user-scalable=no` in `frontend/index.html`
  - wireframe: frontend/index.html
- [x] T003 [P] Set `configuracion_cajas.field_order` to `Caja`, `Estado`, acciones in `specs/007-responsive-mobile/contracts/ui-presentation.yaml` to match `frontend/src/pages/ConfiguracionCajasPage.tsx`

**Checkpoint**: Branch correcto; tests frontend verdes; contrato de labels alineado a headers reales.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Breakpoint único, sin overflow de página, wrap de texto, chrome apilable. **Bloquea user stories.**

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T004 Add `@media screen and (max-width: 768px)` rules for `html`/`body`/`.app-main` (no page `overflow-x`, padding táctil, `overflow-wrap` on long text) in `frontend/src/index.css`
  - wireframe: frontend/src/index.css
- [x] T005 Stack shared chrome in the same media query (`.page-header`, `.consulta-controls`, `.config-cajas-form__row`, `.movimiento-edit-actions`, `.impresion-date-row`, `.pagination` min tap size) in `frontend/src/index.css`
  - wireframe: frontend/src/index.css

**Checkpoint**: En ~360px el shell no hace scroll horizontal; desktop ≥768px no cambia. Queries no aplican a `print`.

---

## Phase 3: User Story 1 — Operación completa en móvil (Priority: P1) 🎯 MVP

**Goal**: Secretaria y escribano pueden usar login, menú y todas las pantallas en celular sin perder controles ni acciones de PC (FR-001, FR-003, FR-006, FR-007, FR-008, FR-011).

**Independent Test**: DevTools 360×800 → login → menú compacto con destinos del rol → Registro (cargar movimiento) y Consulta (recorrer historial) sin zoom ni controles ocultos. Quickstart.md §3–4 (salvo detalle de bloques de tabla, cubierto en US3).

### Tests for User Story 1 (Hybrid — core logic, not CSS-TDD)

- [x] T006 [P] [US1] Extend compact-menu tests (toggle, same destinations as desktop for secretaria and escribano, panel closes on navigate) in `frontend/tests/Navbar.test.tsx`

### Implementation for User Story 1

- [x] T007 [US1] Add mobile menu button + panel (`aria-expanded`, same `NavLink`s, Configuración and Salir remain reachable) in `frontend/src/components/layout/Navbar.tsx`
  - wireframe: frontend/src/components/layout/Navbar.tsx
- [x] T008 [US1] Style compact navbar (hide inline links, show toggle/panel) under `screen and (max-width: 768px)` in `frontend/src/index.css`
  - wireframe: frontend/src/components/layout/Navbar.tsx
- [x] T009 [P] [US1] Keep login card usable at 360px (full-width fields/actions, errors next to fields) in `frontend/src/index.css` and `frontend/src/pages/LoginPage.tsx`
  - wireframe: frontend/src/pages/LoginPage.tsx
- [x] T010 [US1] Stack movimiento form to one column with full-width Entrada/Salida and visible errors in `frontend/src/index.css` and `frontend/src/components/MovimientoForm.tsx`
  - wireframe: registro_de_caja.drawio
- [x] T011 [P] [US1] Stack plazo-fijo form to one column with full-width primary action in `frontend/src/index.css` and `frontend/src/components/PlazoFijoForm.tsx`
  - wireframe: frontend/src/components/PlazoFijoForm.tsx
- [x] T012 [P] [US1] Keep pagination controls visible and tappable under lists in `frontend/src/components/Pagination.tsx` and `frontend/src/index.css`
  - wireframe: frontend/src/components/Pagination.tsx
- [x] T013 [P] [US1] Ensure Registro page blocks remain operable (selector, form, list, pager) in `frontend/src/pages/RegistroCajaPage.tsx`
  - wireframe: registro_de_caja.drawio
- [x] T014 [P] [US1] Ensure Consulta controls, solapas/conjunto, and pager remain operable in `frontend/src/pages/ConsultaCajaPage.tsx`
  - wireframe: consulta_de_caja.drawio
- [x] T015 [P] [US1] Ensure Plazos fijos resumen + page chrome stack without hiding actions in `frontend/src/pages/PlazosFijosPage.tsx` and `frontend/src/components/PlazosFijosResumenPanel.tsx`
  - wireframe: frontend/src/pages/PlazosFijosPage.tsx
- [x] T016 [P] [US1] Ensure Consulta plazos fijos remains operable in `frontend/src/pages/ConsultaPlazosFijosPage.tsx`
  - wireframe: frontend/src/pages/ConsultaPlazosFijosPage.tsx
- [x] T017 [P] [US1] Stack Impresión filters for screen only (do not change print document layout) in `frontend/src/pages/ImpresionPage.tsx` and `frontend/src/index.css`
  - wireframe: frontend/src/pages/ImpresionPage.tsx
- [x] T018 [P] [US1] Stack Configuración alta form and keep archive/unarchive actions tappable in `frontend/src/pages/ConfiguracionCajasPage.tsx`
  - wireframe: frontend/src/pages/ConfiguracionCajasPage.tsx

**Checkpoint**: US1 — todas las rutas del alcance usables en 360px con menú compacto y mismos permisos. MVP.

---

## Phase 4: User Story 2 — Consistencia visual entre dispositivos (Priority: P2)

**Goal**: En móvil, los bloques funcionales siguen el mismo orden de arriba hacia abajo que en PC (FR-002, SC-004).

**Independent Test**: Abrir cada pantalla en desktop y a 360px; la secuencia selector → formulario/filtros → listado → paginación (o equivalente de esa pantalla) coincide. Spec US2.

### Implementation for User Story 2

- [x] T019 [US2] Preserve DOM/visual block order on Registro (no reorder vs desktop) in `frontend/src/pages/RegistroCajaPage.tsx`
  - wireframe: registro_de_caja.drawio
- [x] T020 [P] [US2] Preserve block order on Consulta including conjunto/solapas in `frontend/src/pages/ConsultaCajaPage.tsx` and `frontend/src/components/CajaConsultaSolapa.tsx`
  - wireframe: consulta_de_caja.drawio
- [x] T021 [P] [US2] Preserve block order on plazos (registro y consulta) in `frontend/src/pages/PlazosFijosPage.tsx` and `frontend/src/pages/ConsultaPlazosFijosPage.tsx`
  - wireframe: frontend/src/pages/PlazosFijosPage.tsx
- [x] T022 [P] [US2] Preserve block order on Impresión and Configuración in `frontend/src/pages/ImpresionPage.tsx` and `frontend/src/pages/ConfiguracionCajasPage.tsx`
  - wireframe: frontend/src/pages/ImpresionPage.tsx

**Checkpoint**: SC-004 verificable pantalla a pantalla. US1 no se reordena.

---

## Phase 5: User Story 3 — Lectura clara de datos financieros (Priority: P3)

**Goal**: Cada fila de listado en celular es un bloque apilado con los mismos campos y orden que PC; textos largos completos (FR-004, FR-005, FR-010, FR-012).

**Independent Test**: Historial con descripción larga en Registro/Consulta: bloque Descripción → Monto → Subtotal → Fecha (→ Acciones); sin ellipsis ni scroll horizontal. Spec US3. Contrato `stacked_lists` en `ui-presentation.yaml`.

### Tests for User Story 3 (Hybrid — core logic)

- [x] T023 [P] [US3] Add unit tests that each stacked list exposes `data-label` in contract order (movimientos, consulta inline, plazos fijos, configuración) in `frontend/tests/listadoStackedFields.test.tsx`

### Implementation for User Story 3

- [x] T024 [US3] Add per-cell `data-label` matching desktop headers (incl. Acciones when present) in `frontend/src/components/MovimientoTable.tsx`
  - wireframe: registro_de_caja.drawio
- [x] T025 [P] [US3] Add per-cell `data-label` in contract order in `frontend/src/components/PlazoFijoTable.tsx`
  - wireframe: frontend/src/components/PlazoFijoTable.tsx
- [x] T026 [P] [US3] Add per-cell `data-label` on the inline movimientos table in `frontend/src/pages/ConsultaCajaPage.tsx`
  - wireframe: consulta_de_caja.drawio
- [x] T027 [P] [US3] Add per-cell `data-label` (`Caja`, `Estado`, acciones) in `frontend/src/pages/ConfiguracionCajasPage.tsx`
  - wireframe: frontend/src/pages/ConfiguracionCajasPage.tsx
- [x] T028 [US3] Implement stacked-row CSS (`thead` hidden, `tr` as card, `td` block with `attr(data-label)`, empty state not split into fields, wrap descriptions, actions after fields) for `.movimiento-table` under `screen and (max-width: 768px)` in `frontend/src/index.css`
  - wireframe: registro_de_caja.drawio

**Checkpoint**: FR-010/FR-012; `listadoStackedFields.test.tsx` verde; paridad de tests de páginas.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Paridad de suite, docs y aceptación visual del quickstart (FR-009 orientación, SC-003).

- [x] T029 [P] Adjust existing frontend tests if selectors change in `frontend/tests/RegistroCajaPage.test.tsx`, `ConsultaCajaPage.test.tsx`, `PlazosFijosPage.test.tsx`, `ConsultaPlazosFijosPage.test.tsx`, `ConfiguracionCajasPage.test.tsx`, `LoginPage.test.tsx`, `ImpresionPage.test.tsx`, `AppRoutes.test.tsx`
- [x] T030 [P] Note mobile navbar + stacked lists behavior in `docs/frontend.md`
- [x] T031 Run `frontend` `npm test` and complete `specs/007-responsive-mobile/quickstart.md` at 360×800 and landscape (no horizontal page scroll; print layout unchanged)

**Checkpoint**: Suite frontend verde; quickstart §3–5 cubierto.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Sin dependencias
- **Foundational (Phase 2)**: Depende de Setup — BLOQUEA user stories
- **User Story 1 (P1)**: Depende de Phase 2 — MVP
- **User Story 2 (P2)**: Depende de US1 (mismas pantallas; solo verifica/ajusta orden)
- **User Story 3 (P3)**: Depende de Phase 2; puede empezar en paralelo a US2 (tablas distintas del chrome de US1)
- **Polish**: Depende de US1–US3

### User Story Dependencies

- **US1 (P1)**: Independiente tras foundation (navegación + formularios)
- **US2 (P2)**: Refina orden de bloques sobre el markup de US1
- **US3 (P3)**: Independiente de US2 a nivel de tablas; comparte `index.css`

### Within Each User Story

- Hybrid: tests de navbar/listados cubren lógica; CSS no requiere test rojo previo
- Navbar markup (T007) antes de CSS navbar (T008) o juntos
- `data-label` en componentes (T024–T027) antes o junto al CSS stacked (T028)
- T023 puede escribirse junto a T024–T028 (no TDD estricto)

### Parallel Opportunities

- T002 ∥ T003
- T009 ∥ T011 ∥ T012 ∥ T013 ∥ T014 ∥ T015 ∥ T016 ∥ T017 ∥ T018 (tras T007/T010 según archivo)
- T020 ∥ T021 ∥ T022
- T025 ∥ T026 ∥ T027
- T029 ∥ T030

---

## Parallel Example: User Story 1

```bash
# Tests de menú:
Task: "Compact menu destinations in frontend/tests/Navbar.test.tsx"

# Implementación:
Task: "Navbar.tsx toggle + panel"
Task: "index.css navbar compacto"
Task: "Login + forms + pages en paralelo (archivos distintos)"
```

---

## Parallel Example: User Story 3

```bash
Task: "listadoStackedFields.test.tsx"
Task: "data-label MovimientoTable.tsx"
Task: "data-label PlazoFijoTable.tsx"
Task: "data-label ConsultaCajaPage.tsx"
Task: "data-label ConfiguracionCajasPage.tsx"
# Luego o en paralelo:
Task: "stacked-row CSS in index.css"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1 Setup
2. Phase 2 Foundational
3. Phase 3 US1 (menú + pantallas usables)
4. **STOP and VALIDATE** quickstart login/registro/consulta a 360px (listados aún pueden ser tabla estrecha hasta US3)

### Incremental Delivery

1. Setup + Foundational
2. US1 → demo operación móvil
3. US2 → mismo orden de bloques
4. US3 → bloques apilados + textos completos
5. Polish + quickstart completo

### Parallel Team Strategy

1. Foundation juntos (`index.css`)
2. Dev A: Navbar US1; Dev B: forms/pages US1
3. US3 tablas en paralelo a US2 orden de páginas

---

## Notes

- Hybrid: **no** exigir tests rojos antes de cada regla CSS
- Unit tests obligatorios: Navbar destinos (T006) y `data-label` (T023)
- Desktop ≥768px debe verse como ahora (wireframes)
- `@media screen` para no romper impresión (004)
- No nuevas dependencias CSS
- Commit por tarea o grupo lógico
- `/spec-kitti.tasks.shape` genera Work Units a partir de este archivo y `plan.md`
