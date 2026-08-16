# Implementation Plan: Adaptación Responsive Mobile

**Branch**: `007-responsive-mobile` | **Date**: 2026-08-15 | **Spec**: [spec.md](./spec.md)  
**Input**: Feature specification from `/specs/007-responsive-mobile/spec.md`

## Summary

Adaptar el frontend existente para que **todas** las pantallas (login, menú, registro, consulta, plazos fijos, impresión y configuración) sean usables en smartphone sin perder acciones ni datos respecto de PC. En viewport móvil: navegación compacta (botón/panel con las mismas destinos), listados tabulares como bloques apilados con los mismos campos y orden, textos largos completos con salto de línea, y sin scroll horizontal de página. **No hay cambios de API, modelo ni reglas de negocio.** Desktop conserva el layout actual (fidelidad a wireframes). Estrategia de tests: **Hybrid** (unit tests de lógica de adaptación; CSS/layout por verificación visual).

## Technical Context

**Language/Version**: TypeScript 5.x + React 18 (frontend); Python 3.12 sin cambios (backend)  
**Primary Dependencies**: Vite, React Router 6, CSS (sin framework nuevo); Vitest + Testing Library  
**Storage**: N/A (sin persistencia nueva)  
**Testing**: Hybrid — unit tests para orden de campos en listados y paridad de destinos del menú; sin TDD estricto; tests de página existentes como paridad  
**Target Platform**: Navegador web en smartphone (>= ~360px) y desktop; orientación vertical y horizontal  
**Project Type**: Web application (`frontend/` + `backend/`) — solo `frontend/` se modifica  
**Performance Goals**: Primera pintura usable en móvil sin zoom; tareas SC-001/SC-002 (carga < 2 min, consulta < 90 s)  
**Constraints**: Sin scroll horizontal de página; sin recorte de descripciones; RBAC idéntico a PC; media queries de pantalla no deben alterar el flujo de impresión  
**Scale/Scope**: <= 10 usuarios; 7 pantallas + navbar + 4 tablas; 1 breakpoint primario `768px` (ya usado en CSS)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| I — Integridad Financiera | ✅ PASS | No se tocan cálculos, persistencia ni orden cronológico de movimientos |
| II — RBAC | ✅ PASS | Mismas destinos y acciones por rol; el menú compacto no oculta opciones según dispositivo |
| III — Fidelidad al Diseño | ✅ PASS (con desviación documentada) | Desktop permanece fiel a wireframes. En `<768px` los listados pasan a bloques apilados (FR-010); justificado en Complexity Tracking |
| IV — Seguridad por Diseño | ✅ PASS | Sin nuevos endpoints ni relajación de auth; frontend no decide autorización |
| V — Arquitectura Fullstack Desacoplada | ✅ PASS | Solo presentación en `frontend/`; backend autoritativo sin cambios |
| VI — Costo Mínimo AWS | ✅ PASS | Sin infraestructura nueva; CSS/componentes existentes |

**Post-design re-check (Phase 1)**: ✅ All gates remain pass. Desviación de layout móvil documentada; no hay violación injustificada.

## Project Structure

### Documentation (this feature)

```text
specs/007-responsive-mobile/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── README.md
│   └── ui-presentation.yaml
└── tasks.md             # Phase 2 — NOT created by this command
```

### Source Code (repository root)

```text
frontend/
├── index.html                          # REUSE: viewport ya presente
├── src/
│   ├── index.css                       # MODIFY: shell, navbar, tablas apiladas, wrap, forms
│   ├── App.tsx                         # REUSE: rutas y RBAC de cliente
│   ├── components/
│   │   ├── layout/Navbar.tsx           # MODIFY: menú compacto móvil
│   │   ├── MovimientoTable.tsx         # MODIFY: data-label / orden de campos
│   │   ├── PlazoFijoTable.tsx          # MODIFY: data-label / orden de campos
│   │   ├── MovimientoForm.tsx          # MODIFY si hace falta apilado táctil
│   │   ├── PlazoFijoForm.tsx           # MODIFY si hace falta apilado táctil
│   │   ├── Pagination.tsx              # MODIFY: controles táctiles visibles
│   │   └── ...                         # MODIFY menor: headers, paneles
│   └── pages/
│       ├── LoginPage.tsx               # MODIFY menor: ancho/padding
│       ├── RegistroCajaPage.tsx        # MODIFY menor: bloques en columna
│       ├── ConsultaCajaPage.tsx        # MODIFY: tabla inline + controles
│       ├── PlazosFijosPage.tsx
│       ├── ConsultaPlazosFijosPage.tsx
│       ├── ImpresionPage.tsx           # MODIFY: formulario; no romper impresión
│       └── ConfiguracionCajasPage.tsx  # MODIFY: tabla + form fila
└── tests/
    ├── Navbar.test.tsx                 # MODIFY: toggle móvil + mismas destinos
    ├── listadoStackedFields.test.tsx   # NEW: orden de campos en bloques
    ├── RegistroCajaPage.test.tsx       # PARIDAD
    ├── ConsultaCajaPage.test.tsx       # PARIDAD
    ├── LoginPage.test.tsx              # PARIDAD
    ├── ImpresionPage.test.tsx          # PARIDAD
    ├── ConfiguracionCajasPage.test.tsx # PARIDAD
    └── ...                             # PARIDAD resto de páginas
```

**Structure Decision**: Monorepo actual. Feature 100% frontend. No se agregan paquetes CSS (Tailwind, etc.). Breakpoint canónico: `max-width: 768px` con `@media screen` para no afectar impresión.

## Plan Jerárquico (para Itti-Kit)

### Work Unit 1: Shell, breakpoint y reglas globales de overflow/texto

**Propósito**: Establecer el comportamiento móvil base (sin overflow horizontal, textos que envuelven, padding táctil) sin cambiar datos ni rutas.

**Entidades afectadas**:
- Vista de Pantalla
- Bloque Funcional de Interfaz

**Archivos a crear/modificar**:
- `frontend/src/index.css` — media queries `screen and (max-width: 768px)` para `.app-main`, headers, forms, pagination, login, impresión, config
- `frontend/index.html` — confirmar viewport (sin cambiar scale de usuario)

**Pruebas de Paridad Legacy**:
- `frontend/tests/LoginPage.test.tsx`
- `frontend/tests/AppRoutes.test.tsx`

**Subtareas internas**:
1. Definir breakpoint único `768px` y restringir queries a `screen`.
2. Evitar `overflow-x` de página; `overflow-wrap: anywhere` / `word-break` en descripciones.
3. Apilar `.page-header`, `.consulta-controls`, `.config-cajas-form__row`, `.movimiento-edit-actions`, `.impresion-date-row`.
4. Asegurar targets táctiles mínimos (~44px) en botones de acción primaria y paginación.
5. Verificar que estilos de impresión no se alteran.

**Criterio de éxito**: En ~360px de ancho, login y shells no generan scroll horizontal; textos largos no se recortan.

**Estimación**: 3h

---

### Work Unit 2: Navegación compacta

**Propósito**: En móvil, compactar el menú en botón/panel con las mismas destinos que en PC según rol.

**Entidades afectadas**:
- Bloque Funcional de Interfaz (navegación)

**Archivos a crear/modificar**:
- `frontend/src/components/layout/Navbar.tsx` — toggle, `aria-expanded`, panel de links
- `frontend/src/index.css` — layout navbar móvil
- `frontend/tests/Navbar.test.tsx` — paridad de destinos + toggle

**Pruebas de Paridad Legacy**:
- `frontend/tests/Navbar.test.tsx` — Configuración entre usuario y Salir en desktop; ocultar a escribano

**Subtareas internas**:
1. Añadir control “Menú” visible solo en viewport móvil (CSS o matchMedia en test con clase).
2. El panel incluye los mismos `NavLink` que el nav desktop para el rol.
3. Configuración y Salir permanecen accesibles.
4. Cerrar el panel al navegar.
5. Tests: secretaria y escribano ven el mismo conjunto de destinos que en desktop.

**Criterio de éxito**: FR-011 cubierto; tests de Navbar verdes incluyendo paridad de rol.

**Dependencias**: [WU-1] (estilos de shell)

**Estimación**: 3h

---

### Work Unit 3: Listados apilados (lógica de campos)

**Propósito**: En móvil, cada fila tabular se muestra como bloque con los mismos campos y el mismo orden que las columnas de PC.

**Entidades afectadas**:
- Fila de Listado
- Elemento de Dato Financiero Visible

**Archivos a crear/modificar**:
- `frontend/src/components/MovimientoTable.tsx` — `data-label` por celda en orden PC
- `frontend/src/components/PlazoFijoTable.tsx` — idem
- `frontend/src/pages/ConsultaCajaPage.tsx` — tabla inline
- `frontend/src/pages/ConfiguracionCajasPage.tsx` — tabla de cajas
- `frontend/src/index.css` — patrón stacked-table (`thead` oculto, `tr`/`td` block)
- `frontend/tests/listadoStackedFields.test.tsx` — **unit tests de lógica core** (orden de labels)

**Pruebas de Paridad Legacy**:
- `frontend/tests/RegistroCajaPage.test.tsx`
- `frontend/tests/ConsultaCajaPage.test.tsx`
- `frontend/tests/PlazosFijosPage.test.tsx`
- `frontend/tests/ConsultaPlazosFijosPage.test.tsx`
- `frontend/tests/ConfiguracionCajasPage.test.tsx`

**Subtareas internas**:
1. Extraer o documentar el orden canónico de campos por listado (ver `contracts/ui-presentation.yaml`).
2. [Hybrid tests] Cubrir que cada celda expone `data-label` en el orden de columnas PC.
3. Implementar CSS stacked-row; acciones Editar/Eliminar al final del bloque.
4. Descripciones con wrap completo (FR-012).
5. Estado vacío sigue siendo un mensaje único, no un bloque de campos.

**Criterio de éxito**: FR-010 y FR-012 cubiertos; unit tests de labels verdes; páginas existentes no rompen.

**Dependencias**: [WU-1]

**Estimación**: 5h

---

### Work Unit 4: Formularios y pantallas restantes

**Propósito**: Completar usabilidad táctil de login, registro, plazos, consulta conjunto, impresión y configuración.

**Entidades afectadas**:
- Vista de Pantalla
- Bloque Funcional de Interfaz

**Archivos a crear/modificar**:
- `frontend/src/index.css` — grids de `.movimiento-form` / `.plazo-fijo-form` (ya hay algo a 768px)
- `frontend/src/components/MovimientoForm.tsx` / `PlazoFijoForm.tsx` si el markup lo requiere
- `frontend/src/pages/ImpresionPage.tsx` — controles apilados; preview usable
- `frontend/src/pages/ConsultaCajaPage.tsx` — solapas/conjunto
- `frontend/src/components/Pagination.tsx` — botones visibles

**Pruebas de Paridad Legacy**:
- `frontend/tests/ImpresionPage.test.tsx`
- `frontend/tests/LoginPage.test.tsx`

**Subtareas internas**:
1. Formularios en una columna en móvil; Entrada/Salida a ancho completo.
2. Errores junto al campo/acción, sin tapar botones.
3. Paginación siempre visible bajo el listado.
4. Impresión: layout de pantalla móvil; no cambiar composición de documento impreso.
5. Orientación: layout CSS fluido (sin estado que se pierda al rotar).

**Criterio de éxito**: FR-001–FR-009 cubiertos en recorrido manual del quickstart.

**Dependencias**: [WU-1], [WU-3]

**Estimación**: 4h

---

### Work Unit 5: Verificación Hybrid y aceptación visual

**Propósito**: Confirmar paridad de tests existentes, tests de adaptación y checklist móvil.

**Archivos a crear/modificar**:
- `frontend/tests/*` — ajustes si selectores cambian
- `docs/frontend.md` — nota de comportamiento responsive (opcional, si el doc lista layout)

**Pruebas de Paridad Legacy**:
- Suite completa `frontend` (`npm test`)
- Backend sin cambios: no se espera fallar; no es obligatorio re-correr salvo duda

**Subtareas internas**:
1. Ejecutar `npm test` en `frontend/`.
2. Recorrer quickstart a 360×800 y landscape.
3. Comparar orden de bloques PC vs móvil (SC-004).
4. Confirmar ausencia de scroll horizontal (SC-003).

**Criterio de éxito**: Tests frontend verdes; checklist de `quickstart.md` completa.

**Dependencias**: [WU-2], [WU-3], [WU-4]

**Estimación**: 2h

---

### Notas para Itti-Kit

**Total estimado de Work Units**: 5  
**Tiempo total estimado**: 17h  
**Work Units que pueden ejecutarse en paralelo**: WU-2 y WU-3 tras WU-1; WU-4 tras WU-1+WU-3; WU-5 al final

## Complexity Tracking

> Desviación de Principle III **solo en viewport móvil**, justificada por spec FR-010.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Layout de listados distinto al wireframe en `<768px` (bloques apilados) | El wireframe es de escritorio; una tabla de 4–5 columnas no cabe sin zoom ni scroll horizontal, prohibidos por FR-005/FR-010 | Conservar tabla + scroll horizontal: rechazado en clarificación. Comprimir/recortar columnas: pierde datos financieros |

## Phase Artifacts Generated

| Artifact | Path | Status |
|----------|------|--------|
| Research | [research.md](./research.md) | ✅ Complete |
| Data Model | [data-model.md](./data-model.md) | ✅ Complete |
| Contracts | [contracts/](./contracts/) | ✅ Complete (sin API nueva) |
| Quickstart | [quickstart.md](./quickstart.md) | ✅ Complete |

## Testing Strategy (plan reference)

- **Enfoque**: `Hybrid (Unit Tests for core logic, no strict TDD)` — per `spec.md` § Testing Strategy
- **Rationale**: Feature de presentación; tests unitarios cubren orden de campos en listados apilados y paridad de destinos del menú. CSS y layout se validan en quickstart.
- **Scope note**: `/spec-kitti.tasks` MUST emitir tareas de unit test para lógica de listados/menú, **sin** exigir tests escritos antes de cada cambio de CSS. No omitir tests de paridad de páginas existentes.

## Suggested Next Command

`/spec-kitti.tasks` → `/spec-kitti.tasks.shape` → `/spec-kitti.implement`
