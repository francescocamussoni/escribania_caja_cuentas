# Mount Alignment: Informes PDF API

**Feature**: `004-impresion-caja-plazo`  
**Task**: T003 — cross-check OpenAPI vs `backend/src/app/api/router.py`  
**Date**: 2026-08-06

## Stack de montaje actual (feature 001)

```text
main.py          → app.include_router(api_router, prefix="/api/v1")
api/router.py    → api_router.include_router(cajas.router, prefix="/cajas")
```

## Contrato OpenAPI (004) — path declarado

| OpenAPI path | Método | operationId |
|--------------|--------|-------------|
| `/api/v1/informes/pdf` | POST | `generateInformePdf` |

## Alineación ✅ (planeado)

El endpoint de informes usa un router **dedicado** bajo `/informes` (no anidado en
`/cajas`), porque opera sobre parámetros de filtro en el body y devuelve `application/pdf`.

### Registro planeado en T015

```python
# backend/src/app/api/router.py
from app.api.routes import informes

api_router.include_router(informes.router, prefix="/informes", tags=["informes"])
```

```python
# backend/src/app/api/routes/informes.py
router = APIRouter()

@router.post("/pdf", ...)
```

### URL efectiva (implementación)

| Método | URL |
|--------|-----|
| POST | `/api/v1/informes/pdf` |

## Notas de implementación

1. **Content-Type**: respuesta `application/pdf` con `Content-Disposition: attachment`.
2. **Auth**: JWT requerido; roles `secretaria` y `escribano` (solo lectura).
3. **Body**: `InformePdfRequest` con `hasta_hoy`, `modo`, `tipo`, `caja_id`.

## Resultado T003

**PASS** — Contrato alineado con patrón `/api/v1` + router `/informes`; listo para T014–T015.
