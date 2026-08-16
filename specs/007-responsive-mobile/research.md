# Phase 0 Research — Adaptación Responsive Mobile

## Decision 1: Solo frontend; sin cambios de API ni datos

- **Decision**: No modificar backend, OpenAPI de negocio, ni persistencia.
- **Rationale**: La spec asume que la funcionalidad de negocio no cambia; RBAC y subtotales ya viven en el servidor (Constitución I, II, V).
- **Alternatives considered**:
  - Endpoints “mobile”: descartados (duplican contratos y no aportan).
  - App nativa: fuera de alcance y de costo (Principio VI).

## Decision 2: Breakpoint único `768px` con `@media screen`

- **Decision**: Reutilizar el umbral ya presente en `frontend/src/index.css` (`max-width: 768px`) y calificar las nuevas reglas como `screen` para no alterar impresión.
- **Rationale**: Ya hay grids de formulario a 768px; un segundo breakpoint fragmentaría el diseño. Impresión (feature 004) no debe heredar stacked-cards.
- **Alternatives considered**:
  - 480px / 640px: más “phone-only”, pero deja tablets pequeñas con tabla rota.
  - Container queries: más preciso, pero añade complejidad innecesaria a la escala actual.

## Decision 3: Tablas semánticas + CSS stacked-row (`data-label`)

- **Decision**: Conservar `<table>` y, en móvil, mostrar cada `tr` como bloque y cada `td` con etiqueta vía `data-label` (mismo texto y orden que `<th>` de PC).
- **Rationale**: Cumple FR-010 sin reescribir las páginas a otro componente; mantiene lectores de pantalla y tests que buscan tablas/celdas; acciones Editar/Eliminar siguen en la misma fila lógica.
- **Alternatives considered**:
  - Cards React distintas: más markup duplicado y riesgo de omitir campos.
  - Tabla + scroll horizontal interno: rechazado en clarificación (opción A).
  - Ocultar columnas: rechazado (opción D / recorte).

## Decision 4: Menú compacto (botón + panel), mismas destinos

- **Decision**: En móvil, ocultar la fila de links y exponerlas en un panel accionado por un botón (hamburger/“Menú”), incluyendo Configuración y Salir según rol.
- **Rationale**: Clarificación B; el navbar actual es `display:flex` y desborda en ~360px. Compactar no cambia RBAC de cliente (las rutas protegidas siguen en `App.tsx`).
- **Alternatives considered**:
  - Menú siempre visible (clarificación A): ocupa demasiado alto.
  - Barra inferior fija (clarificación C): nuevo patrón de UX no pedido.

## Decision 5: Sin librería CSS nueva

- **Decision**: Extender `index.css`; no introducir Tailwind, Bootstrap ni UI kits.
- **Rationale**: El proyecto ya usa CSS plano; un framework nuevo viola “mínimo cambio” y Principio VI (bundle/proceso).
- **Alternatives considered**:
  - Tailwind: tokens y build extra sin Figma-token pipeline en esta feature.
  - Component library: overkill para 7 pantallas.

## Decision 6: Testing Hybrid (no TDD estricto)

- **Decision**: Unit tests para (1) orden de `data-label` en listados y (2) conjunto de destinos del menú compacto = desktop por rol. El resto es paridad de tests existentes + quickstart visual.
- **Rationale**: Spec § Testing Strategy = Hybrid. CSS no se “TDDea” de forma útil en jsdom (no hay layout real).
- **Alternatives considered**:
  - TDD-first de cada regla CSS: bajo valor, alto ruido.
  - Sin tests: rechazado; hay lógica de campos/roles que sí es testeable.

## Decision 7: Viewport existente; no bloquear zoom

- **Decision**: Conservar `width=device-width, initial-scale=1.0` en `index.html`. No usar `user-scalable=no`.
- **Rationale**: FR-004 pide no *requerir* zoom, no prohibirlo. Bloquear zoom es un anti-patrón de accesibilidad.
- **Alternatives considered**:
  - `maximum-scale=1`: descartado por accesibilidad.
