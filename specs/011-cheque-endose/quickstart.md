# Quickstart: 011-cheque-endose

**Branch**: `011-cheque-endose`  
**Enfoque**: TDD-first (ver `spec.md` › Testing Strategy)

## Prerequisitos

```bash
git checkout 011-cheque-endose

# Backend (desde /backend) — la suite base (incluida 010) debe pasar antes de empezar
python -m pytest tests/

# Frontend (desde /frontend)
npm run test -- --run
```

## Orden de implementación (TDD-first)

Cada Work Unit: **(1)** tests que fallan → **(2)** implementar → **(3)** correr tests → **(4)** suite completa (paridad).

### WU-1 — Migración y modelo
```bash
cd backend
# Tests: tests/unit/test_movimiento_endose_model.py (propiedades, CHECKs, índice único)
# Implementar: alembic/versions/011_movimiento_endose.py, src/app/models/movimiento.py
alembic upgrade head && alembic downgrade -1 && alembic upgrade head
python -m pytest tests/unit -v
```

### WU-2 — Servicio de endose
```bash
# Tests: tests/unit/test_movimiento_service.py, tests/integration/test_cheques_endose_service.py
#   - entrada: origen +M, destino -M (neto 0); salida: origen -M, destino +M
#   - fecha de liquidación futura OK; atomicidad (falla ⇒ cheque pendiente y sin movimiento)
#   - 2º endose / endose tras liquidar ⇒ ChequeYaLiquidadoError; destino == origen / archivada / inexistente
#   - update/delete de endosado y de destino ⇒ MovimientoEndosadoError
#   - endoses cruzados A→B y B→A concurrentes sin deadlock
python -m pytest tests/ -k "endose or endos" -v
```

### WU-3 — Schemas y endpoint
```bash
# Tests: tests/integration/test_cheques_endose_api.py, test_cheques_liquidar_api.py (regresión),
#        test_consulta_rbac.py (Escribano 403), test_movimiento_edit_delete.py (409)
python -m pytest tests/integration -k "endose or liquidar or rbac or edit_delete" -v
```

### WU-4 / WU-5 — Frontend (requieren referencia Figma, ver plan)
```bash
cd frontend
# Tests: tests/EndoseDialog.test.tsx, ChequesPendientesBlock.test.tsx, ChequesPage.test.tsx,
#        MovimientoTable.test.tsx, RegistroCajaPage.test.tsx
npm run test -- --run
npm run build
```

## Verificación manual (ambos roles)

1. **Secretaria**: Registro → caja A (ARS) → Instrumento *Cheque*, Entrada, monto 500, fecha de liquidación futura. El cheque aparece pendiente; **Liquidar** deshabilitado, **Endose** habilitado; Valor de caja sin cambios.
2. Pulsar **Endose** → ventana con las cajas (sin A) → sin selección **Confirmar** deshabilitado → elegir B → confirmar.
3. Caja A: cheque en el historial como *Liquidado · Endosado → B*, Valor de caja +500. Caja B: movimiento *Salida* 500 "Endose cheque: … (Caja A)", Valor de caja −500. Sin botones Editar/Eliminar en ambos.
4. Saldo a futuro de A y sección **Cheques**: el cheque ya no figura. Informe de Caja de A y B: ambos movimientos presentes.
5. Repetir con un cheque de **Salida** (A −M, B +M) y desde la sección **Cheques** (ambos listados).
6. Cancelar la ventana y forzar un error de red: el cheque permanece pendiente.
7. **Escribano**: sección Cheques y Consulta sin botón **Endose** ni **Liquidar**; `POST …/endosar` ⇒ 403.
8. Regresión: **Liquidar** normal sigue deshabilitado antes de la fecha y no crea movimientos en otras cajas.
