# Quickstart: 010-cheques-instrumento

**Branch**: `010-cheques-instrumento`  
**Enfoque**: TDD-first (tests antes de la implementación — ver `spec.md` › Testing Strategy)

## Prerequisitos

```bash
git checkout 010-cheques-instrumento

# Backend (desde /backend) — la suite base debe pasar antes de empezar
python -m pytest tests/

# Frontend (desde /frontend)
npm run test -- --run
```

Para el desarrollo local con base de datos y migraciones usar el flujo ya documentado del repo (`Makefile` / `docker-compose.yml` / `backend/README.md`).

---

## Orden de implementación (TDD-first)

Cada Work Unit: **(1)** escribir tests que fallan → **(2)** implementar → **(3)** correr tests → **(4)** correr la suite completa (paridad).

### WU-1 — Migración y modelo

```bash
cd backend
# Tests primero:
#   tests/unit/test_movimiento_cheque_model.py      (propiedades derivadas, constraints)
#   tests/unit/test_dates.py                        (end_of_month)
# Implementar:
#   alembic/versions/010_movimiento_cheque.py
#   src/app/models/movimiento.py   (+instrumento, +fecha_liquidacion, +fecha_liquidado, subtotal nullable, CHECKs, helpers de fecha efectiva)
#   src/app/core/dates.py          (+end_of_month)

alembic upgrade head
alembic downgrade -1      # debe abortar con mensaje claro si hay cheques pendientes
alembic upgrade head
python -m pytest tests/unit -v
```

### WU-2 — Núcleo de saldo y proyección (lógica pura + paridad)

```bash
# Tests primero:
#   tests/unit/test_saldo_futuro.py                 (proyección pura: acumulado, agrupación, vencidos, ARS/USD)
#   tests/integration/test_saldo_service.py         (suma vs último subtotal; cheques pendientes excluidos)
#   tests/integration/test_cajas_saldo_moneda.py    (paridad /saldo y /saldo-general)
# Implementar:
#   src/app/services/saldo_futuro.py
#   src/app/services/saldo_service.py
#   src/app/api/routes/cajas.py, src/app/services/caja_service.py  (usar saldo_service)

python -m pytest tests/unit/test_saldo_futuro.py tests/integration/test_cajas_saldo_moneda.py -v
```

### WU-3 — Schemas de API

```bash
# Tests primero:  tests/unit/test_movimiento_cheque_schema.py
#   fecha_liquidacion: obligatoria con cheque, prohibida sin cheque, > hoy, formato; cheque + complementario → error;
#   update: instrumento "ninguno" → error; DTO de respuesta (estado, subtotal null, liquidable)
# Implementar:  src/app/schemas/movimiento.py  (+ nuevos DTOs de cheques/saldo futuro)
python -m pytest tests/unit/test_movimiento_cheque_schema.py -v
```

### WU-4 — Servicio de movimientos (cheques)

```bash
# Tests primero:
#   tests/unit/test_movimiento_service.py  (create cheque sin stream; liquidar; recálculo; update/delete de pendientes)
#   tests/integration/test_movimiento_service.py
# Implementar:  src/app/services/movimiento_service.py
python -m pytest tests/unit tests/integration/test_movimiento_service.py -v
```

### WU-5 — Endpoints

```bash
# Tests primero:
#   tests/integration/test_cheques_api.py           (crear/no impacto/liquidar/409/RBAC)
#   tests/integration/test_cheques_seccion_api.py   (/cheques aptos/próximos/paginación)
#   tests/integration/test_saldo_futuro_api.py
#   tests/integration/test_movimientos_api.py, test_movimiento_edit_delete.py, test_consulta_rbac.py (extender)
# Implementar:
#   src/app/api/routes/movimientos.py  (+POST liquidar, +GET cheques-pendientes, cambios list/create/update)
#   src/app/api/routes/cajas.py        (+GET saldo-futuro)
#   src/app/api/routes/cheques.py      (NUEVO: GET /cheques)
#   src/app/api/router.py              (registrar cheques)
python -m pytest tests/integration -v
```

### WU-6 — Informe PDF

```bash
# Tests primero:  tests/unit/test_pdf_informe_renderer.py, tests/unit/test_informe_service.py, tests/integration/test_informes_api.py
# Implementar:    src/app/services/informe_service.py, src/app/services/pdf_informe_renderer.py, src/app/api/routes/informes.py
python -m pytest tests/ -v
```

### WU-7..10 — Frontend

```bash
cd frontend
# Tests primero (frontend/tests/):
#   MovimientoForm.test.tsx            (instrumento, fecha de liquidación, oculta "Entrada y Salida", reset)
#   ChequesPendientesBlock.test.tsx    (Liquidar solo secretaria; solo lectura en Consulta)
#   SaldoFuturoDesplegable.test.tsx    (carga al expandir, filas acumuladas, vencidos, ARS/USD, vacío)
#   ChequesPage.test.tsx               (dos listados, paginación, Liquidar solo secretaria)
#   Navbar.test.tsx, AppRoutes.test.tsx (enlace "Cheques" entre "Consulta plazos fijos" e "Impresión"; ambos roles)
# Implementar:
#   src/services/api.ts, src/components/{MovimientoForm,MovimientoTable,ChequesPendientesBlock,SaldoFuturoDesplegable}.tsx,
#   src/pages/{RegistroCajaPage,ConsultaCajaPage,ChequesPage}.tsx, src/components/layout/Navbar.tsx, src/App.tsx, src/index.css

npm run test -- --run
npm run build
```

---

## Verificación manual (obligatoria por constitución: ambos roles)

### Como Secretaria

1. **Registro** → caja con saldo ARS conocido (ej. 1000). El desplegable **Instrumento** aparece entre *Fecha (opcional)* y *Entrada*, con `-` por defecto.
2. Con `-`: registrar entrada/salida normal → comportamiento idéntico al anterior.
3. Elegir **Cheque** → aparece **Fecha de liquidación**; el botón **Entrada y Salida** desaparece/queda deshabilitado.
4. Intentar fecha de liquidación vacía, **hoy** o pasada → rechazo con mensaje claro; no se crea nada.
5. Cheque **Entrada 500** con liquidación D1 (futura) → aparece en el bloque **cheques pendientes** (arriba del historial); **Valor de caja no cambia**.
6. Cheque **Salida 200** con liquidación D2 > D1 → idem.
7. Expandir **Saldo a futuro** → `Hoy 1000 · D1 1500 · D2 1300`.
8. **Editar** un cheque pendiente (monto/fecha) → sin cambios en Valor de caja. Cambiar Cheque ↔ Echeque OK; no existe opción `-`.
9. **Liquidar** el cheque de entrada → desaparece de pendientes; pasa al historial con su subtotal; Valor de caja = 1500; botón Liquidar ya no aparece.
10. **Cheques** (menú entre *Consulta plazos fijos* e *Impresión*): cheques con fecha ≤ hoy en **Aptos para liquidar**; con fecha dentro del mes en **Próximos a liquidar este mes**; **Liquidar** disponible desde ahí.
11. **Impresión** → informe de Caja: movimientos sin cheques pendientes; sección **Cheques pendientes**; **Saldo a futuro** idéntico a pantalla.

### Como Escribano

1. **Consulta** → ve Valor de caja, bloque de cheques pendientes (**sin** botones), y **Saldo a futuro**.
2. **Cheques** → ve ambos listados **sin** botón Liquidar.
3. Intento directo por API de crear/editar/eliminar/liquidar → `403`.
4. **Impresión** → el informe de Caja incluye las mismas secciones.

### Casos de borde

- Liquidar dos veces (doble clic / dos pestañas) → la segunda responde `409`, el saldo no se duplica.
- Cajas adicionales con un cheque → se crea un cheque pendiente independiente en cada caja.
- Movimientos históricos (previos a la feature) → sin cambios en subtotales ni orden.
- Subtotal general / Valor en conjunto → no incluyen cheques pendientes.

---

## Criterios de salida

- Suite de backend y frontend en verde (incluidos tests de paridad).
- `alembic upgrade head` / `downgrade -1` / `upgrade head` sin errores sobre una base con datos.
- Verificación manual con ambos roles completada.
- Sin secretos ni datos sensibles en logs (`rol`/`username` sí; montos no).
