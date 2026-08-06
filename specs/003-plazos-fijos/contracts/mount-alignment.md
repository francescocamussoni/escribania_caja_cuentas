# Mount Alignment: Plazos Fijos API

**Feature**: `003-plazos-fijos`  
**Task**: T002 — cross-check OpenAPI vs `backend/src/app/api/router.py`  
**Date**: 2026-08-06

## Stack de montaje actual (feature 001)

```text
main.py          → app.include_router(api_router, prefix="/api/v1")
api/router.py    → api_router.include_router(cajas.router, prefix="/cajas")
                 → api_router.include_router(movimientos.router, prefix="/cajas")
movimientos.py   → @router.get("/{caja_id}/movimientos")
```

URL efectiva movimientos: `GET /api/v1/cajas/{caja_id}/movimientos`

## Contrato OpenAPI (003) — paths declarados

| OpenAPI path | Métodos | operationId |
|--------------|---------|-------------|
| `/api/v1/cajas/{cajaId}/plazos-fijos/resumen` | GET | `getPlazosFijosResumen` |
| `/api/v1/cajas/{cajaId}/plazos-fijos` | GET, POST | `listPlazosFijos`, `createPlazoFijo` |
| `/api/v1/cajas/{cajaId}/plazos-fijos/{plazoFijoId}` | PATCH, DELETE | `updatePlazoFijo`, `deletePlazoFijo` |

## Alineación ✅

El contrato sigue el **mismo patrón** que movimientos: prefijo global `/api/v1` + router
`/cajas` + rutas anidadas bajo `{caja_id}`.

### Registro planeado en T012/T013

```python
# backend/src/app/api/router.py
from app.api.routes import plazos_fijos

api_router.include_router(plazos_fijos.router, prefix="/cajas", tags=["plazos-fijos"])
```

```python
# backend/src/app/api/routes/plazos_fijos.py
router = APIRouter()

@router.get("/{caja_id}/plazos-fijos/resumen", ...)
@router.get("/{caja_id}/plazos-fijos", ...)
@router.post("/{caja_id}/plazos-fijos", ...)
@router.patch("/{caja_id}/plazos-fijos/{plazo_fijo_id}", ...)
@router.delete("/{caja_id}/plazos-fijos/{plazo_fijo_id}", ...)
```

### URLs efectivas (implementación)

| Método | URL |
|--------|-----|
| GET | `/api/v1/cajas/{caja_id}/plazos-fijos/resumen` |
| GET | `/api/v1/cajas/{caja_id}/plazos-fijos?page=1&page_size=20` |
| POST | `/api/v1/cajas/{caja_id}/plazos-fijos` |
| PATCH | `/api/v1/cajas/{caja_id}/plazos-fijos/{plazo_fijo_id}` |
| DELETE | `/api/v1/cajas/{caja_id}/plazos-fijos/{plazo_fijo_id}` |

## Notas de implementación

1. **Orden de rutas**: declarar `.../plazos-fijos/resumen` antes que rutas con más segmentos
   (igual que no hay conflicto en movimientos; `resumen` es segmento fijo, no `{id}`).

2. **Nombres de parámetros**: OpenAPI usa `cajaId` / `plazoFijoId`; FastAPI puede usar
   `caja_id` / `plazo_fijo_id` en código (convención Python). Paridad con movimientos
   (`cajaId` en spec 001, `caja_id` en rutas).

3. **Auth**: `GET` requiere JWT (secretaria + escribano); `POST/PATCH/DELETE` requiere
   `require_role("secretaria")` — alineado al contrato.

4. **Sin cambios requeridos en openapi.yaml** tras este cross-check.

## Resultado T002

**PASS** — Contrato alineado con patrón de montaje existente; listo para implementación en T012–T013.
