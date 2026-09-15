# Quickstart: 009-entrada-salida-fecha

**Branch**: `009-entrada-salida-fecha`

## Prerequisitos

```bash
# Estar en la rama correcta
git checkout 009-entrada-salida-fecha

# Backend (desde /backend)
python -m pytest tests/  # suite base debe pasar antes de empezar

# Frontend (desde /frontend)
npm run test -- --run   # suite base debe pasar antes de empezar
```

---

## Orden de implementación (TDD-first)

### WU-1: Migración `fecha_override`

```bash
cd backend

# 1. Crear archivo de migración
# → backend/alembic/versions/009_movimiento_fecha_override.py

# 2. Aplicar migración
alembic upgrade head

# 3. Verificar reversibilidad
alembic downgrade -1
alembic upgrade head

# 4. Actualizar modelo ORM
# → backend/src/app/models/movimiento.py
# añadir: fecha_override: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
```

---

### WU-2: Schema `fecha_manual`

```bash
cd backend

# Escribir tests primero (TDD):
# → backend/tests/unit/test_movimiento_moneda.py  (añadir casos)

# Luego implementar:
# → backend/src/app/schemas/movimiento.py
#   - añadir: fecha_manual: date | None = None  con validador
#   - eliminar: validate_complementario_only_for_usd

python -m pytest tests/unit/test_movimiento_moneda.py -v
```

---

### WU-3: Servicio — par ARS y COALESCE

```bash
cd backend

# Escribir tests primero (TDD):
# → backend/tests/unit/test_movimiento_service.py  (añadir casos)

# Luego implementar:
# → backend/src/app/services/movimiento_service.py
#   - create_movimiento_pair: añadir parámetro moneda, quitar hardcode "USD"
#   - create_movimiento: ORDER BY COALESCE(fecha_override, created_at)
#   - create_movimiento: aceptar fecha_override: datetime | None
#   - recalculate_subtotals: ORDER BY COALESCE(fecha_override, created_at)

python -m pytest tests/unit/ -v
```

---

### WU-4: Endpoint y response

```bash
cd backend

# Escribir tests de integración primero (TDD):
# → backend/tests/integration/test_movimientos_api.py  (añadir casos)

# Luego implementar:
# → backend/src/app/api/routes/movimientos.py
#   - calcular fecha_override desde payload.fecha_manual
#   - pasar moneda a create_movimiento_pair
# → backend/src/app/schemas/movimiento.py
#   - movimiento_to_response: fecha = movimiento.fecha_override or movimiento.created_at

python -m pytest tests/ -v
```

---

### WU-5: Frontend

```bash
cd frontend

# Crear tests primero (TDD):
# → frontend/src/components/MovimientoForm.test.tsx  (archivo nuevo)

# Luego implementar:
# → frontend/src/services/api.ts
#   - añadir fecha_manual?: string a CreateMovimientoPayload
# → frontend/src/components/MovimientoForm.tsx
#   - eliminar pendingTipo, dialog JSX
#   - añadir estado fechaManual
#   - añadir <input type="date">
#   - añadir botón "Entrada y Salida"

npm run test -- --run
```

---

## Verificación final

```bash
# Backend — suite completa
cd backend && python -m pytest tests/ -v

# Frontend — suite completa  
cd frontend && npm run test -- --run

# Flujo manual: abrir app, seleccionar caja, probar:
# 1. Botón "Entrada" con moneda USD → no aparece diálogo
# 2. Botón "Entrada y Salida" con ARS → dos registros en historial
# 3. Selector de fecha → fecha en historial = fecha elegida a las 09:00
# 4. Sin fecha → fecha en historial = hora actual
```

---

## Variables de entorno relevantes

No se requieren variables de entorno nuevas para esta feature. Las existentes en `.env` son suficientes.

---

## Nota sobre zona horaria

El backend usa `ZoneInfo("America/Argentina/Buenos_Aires")` (ya importado en `movimientos.py` como `_ARGENTINA_TZ`). La construcción de `fecha_override` debe reutilizar esta constante:

```python
from zoneinfo import ZoneInfo
_ARGENTINA_TZ = ZoneInfo("America/Argentina/Buenos_Aires")  # ya existe en routes/movimientos.py

fecha_override = datetime(
    payload.fecha_manual.year,
    payload.fecha_manual.month,
    payload.fecha_manual.day,
    9, 0, 0,
    tzinfo=_ARGENTINA_TZ,
)
```
