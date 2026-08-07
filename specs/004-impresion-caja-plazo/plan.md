# Implementation Plan: Impresión de Caja y Plazos Fijos

**Branch**: `004-impresion-caja-plazo` | **Date**: 2026-08-06 | **Spec**: [spec.md](./spec.md)  
**Input**: Feature specification from `/specs/004-impresion-caja-plazo/spec.md`

## Summary

Nueva sección **Impresión** (`/impresion`) para Secretaria y Escribano: formulario con
tipo (Caja / Plazo fijo), selector de caja, temporalidad (mes/año o período específico),
opción **Hasta hoy** (rango desde mes/fecha inicio hasta hoy en AR) y generación de
**PDF formal** vía `POST /api/v1/informes/pdf`. El backend filtra datos
con las mismas reglas que consulta, calcula saldos dual (caja) o resumen filtrado
(plazos), renderiza PDF con **fpdf2** y devuelve archivo con nombre
`<TIPO>-<NOMBRE_CAJA>-<PERIODO>.pdf`. Enfoque **TDD** según spec. Sin migraciones DB.

## Technical Context

**Language/Version**: Python 3.12 (backend), TypeScript 5.x / React 18 (frontend)  
**Primary Dependencies**: FastAPI, SQLAlchemy 2, Pydantic v2 (existentes); **fpdf2** (nuevo); React Router, Vite (existentes)  
**Storage**: PostgreSQL 16 — sin cambios de schema (lectura `movimiento`, `plazo_fijo`, `caja`)  
**Testing**: pytest + httpx (backend TDD/integration); Vitest + Testing Library (frontend)  
**Target Platform**: Navegador web; API Linux container (igual que 001/003)  
**Project Type**: Web application (`frontend/` + `backend/`)  
**Performance Goals**: Generación PDF < 30s (SC-001); API < 500ms p95 para consultas auxiliares  
**Constraints**: RBAC server-side; zona horaria AR; PDF A4 formal; solo lectura; filename FR-021a; flag `hasta_hoy` en ambos modos temporales  
**Scale/Scope**: 15 cajas; informes sin límite de 20 filas; 1 pantalla nueva + 1 endpoint

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| I — Integridad Financiera | ✅ PASS | Saldos y totales calculados en backend; reutiliza subtotales persistidos y agregaciones SQL |
| II — RBAC | ✅ PASS | `secretaria` + `escribano` en POST informes; sin escritura de datos financieros |
| III — Fidelidad al Diseño | ✅ PASS (con nota) | Sin drawio nuevo; paridad layout Consulta (FR-007); PDF B/N con signos (clarificación Q3) |
| IV — Seguridad | ✅ PASS | JWT, validación server-side, logs sin montos/PII, `extra="forbid"` en request |
| V — Fullstack Desacoplado | ✅ PASS | OpenAPI en `contracts/`; PDF y filtros solo en backend |
| VI — Costo Mínimo AWS | ✅ PASS | fpdf2 puro Python; sin S3/cola; mismo deploy EC2 existente |

**Post-design re-check (Phase 1)**: ✅ All gates pass. No Complexity Tracking entries required.

## Project Structure

### Documentation (this feature)

```text
specs/004-impresion-caja-plazo/
├── plan.md              # This file
├── research.md          # Phase 0
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/
│   └── openapi.yaml     # Phase 1 — POST informes/pdf
└── tasks.md             # Phase 2 (/spec-kitti.tasks)
```

### Source Code (cambios esperados)

```text
backend/
├── pyproject.toml                          # MODIFY — add fpdf2
├── src/app/
│   ├── schemas/
│   │   └── informe.py                      # NEW — InformePdfRequest, validators
│   ├── services/
│   │   ├── informe_service.py              # NEW — filtros, saldos, resumen filtrado
│   │   └── pdf_informe_renderer.py         # NEW — fpdf2 A4, tablas, encabezado
│   ├── api/routes/
│   │   └── informes.py                     # NEW — POST /informes/pdf
│   ├── core/
│   │   └── filenames.py                    # NEW — normalize caja name, build filename
│   └── main.py                             # MODIFY — register router
├── tests/
│   ├── unit/
│   │   ├── test_informe_date_range.py      # NEW
│   │   ├── test_informe_filename.py        # NEW
│   │   └── test_pdf_informe_renderer.py    # NEW
│   └── integration/
│       └── test_informes_api.py            # NEW — RBAC, PDF bytes, 400/404

frontend/
├── src/
│   ├── pages/
│   │   └── ImpresionPage.tsx               # NEW
│   ├── components/
│   │   └── TemporalidadSelector.tsx        # NEW (opcional — o inline en page)
│   ├── services/
│   │   └── api.ts                          # MODIFY — postInformePdf blob helper
│   ├── components/layout/Navbar.tsx          # MODIFY — link Impresión
│   └── App.tsx                             # MODIFY — route /impresion
└── tests/
    └── ImpresionPage.test.tsx              # NEW
```

**Structure Decision**: Extensión del monorepo existente. Sin Alembic. Dependencia nueva
única: `fpdf2` en backend.

## Plan Jerárquico (para Itti-Kit)

### Work Unit 1: Servicio de Informes y Filtros (backend)

**Propósito**: Resolver rangos temporales AR, consultar movimientos/plazos filtrados y calcular saldos/resumen según clarificaciones.

**Entidades afectadas**:
- `movimiento` (lectura)
- `plazo_fijo` (lectura)
- `caja` (lectura)

**Archivos a crear/modificar**:
- `backend/src/app/schemas/informe.py` — DTO + validación modo/fechas
- `backend/src/app/services/informe_service.py` — queries y cálculos
- `backend/src/app/core/filenames.py` — `build_informe_filename()`
- `backend/tests/unit/test_informe_date_range.py`
- `backend/tests/unit/test_informe_service.py`

**Pruebas de Paridad Legacy**:
- `test_informe_service.py` — saldo cierre vs actual; resumen plazos solo período filtrado
- `test_informe_date_range.py` — límites mes AR, inclusive fechas

**Subtareas internas**:
1. [TDD] Tests rango mes/año, período y **hasta hoy** (AR timezone, ej. abr→17/jul)
2. Schema `InformePdfRequest` con `hasta_hoy: bool` y validadores cruzados
3. `resolve_date_range()` — mes único vs mes→hoy vs período vs período→hoy
4. `fetch_movimientos_informe` — orden desc, filtro `created_at` AR
5. `compute_saldo_cierre` y reutilizar lógica saldo actual
6. `fetch_plazos_informe` + `compute_resumen_plazos_filtrado`
7. Helper filename FR-021a (incl. sufijo hasta hoy)

**Criterio de éxito**: Tests unitarios verdes; cálculos coinciden con casos manuales de spec.

**Estimación**: 4h

---

### Work Unit 2: Renderer PDF y Endpoint API (backend)

**Propósito**: Renderizar PDF formal A4 y exponer `POST /api/v1/informes/pdf`.

**Entidades afectadas**: N/A (bytes efímeros)

**Archivos a crear/modificar**:
- `backend/pyproject.toml` — `fpdf2`
- `backend/src/app/services/pdf_informe_renderer.py`
- `backend/src/app/api/routes/informes.py`
- `backend/src/app/api/router.py` — include informes
- `backend/tests/unit/test_pdf_informe_renderer.py`
- `backend/tests/integration/test_informes_api.py`

**Pruebas de Paridad Legacy**:
- `test_informes_api.py` — 200 PDF, 400 fechas inválidas, 401, 404, escribano OK
- `test_pdf_informe_renderer.py` — encabezado, signos +/−, período vacío con mensaje

**Subtareas internas**:
1. [TDD] Integration test POST informes (red)
2. Renderer caja: encabezado operativo, dos saldos, tabla con Entrada/Salida
3. Renderer plazo fijo: resumen dual + tabla orden consulta
4. Route con `StreamingResponse`, `Content-Disposition`
5. Log seguridad `informe_generated` (sin montos)

**Criterio de éxito**: `curl` devuelve `%PDF-`; filename correcto; SC-005/SC-006/SC-007.

**Dependencias**: [WU-1]

**Estimación**: 5h

---

### Work Unit 3: Pantalla Impresión (frontend)

**Propósito**: UI `/impresion` con formulario, validación cliente y descarga PDF.

**Entidades afectadas**: N/A

**Archivos a crear/modificar**:
- `frontend/src/pages/ImpresionPage.tsx`
- `frontend/src/services/api.ts` — `postInformePdf()`
- `frontend/src/App.tsx` — ruta + guard roles
- `frontend/src/components/layout/Navbar.tsx` — enlace Impresión
- `frontend/tests/ImpresionPage.test.tsx`

**Pruebas de Paridad Legacy**:
- `ImpresionPage.test.tsx` — validación campos, submit, error 400, loading state

**Subtareas internas**:
1. [TDD] Component tests formulario (incl. checkbox **Hasta hoy**, ocultar fecha fin)
2. Controles tipo / caja / temporalidad + **Hasta hoy** (paridad ConsultaCajaPage)
3. Integración API blob + parse `Content-Disposition`
4. Navbar + ruta para secretaria y escribano
5. Mensajes error usuario (fechas inválidas, sin caja)

**Criterio de éxito**: Flujo manual quickstart §3; descarga con nombre esperado.

**Dependencias**: [WU-2]

**Estimación**: 4h

---

### Work Unit 4: Documentación y verificación E2E

**Propósito**: Actualizar docs operativos y validar criterios SC-001–SC-008.

**Archivos a crear/modificar**:
- `docs/frontend.md` — ruta `/impresion`
- Verificación manual según `quickstart.md`

**Subtareas internas**:
1. Actualizar docs rutas y permisos
2. Ejecutar suite backend + frontend
3. Checklist manual PDF legible A4

**Criterio de éxito**: Quickstart completo sin errores; tests verdes.

**Dependencias**: [WU-3]

**Estimación**: 2h

---

### Notas para Itti-Kit

**Total estimado de Work Units**: 4  
**Tiempo total estimado**: 15h  
**Work Units que pueden ejecutarse en paralelo**: WU-1 → WU-2 → WU-3 secuencial; WU-4 al final

---

## Complexity Tracking

> No violations requiring justification.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |

## Phase Artifacts Generated

| Artifact | Path | Status |
|----------|------|--------|
| Research | [research.md](./research.md) | ✅ Complete |
| Data Model | [data-model.md](./data-model.md) | ✅ Complete |
| OpenAPI | [contracts/openapi.yaml](./contracts/openapi.yaml) | ✅ Complete |
| Quickstart | [quickstart.md](./quickstart.md) | ✅ Complete |

## Testing Strategy (plan reference)

- **Enfoque**: `TDD` — per `spec.md` § Testing Strategy
- **Rationale**: Paridad financiera con consulta; filtros y totales requieren tests antes de implementación
- **Scope note**: `/spec-kitti.tasks` MUST emit test tasks before implementation tasks

## Suggested Next Command

`/spec-kitti.tasks` → `/spec-kitti.tasks.shape` → `/spec-kitti.implement`
