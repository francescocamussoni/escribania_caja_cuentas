# Implementation Plan: Endose de cheques pendientes

**Branch**: `011-cheque-endose` | **Date**: 2026-11-04 | **Spec**: [spec.md](./spec.md)  
**Input**: Feature specification from `/specs/011-cheque-endose/spec.md`  
**Depende de**: `specs/010-cheques-instrumento` (ya implementada en el código)

---

## Summary

Agregar a cada cheque pendiente un botón **Endose** (siempre habilitado, solo Secretaria) junto a **Liquidar** (que sigue habilitándose en la fecha de liquidación). Al pulsarlo se abre una ventana con las cajas para elegir una destino; al confirmar, **en una sola operación atómica**:

1. el cheque queda **liquidado en su caja de origen** (entrada suma / salida resta), y
2. en la caja destino se crea un **movimiento común inverso** (salida si el cheque era de entrada, entrada si era de salida), misma moneda y monto. Neto entre cajas = 0.

El cheque endosado y su movimiento destino son **registros finales** (sin editar ni eliminar).

**Enfoque técnico** (detalle en [research.md](./research.md)):

- Extender `movimiento` con `endosado_a_caja_id` (cheque) y `endose_cheque_id` (destino, único) + 2 `CHECK`s. El estado sigue siendo `pendiente | liquidado`; "Endosado" es derivado ⇒ saldos, saldo a futuro, sección Cheques e informes funcionan **sin cambios**.
- `MovimientoService.endosar_cheque`: lock de ambas cajas en orden ascendente de `id` → fila del cheque → inserción del destino → replay de ambos streams; todo en la transacción del request (rollback íntegro ante falla).
- Nuevo `POST /api/v1/cajas/{caja_id}/movimientos/{movimiento_id}/endosar` (`{caja_destino_id}`); descripción del destino generada en servidor.
- `update_movimiento` / `delete_movimiento` rechazan (409) registros de endose; `editable = false` en la respuesta.
- Frontend: `EndoseDialog` (lista de cajas, excluye la de origen) y botón **Endose** en el bloque de pendientes y en la sección Cheques.
- Sin dependencias nuevas, sin scheduler, sin cambios de infraestructura.

> **Hallazgo**: la regla "Liquidar solo desde la fecha de liquidación" (FR-003) **ya existe** en backend (`ChequeAunNoLiquidableError`) y frontend (botón deshabilitado). Esta feature solo agrega tests de regresión sobre ella.

---

## Technical Context

**Language/Version**: Python 3.12 (backend) · TypeScript 5.6 / React 18.3 (frontend)  
**Primary Dependencies**: FastAPI 0.115, SQLAlchemy 2.0, Alembic 1.14, Pydantic 2.10, React Router 6, Vite 5 — **sin dependencias nuevas**  
**Storage**: PostgreSQL 16 (local + AWS RDS) — 2 columnas nuevas en `movimiento` + migración Alembic `011`  
**Testing**: pytest (unit + integración sobre Postgres) · Vitest 2 + Testing Library 16 · **TDD-first** (decisión de la spec)  
**Target Platform**: Linux server (backend) · Navegador web (frontend)  
**Project Type**: Web application (`backend/` + `frontend/`)  
**Performance Goals**: Endose = una transacción corta (≤ operación de liquidación); ventana de cajas sin llamadas extra pesadas (≤ ~15+ cajas)  
**Constraints**: Atomicidad total (cheque + destino); idempotencia (409 en doble endose); sin deadlocks en endoses cruzados (orden de locks por `id`); cálculos de saldo solo en servidor (Principio V); RBAC servidor (403 Escribano); descripción del destino generada en servidor (sin texto libre del cliente)  
**Scale/Scope**: ≤ 10 usuarios concurrentes · 15+ cajas · 2 monedas (ARS/USD)

---

## Constitution Check

*GATE: evaluado antes de Phase 0. Re-evaluado post-diseño (abajo).*

| Principio | Estado | Evidencia |
|---|---|---|
| **I. Integridad Financiera de Caja** | ✅ PASS | Origen y destino impactan por los streams (caja, moneda) existentes, mismo monto y moneda, subtotal recalculado en orden de fecha efectiva; ARS/USD nunca se mezclan. Atomicidad: un solo commit; falla ⇒ rollback de ambos efectos. Los registros de endose no se editan/eliminan ⇒ no hay recálculo en cascada que desalinee las cajas. Índice único parcial impide doble endose. |
| **II. RBAC** | ✅ PASS | `POST …/endosar` con `require_role("secretaria")` (403 Escribano). `endosable` solo `true` para Secretaria. Auditoría: `updated_by` (cheque), `created_by` (destino) + evento `cheque_endorsed`. |
| **III. Fidelidad al Diseño (Wireframes)** | ⚠️ PASS CON DESVIACIÓN DOCUMENTADA | Se agrega un botón **Endose** en filas de cheques pendientes y una ventana modal de selección de caja; ninguno figura en los `.drawio`. Pedido explícito del usuario (ver Complexity Tracking). Colores semánticos respetados (verde entrada / rojo salida). |
| **IV. Seguridad por Diseño** | ✅ PASS | Payload validado por Pydantic (`extra="forbid"`, `caja_destino_id ≥ 1`); destino validado en servidor (existe, activa, ≠ origen); el cliente no envía descripción ni montos; consultas parametrizadas (SQLAlchemy); errores genéricos sin detalles internos; logs sin montos ni descripciones; locks ordenados evitan DoS por deadlock. |
| **V. Arquitectura Fullstack Desacoplada** | ✅ PASS | Toda la lógica contable en el backend; frontend solo presenta y envía `caja_destino_id`. Contrato en `contracts/openapi-delta.yaml`. |
| **VI. Costo Mínimo en AWS** | ✅ PASS | Sin servicios ni dependencias nuevas; solo 2 columnas y 1 índice parcial. |

**Constraints técnicas**: PostgreSQL ✔ · ARS/USD independientes ✔ · catálogo de cajas sin cambios ✔ · paginación existente sin cambios ✔.  
**Tests obligatorios** (subtotales y RBAC) ✔ planificados en WU-2 y WU-3.

### Re-check post-diseño (Phase 1)

**PASS.** Ninguna decisión de Phase 1 introduce violaciones:
- Mantener `estado = liquidado` evita relajar `ck_movimiento_subtotal_estado` o tocar `impacta_saldo_expr`.
- Las dos columnas nuevas se protegen con `CHECK`s y un índice único parcial.
- La desviación de wireframes (Principio III) queda documentada en Complexity Tracking y se valida en la verificación manual.

---

## Project Structure

### Documentation (this feature)

```text
specs/011-cheque-endose/
├── plan.md                    ← este archivo
├── research.md                ← Phase 0 ✅
├── data-model.md              ← Phase 1 ✅
├── quickstart.md              ← Phase 1 ✅
├── contracts/
│   └── openapi-delta.yaml     ← Phase 1 ✅
├── checklists/
│   └── requirements.md
└── tasks.md                   ← generado por /spec-kitti.tasks
```

### Source Code — archivos afectados

```text
backend/
├── alembic/versions/
│   └── 011_movimiento_endose.py                  [CREAR]
├── src/app/
│   ├── models/
│   │   └── movimiento.py                         [MODIFICAR] +endosado_a_caja_id/endose_cheque_id, CHECKs, relaciones, propiedades
│   ├── schemas/
│   │   └── movimiento.py                         [MODIFICAR] +EndosarChequeRequest/EndoseResponse/EndoseOrigen, campos en MovimientoResponse, is_editable
│   ├── services/
│   │   └── movimiento_service.py                 [MODIFICAR] +endosar_cheque, +MovimientoEndosadoError, bloqueo en update/delete
│   └── api/routes/
│       └── movimientos.py                        [MODIFICAR] +POST .../endosar; 409 en PATCH/DELETE
└── tests/
    ├── unit/
    │   ├── test_movimiento_endose_model.py       [CREAR]
    │   ├── test_movimiento_endose_schema.py      [CREAR]
    │   └── test_movimiento_service.py            [MODIFICAR] endose
    └── integration/
        ├── test_cheques_endose_service.py        [CREAR]
        ├── test_cheques_endose_api.py            [CREAR]
        ├── test_cheques_liquidar_api.py          [MODIFICAR] regresión: Liquidar sigue exigiendo fecha
        ├── test_movimiento_edit_delete.py        [MODIFICAR] 409 en endose
        └── test_consulta_rbac.py                 [MODIFICAR] Escribano 403 en endosar

frontend/
├── src/
│   ├── services/
│   │   └── api.ts                                [MODIFICAR] Movimiento ampliado, endosarCheque
│   ├── components/
│   │   ├── EndoseDialog.tsx                      [CREAR]     ventana de selección de caja
│   │   ├── ChequesPendientesBlock.tsx            [MODIFICAR] botón Endose + diálogo
│   │   └── MovimientoTable.tsx                   [MODIFICAR] marcas Endosado / Endose desde; oculta Editar/Eliminar
│   ├── pages/
│   │   ├── ChequesPage.tsx                       [MODIFICAR] botón Endose en ambos listados
│   │   └── RegistroCajaPage.tsx                  [MODIFICAR] handler y refresco tras endose
│   └── index.css                                 [MODIFICAR] estilos del diálogo/lista de cajas
└── tests/
    ├── EndoseDialog.test.tsx                     [CREAR]
    ├── ChequesPendientesBlock.test.tsx           [MODIFICAR]
    ├── ChequesPage.test.tsx                      [MODIFICAR]
    ├── MovimientoTable.test.tsx                  [MODIFICAR]
    └── RegistroCajaPage.test.tsx                 [MODIFICAR]
```

**Structure Decision**: Se mantiene la estructura web existente `backend/` + `frontend/`; la feature es aditiva sobre los módulos de cheques de la feature 010.

---

## Plan Jerárquico (para Itti-Kit)

### Work Unit 1: Backend — Migración 011 y modelo `Movimiento`

**Propósito**: Persistir el vínculo cheque ↔ movimiento de endose con integridad a nivel base de datos.

**Entidades afectadas**:
- `Movimiento` (legacy: tabla `movimiento`, modelo `models/movimiento.py`)

**Archivos a crear/modificar**:
- `backend/alembic/versions/011_movimiento_endose.py` — 2 columnas + FKs, 2 `CHECK`s, índice único parcial; `downgrade` aborta si hay endoses
- `backend/src/app/models/movimiento.py` — columnas, `CheckConstraint`s, relaciones `selectin`, propiedades `endosado`, `es_endose_destino`, `bloqueado_por_endose`
- `backend/tests/unit/test_movimiento_endose_model.py`

**Pruebas de Paridad Legacy**:
- `backend/tests/unit/test_movimiento_cheque_model.py`, `backend/tests/integration/test_movimiento_cheque_constraints.py` (constraints de 010 intactos).

**Subtareas internas**:
1. [TDD] Propiedades derivadas; CHECK rechaza `endosado_a_caja_id` en movimiento común o cheque pendiente; CHECK rechaza `endose_cheque_id` en un cheque
2. [TDD] Índice único: dos movimientos con el mismo `endose_cheque_id` ⇒ error de integridad
3. Implementar migración y modelo
4. Verificar `upgrade → downgrade -1 → upgrade`

**Criterio de éxito**: migración reversible; constraints activos; suite unitaria de 010 en verde.

**Dependencias**: ninguna

**Estimación**: 2 h

---

### Work Unit 2: Backend — Servicio de endose y bloqueo de edición/eliminación

**Propósito**: Implementar la operación atómica de endose y proteger los registros resultantes.

**Entidades afectadas**:
- `MovimientoService` (legacy: `services/movimiento_service.py`)

**Archivos a crear/modificar**:
- `backend/src/app/services/movimiento_service.py` — `endosar_cheque`, `MovimientoEndosadoError`, `ChequeEndosoInvalidoError`/validaciones de destino, `create_movimiento(..., endose_cheque_id=None)`; guards en `update_movimiento`/`delete_movimiento`
- `backend/tests/unit/test_movimiento_service.py`
- `backend/tests/integration/test_cheques_endose_service.py`

**Pruebas de Paridad Legacy**:
- `backend/tests/integration/test_movimiento_service.py`, `test_cheques_liquidar_api.py`, `test_movimiento_edit_delete.py`, `test_cheques_edicion_api.py` (liquidar, editar y eliminar sin cambios para registros no endosados).

**Subtareas internas**:
1. [TDD] Cheque de entrada: origen +M, destino salida M (−M); cheque de salida: origen −M, destino entrada M (+M); neto 0; ARS y USD independientes
2. [TDD] Endose con `fecha_liquidacion` futura funciona; el cheque queda liquidado con `fecha_liquidado`, `endosado_a_caja_id` y subtotal correcto en ambos streams
3. [TDD] Descripción del destino generada (`Endose cheque: … (Caja …)`), truncada a 500; `instrumento = ninguno`, `endose_cheque_id` seteado
4. [TDD] Errores: cheque inexistente / de otra caja ⇒ `MovimientoNotFoundError`; ya liquidado o endosado ⇒ `ChequeYaLiquidadoError`; destino inexistente, archivada o == origen ⇒ error de validación
5. [TDD] Atomicidad: forzar falla tras marcar el cheque ⇒ tras rollback el cheque sigue pendiente y no existe movimiento destino
6. [TDD] Concurrencia: dos endoses simultáneos del mismo cheque ⇒ uno OK y otro 409; endoses cruzados A→B / B→A sin deadlock (locks por `id` ascendente)
7. [TDD] `update_movimiento` / `delete_movimiento` sobre cheque endosado y sobre movimiento destino ⇒ `MovimientoEndosadoError`; sobre el resto sin cambios
8. Implementar servicio

**Criterio de éxito**: SC-002, SC-003 y SC-005 verificados por tests; suite de movimientos/cheques sin regresiones.

**Dependencias**: WU-1

**Estimación**: 6 h

---

### Work Unit 3: Backend — Schemas y endpoint de endose

**Propósito**: Exponer el endose con RBAC, validación estricta y respuestas coherentes.

**Entidades afectadas**:
- Router `movimientos`, schemas `movimiento`

**Archivos a crear/modificar**:
- `backend/src/app/schemas/movimiento.py` — `EndosarChequeRequest` (`extra="forbid"`), `EndoseOrigen`, `EndoseResponse`; `MovimientoResponse` + `endosable`, `endosado_a`, `endose_origen`; `is_editable` considera `bloqueado_por_endose`
- `backend/src/app/api/routes/movimientos.py` — `POST /{caja_id}/movimientos/{movimiento_id}/endosar`; `409` en PATCH/DELETE; evento `cheque_endorsed` (sin montos ni descripciones)
- `backend/tests/unit/test_movimiento_endose_schema.py`
- `backend/tests/integration/test_cheques_endose_api.py`, `test_consulta_rbac.py`, `test_movimiento_edit_delete.py`, `test_cheques_liquidar_api.py`

**Pruebas de Paridad Legacy**:
- `backend/tests/integration/test_cheques_api.py`, `test_cheques_seccion_api.py`, `test_saldo_futuro_api.py`, `test_saldo_proyectado_api.py`, `test_informes_api.py` (un cheque endosado ya no es pendiente en ninguna vista; resto sin cambios).

**Subtareas internas**:
1. [TDD] `POST …/endosar` ⇒ 200 con `cheque` (liquidado, `endosado_a`) y `movimiento_destino` (`endose_origen`, tipo inverso); saldos de ambas cajas por `/saldo`
2. [TDD] 401 sin token; 403 Escribano; 404 caja/cheque/destino inexistente; 409 ya liquidado/endosado; 422 destino == origen, archivada o payload inválido (campos extra, `caja_destino_id` ≤ 0)
3. [TDD] Tras endosar: el cheque no aparece en `/cheques` (aptos/próximos), `cheques-pendientes`, `saldo-futuro` ni `saldo-proyectado`; ambos movimientos aparecen en `/movimientos` de su caja y en el informe de Caja
4. [TDD] PATCH/DELETE de cheque endosado y de movimiento destino ⇒ 409; `editable = false`
5. [TDD] Regresión: `liquidar` antes de la fecha ⇒ 409; liquidar normal no crea movimientos en otras cajas
6. Implementar schemas y endpoint; logging estructurado
7. Correr la suite completa de integración

**Criterio de éxito**: endpoint conforme a `contracts/openapi-delta.yaml`; RBAC verificado (SC-006); sin regresión.

**Dependencias**: WU-2

**Estimación**: 4 h

---

### Work Unit 4: Frontend — API client y ventana de selección de caja

**Propósito**: Permitir elegir la caja destino y confirmar el endose.

**Entidades afectadas**:
- `api.ts`, `EndoseDialog` (nuevo)

**Archivos a crear/modificar**:
- `frontend/src/services/api.ts` — `Movimiento` + `endosable`, `endosado_a`, `endose_origen`; tipos `EndoseResponse`; `endosarCheque(cajaId, movimientoId, cajaDestinoId)`
- `frontend/src/components/EndoseDialog.tsx` — diálogo `role="dialog"` `aria-modal`, lista de cajas (radio) sin la caja origen, **Confirmar** deshabilitado sin selección, **Cancelar**/Esc sin efectos, estado "enviando" y error
- `frontend/src/index.css` — estilos (reutilizando el patrón `.complementario-dialog*`)
- `frontend/tests/EndoseDialog.test.tsx`

**Pruebas de Paridad Legacy**:
- `frontend/tests/MovimientoForm.test.tsx` (diálogo complementario intacto), `frontend/tests/ConsultaCajaPage.test.tsx`.

**Subtareas internas**:
1. [TDD] Lista las cajas desplegadas y excluye la caja origen; sin selección **Confirmar** está deshabilitado
2. [TDD] Seleccionar + confirmar llama `onConfirm(cajaId)`; **Cancelar** y Esc cierran sin llamar
3. [TDD] Durante el envío bloquea doble confirmación; ante error muestra mensaje genérico y mantiene el cheque pendiente
4. [TDD] `endosarCheque` envía solo `{ caja_destino_id }` al endpoint correcto
5. Implementar tipos, función y componente
6. Correr Vitest y `npm run build`

**Criterio de éxito**: tests del diálogo en verde.

**Dependencias**: contrato `openapi-delta.yaml` (puede avanzar en paralelo a WU-2/3)

**Estimación**: 4 h

---

### Work Unit 5: Frontend — Botón Endose en registros y sección Cheques

**Propósito**: Exponer **Endose** junto a **Liquidar** y reflejar el resultado en las listas.

**Entidades afectadas**:
- `ChequesPendientesBlock`, `ChequesPage`, `MovimientoTable`, `RegistroCajaPage`

**Archivos a crear/modificar**:
- `frontend/src/components/ChequesPendientesBlock.tsx` — botón **Endose** (habilitado siempre que `endosable`), abre `EndoseDialog`; refresca tras éxito
- `frontend/src/pages/ChequesPage.tsx` — botón **Endose** en **Aptos para liquidar** y **Próximos a liquidar este mes**
- `frontend/src/pages/RegistroCajaPage.tsx` — handler de endose y refresco de Valor de caja, historial, bloque y Saldo a futuro
- `frontend/src/components/MovimientoTable.tsx` — marcas **Endosado → <caja>** / **Endose desde <caja>**; sin Editar/Eliminar si `editable = false`
- `frontend/tests/ChequesPendientesBlock.test.tsx`, `ChequesPage.test.tsx`, `MovimientoTable.test.tsx`, `RegistroCajaPage.test.tsx`

**Pruebas de Paridad Legacy**:
- `frontend/tests/ChequesPendientesBlock.test.tsx`, `ChequesPage.test.tsx`, `RegistroCajaPage.test.tsx`, `ConsultaCajaPage.test.tsx`, `listadoStackedFields.test.tsx` (Liquidar deshabilitado antes de la fecha, sin acciones para Escribano, tablas apiladas en móvil).

**Subtareas internas**:
1. [TDD] **Endose** visible junto a **Liquidar**; con fecha de liquidación futura: Liquidar deshabilitado y Endose habilitado; con fecha llegada: ambos habilitados
2. [TDD] Escribano (y Consulta) no ve **Endose** ni **Liquidar**
3. [TDD] Flujo completo: Endose → elegir caja → confirmar → llamada a `endosarCheque` → el cheque sale del listado/sección y se refrescan saldos
4. [TDD] Error del servidor (p. ej. 409): mensaje claro y el cheque permanece en la lista
5. [TDD] `MovimientoTable` muestra las marcas de endose y oculta acciones de edición cuando `editable = false`
6. Implementar componentes y páginas
7. Verificar responsive (tablas apiladas en móvil) y correr Vitest + `npm run build`

**Criterio de éxito**: flujo cargar cheque → Endose → ver ambos movimientos funciona en Registro y en la sección Cheques; Escribano en solo lectura.

**Dependencias**: WU-4

**Estimación**: 5 h

---

### Notas para Itti-Kit

**Total Work Units**: 5  
**Tiempo total estimado**: 21 h  
**Paralelismo**: WU-4 puede avanzar en paralelo a WU-2/WU-3 usando el contrato `openapi-delta.yaml`; WU-5 requiere WU-4 (y WU-3 para integración real).

**Secuencia recomendada**:
```
WU-1 (migración + modelo) ─► WU-2 (servicio) ─► WU-3 (schemas + endpoint)
                                                        │
WU-4 (api.ts + EndoseDialog) ───────────────────────────┴─► WU-5 (botón Endose en vistas)
```

**Gate de UI (regla `spec-kitti-figma.mdc`)**: WU-4 y WU-5 son tareas de UI; `/spec-kitti.tasks` deberá obtener la referencia Figma (URL o `node-id`) del desarrollador antes de generarlas.

---

## Complexity Tracking

> Sin violaciones a la constitución. Se documentan las desviaciones/riesgos aceptados.

| Item | Por qué es necesario | Alternativa más simple descartada porque… |
|---|---|---|
| **Desviación de wireframes (Principio III)**: botón *Endose* en filas de cheques pendientes y ventana modal de selección de caja | Funcionalidad pedida explícitamente; no existe en los `.drawio` vigentes | No hay forma de ofrecerla sin ampliar el layout; se valida con los usuarios en la verificación manual (quickstart). |
| Dos columnas + 2 `CHECK`s + índice único parcial en `movimiento` | Vínculo bidireccional cheque ↔ destino con integridad en base de datos y protección ante doble endose | Solo lógica de servicio permitiría estados incoherentes ante concurrencia o bugs. Tabla `endose` aparte agrega joins en cada listado (ver research §1). |
| Locks de **dos cajas en orden ascendente de `id`** | Evita deadlock entre endoses cruzados A→B y B→A y serializa el replay de ambos streams | Lockear solo origen permitiría interleaving de recálculos en el destino; lockear sin orden puede interbloquear. |
| Bloqueo de edición/eliminación de endoses (409 + `editable=false`) | Evita que una modificación deje las dos cajas desalineadas (decisión de clarificación 3) | Cascada de eliminación o edición libre exige recalcular y sincronizar dos cajas y no estaba pedido. |
