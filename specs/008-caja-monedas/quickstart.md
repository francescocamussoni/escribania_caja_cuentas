# Quickstart: Selección de Moneda en Registro de Cajas

**Feature**: `008-caja-monedas`  
**Branch**: `008-caja-monedas`

> Stack local: [docs/desarrollo-local.md](../../docs/desarrollo-local.md)

## Prerequisites

- Docker & Docker Compose (o Python 3.12 + Node 20 + PostgreSQL 16)
- Checkout de `008-caja-monedas` **después** de implementar (este archivo guía verificación)

## 1. Levantar y migrar

```bash
cp .env.example .env
make up
make migrate    # incluye 008_movimiento_moneda
make seed
```

API: http://localhost:8000/docs  
Frontend: http://localhost:5173

## 2. Tests (TDD)

Escribir/ejecutar **antes** de completar cada capa de producción:

```bash
# Backend
cd backend && pytest tests/unit/test_movimiento_service.py tests/integration/test_movimientos_api.py tests/integration/test_movimiento_edit_delete.py -q

# Casos nuevos esperados (nombres orientativos)
# test_create_usd_pair_is_atomic
# test_subtotal_does_not_mix_currencies
# test_list_filter_moneda_and_fecha
# test_saldo_returns_ars_and_usd
# test_saldo_general_does_not_sum_currencies

cd frontend && npm test -- --run
```

## 3. Verificación manual (secretaria)

1. Login secretaria. Abrir Registro de Caja.
2. Confirmar selector **Moneda** en ARS por defecto (orden: Descripción, Monto, Moneda, Entrada, Salida).
3. Registrar entrada ARS: un renglón, sin cartel; valor de caja ARS sube; USD intacto.
4. Cambiar a USD, Entrada: cartel **¿Registrar también como salida?**
   - Cancelar → un movimiento USD.
   - Confirmar → dos movimientos USD mismo monto, tipos opuestos; si se fuerza un error de persistencia, no debe quedar ninguno.
5. Listado: cada monto muestra ARS o USD. Filtrar moneda USD; filtrar rango de fechas; combinar ambos. **Valor de caja** sigue mostrando ambos saldos.
6. Escribano: ve moneda y filtros; no registra ni ve cartel.

## 4. Breaking changes de API (clientes)

| Antes | Ahora |
|-------|--------|
| `POST .../movimientos` → `Movimiento` | → `{ movimiento, complementario }` |
| `saldo_actual` | `saldo_ars` + `saldo_usd` |
| `subtotal_general` | `subtotal_general_ars` + `subtotal_general_usd` |
| GET listado sin query extra | `moneda`, `fecha_desde`, `fecha_hasta` opcionales |

Actualizar `frontend/src/services/api.ts` y pantallas de consulta conjunto.

## 5. Constitución

Tras el merge, enmendar constitución: constraint “moneda única ARS” → movimientos de caja ARS|USD, subtotal por caja **y** moneda. Plazos fijos siguen ARS.
