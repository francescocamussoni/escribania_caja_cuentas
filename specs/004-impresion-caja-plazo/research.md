# Research: Impresión de Caja y Plazos Fijos

**Feature**: `004-impresion-caja-plazo`  
**Date**: 2026-08-06

## R1 — Extensión del stack existente

**Decision**: Reutilizar monorepo `frontend/` + `backend/` (Python 3.12 + FastAPI + SQLAlchemy 2; React 18 + TypeScript + Vite; PostgreSQL 16) sin nuevos servicios Docker.

**Rationale**:
- Feature incremental de solo lectura sobre datos de features 001 y 003.
- Mismos patrones JWT, RBAC, zona horaria AR (`app.core.dates`).

**Alternatives considered**:
- **Microservicio de reporting**: rechazado — costo operativo y duplicación de auth.
- **Generación PDF en el navegador (jsPDF)**: rechazado — lógica de filtrado/totales debe ser autoritativa en backend (constitución V).

## R2 — Ubicación de la generación PDF

**Decision**: Generación **100% en backend**; el frontend solo envía parámetros y descarga el binario.

**Rationale**:
- Paridad garantizada con consulta (misma capa de servicio/SQL).
- RBAC validado server-side antes de emitir bytes.
- Nombre de archivo y `Content-Disposition` controlados en API.

**Alternatives considered**:
- **Frontend render + print**: difícil garantizar SC-002/SC-003 y formato formal A4.
- **JSON + plantilla cliente**: duplica reglas de orden y totales.

## R3 — Librería PDF (Python)

**Decision**: **`fpdf2`** (PyPI: `fpdf2`) para composición del PDF en A4.

**Rationale**:
- Dependencia pura Python; sin Cairo/Pango (WeasyPrint) ni binarios extra en EC2 `t4g.micro`.
- Soporta tablas, fuentes estándar legibles (Helvetica/Times), multipágina.
- Suficiente para encabezado operativo + tablas + signos Entrada/Salida.

**Alternatives considered**:
- **ReportLab**: más potente pero API más verbosa; fpdf2 cubre el alcance v1.
- **WeasyPrint (HTML→PDF)**: mejor CSS pero dependencias de sistema y mayor peso en deploy.
- **LaTeX**: sobredimensionado para informes tabulares simples.

## R4 — Contrato API de informes

**Decision**: Un endpoint **`POST /api/v1/informes/pdf`** con cuerpo JSON (`InformePdfRequest`) y respuesta `application/pdf` + header `Content-Disposition: attachment; filename="..."`.

**Rationale**:
- Un solo punto de validación Pydantic (tipo, caja, modo temporal).
- POST evita URLs largas con fechas; no es operación idempotente de caché.
- Filename generado en servidor según FR-021a.

**Alternatives considered**:
- **GET con query string**: expone parámetros en logs/proxies; menos adecuado para rangos de fechas.
- **Dos endpoints** (`/informes/caja`, `/informes/plazo-fijo`): más rutas sin beneficio claro en v1.

## R5 — Filtros temporales y campo fecha

**Decision**:

| Tipo | Campo filtrado | Implementación |
|------|----------------|----------------|
| Caja | Fecha del movimiento | `DATE(created_at AT TIME ZONE 'America/Argentina/Buenos_Aires')` |
| Plazo fijo | Fecha de creación | Misma conversión sobre `plazo_fijo.created_at` |

Modo **mes/año** sin `hasta_hoy`: rango `[primer_día_mes, último_día_mes]` inclusive en calendario AR.  
Modo **mes/año** con `hasta_hoy=true`: rango `[primer_día_mes_seleccionado, hoy_AR]` inclusive.  
Modo **período** sin `hasta_hoy`: `fecha_inicio` ≤ fecha ≤ `fecha_fin` inclusive.  
Modo **período** con `hasta_hoy=true`: `fecha_inicio` ≤ fecha ≤ `hoy_AR` inclusive (`fecha_fin` ignorada / no enviada).

**Rationale**:
- Alineado con spec y con el modelo actual (`movimiento.fecha` expuesta como `created_at`).
- Reutiliza `today_ar()` y `ARGENTINA_TZ` existentes.

**Alternatives considered**:
- **Filtro UTC sin conversión**: desalinearía límites de mes para usuarios en Argentina.

## R6 — Cálculos de saldos y resumen (caja / plazos)

**Decision**:

**Caja**:
- **Saldo actual**: subtotal del último movimiento cronológico de la caja (misma lógica que `GET /cajas/{id}/saldo`).
- **Saldo al cierre del período**: subtotal del movimiento con `created_at` máximo dentro del conjunto filtrado; si el conjunto está vacío, no mostrar valor numérico engañoso (solo mensaje).

**Plazos fijos**:
- Listado: misma cláusula `ORDER BY` que `PlazoFijoService._list_order_clauses` sin `LIMIT`.
- Resumen: `SUM` sobre plazos con `fecha_vencimiento >= hoy_AR` **y** `created_at` dentro del rango del informe (clarificación sesión 2026-08-06).

**Rationale**:
- Cumple FR-016, FR-019 y clarificaciones Q1/Q2.
- Reutiliza funciones de orden existentes; evita drift con consulta.

**Alternatives considered**:
- **Resumen global de caja en informe filtrado**: rechazado por clarificación del usuario.

## R7 — UX frontend (pantalla Impresión)

**Decision**:
- Nueva ruta `/impresion` para roles `secretaria` y `escribano`.
- Layout paridad `ConsultaCajaPage`: selector de caja, controles de temporalidad, botón **Generar informe**.
- Radio/toggle: tipo **Caja** | **Plazo fijo**; modo **Mes y año** | **Período específico**.
- Checkbox **Hasta hoy** visible en ambos modos; oculta/deshabilita selector `fecha_fin` en período.
- Descarga vía `fetch` + `Blob` + `<a download>` usando filename de `Content-Disposition`.
- Estado de carga (`generando...`) y errores de validación en pantalla.

**Rationale**:
- FR-001–FR-007; sin wireframe nuevo.
- Navbar: enlace **Impresión** junto a consultas.

**Alternatives considered**:
- **Abrir PDF en nueva pestaña sin descarga**: spec permite ambos; implementar descarga explícita como default UX.

## R8 — Testing (TDD)

**Decision**: TDD estricto según `spec.md` § Testing Strategy.

**Scope**:
- Unit: normalización filename, rango mes/año AR, cálculo saldo cierre, resumen plazos filtrado.
- Integration: POST informes 200/400/401/404, bytes PDF válidos (`%PDF`), RBAC secretaria+escribano.
- Frontend: `ImpresionPage.test.tsx` — validación formulario, llamada API, manejo blob/error.

**Rationale**: Dominio financiero + paridad con consulta; regresiones en filtros son críticas.

**Scope note**: Esta decisión DEBE honrarse en `/spec-kitti.tasks` (tests antes de implementación).

**Alternatives considered**: Ninguna — spec ya fijó TDD.

## R9 — Persistencia y límites

**Decision**: Sin tabla nueva; informes efímeros. Sin límite artificial de filas en PDF (FR-023). Timeout de generación alineado a stack existente (~30s objetivo SC-001).

**Rationale**: Assumptions spec; volumen esperado bajo (escribanía, ≤10 usuarios).

**Alternatives considered**:
- **Cola async + S3**: fuera de alcance v1.

## R10 — Opción "Hasta hoy" (amend 2026-08-06)

**Decision**: Campo booleano `hasta_hoy` en `InformePdfRequest`, aplicable a `MES_ANIO` y `PERIODO`. El servidor resuelve `date_to = today_ar()` cuando está activo.

**Rationale**:
- Informes acumulados desde un mes o fecha de inicio sin pedir fecha fin manual.
- Ejemplo de negocio: abril + hoy 17/jul → abr, may, jun completos + 1–17 jul.
- Validación: inicio (mes o fecha) no puede ser posterior a hoy.

**Alternatives considered**:
- **Solo en modo período**: rechazado — el amend exige ambos modos.
- **Mes fin explícito en UI**: más fricción que un checkbox único.
