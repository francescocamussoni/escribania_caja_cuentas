# Mount Alignment: Auth Change Password API

**Feature**: `005-cambio-clave-consulta-conjunto`  
**Task**: T002 — cross-check OpenAPI vs `backend/src/app/api/router.py` y `backend/src/app/api/routes/auth.py`  
**Date**: 2026-08-14

## Stack de montaje actual

```text
main.py          → app.include_router(api_router, prefix="/api/v1")
api/router.py    → api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
auth.py          → APIRouter()  (hoy: POST /login)
```

## Contrato OpenAPI (005) — paths declarados

| OpenAPI path | Método | operationId | Auth |
|--------------|--------|-------------|------|
| `/api/v1/auth/change-password` | POST | `changePasswordPublic` | ninguna |
| `/api/v1/auth/me/password` | POST | `changePasswordAuthenticated` | Bearer JWT |

## Alineación ✅ (planeado)

Los endpoints nuevos van en el **mismo** `auth.router` (no hace falta `include_router` extra).

### Registro planeado (T013 / T018)

```python
# backend/src/app/api/routes/auth.py  (router ya montado en /auth)

@router.post("/change-password", status_code=204)
def change_password_public(...): ...

@router.post("/me/password", status_code=204)
def change_password_me(...): ...
```

### URL efectiva

| Método | URL |
|--------|-----|
| POST | `/api/v1/auth/change-password` |
| POST | `/api/v1/auth/me/password` |

Coincide con OpenAPI: `/api/v1` + `/auth` + path del handler.

## Notas de implementación (no T002)

1. `change-password` público: sin `HTTPBearer`; 401 genérico como login.
2. `me/password`: `Depends(get_current_user)`; sujeto = JWT `sub`, no username en body.
3. Consulta conjunta **no** añade rutas; reutiliza `GET /api/v1/cajas/{id}/saldo` y `GET /api/v1/cajas/{id}/movimientos`.

## Resultado T002

**PASS** — Contrato alineado con el patrón existente `/api/v1` + `/auth`. Listo para T013 y T018.
