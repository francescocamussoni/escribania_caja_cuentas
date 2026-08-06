# Quickstart: Plazos Fijos por Caja

**Feature**: `003-plazos-fijos`  
**Branch**: `003-plazos-fijos`  
**Depends on**: `001-registro-cajas` (stack local y auth operativos)

> Documentación operativa: [docs/README.md](../../docs/README.md) · [frontend](../../docs/frontend.md)

## Prerequisites

- Feature base desplegada (`make up`, migraciones y seed de cajas/usuarios)
- Branch `003-plazos-fijos` checked out

## 1. Levantar entorno

```bash
git checkout 003-plazos-fijos
make up
make migrate    # incluye revisión plazo_fijo tras implementación
```

Usuarios de prueba (seed existente):

| Usuario | Rol | Uso |
|---------|-----|-----|
| `admin` | secretaria | Gestión plazos fijos |
| `escribano` | escribano | Solo consulta |

## 2. Verificar API (tras implementación)

Login:

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin"}' | jq -r .access_token)
```

Crear plazo fijo (caja id 1):

```bash
curl -s -X POST "http://localhost:8000/api/v1/cajas/1/plazos-fijos" \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "monto_ingresado": "100000.00",
    "monto_a_vencimiento": "105000.00",
    "fecha_vencimiento": "2026-12-31"
  }' | jq
```

Resumen activos:

```bash
curl -s "http://localhost:8000/api/v1/cajas/1/plazos-fijos/resumen" \
  -H "Authorization: Bearer $TOKEN" | jq
```

Listar (página 1):

```bash
curl -s "http://localhost:8000/api/v1/cajas/1/plazos-fijos?page=1" \
  -H "Authorization: Bearer $TOKEN" | jq
```

RBAC escribano (debe fallar 403):

```bash
ESC_TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"escribano","password":"escribano"}' | jq -r .access_token)

curl -s -o /dev/null -w "%{http_code}" -X POST "http://localhost:8000/api/v1/cajas/1/plazos-fijos" \
  -H "Authorization: Bearer $ESC_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"monto_ingresado":"1000.00","monto_a_vencimiento":"1100.00","fecha_vencimiento":"2027-01-01"}'
# Esperado: 403
```

## 3. Frontend (tras implementación)

| Ruta | Rol | Descripción |
|------|-----|-------------|
| `/plazos-fijos` | secretaria | Gestión CRUD |
| `/consulta-plazos-fijos` | secretaria, escribano | Consulta con botón Consulta |

```text
http://localhost:5173/plazos-fijos
http://localhost:5173/consulta-plazos-fijos
```

## 4. Tests (TDD)

```bash
make test
# o
cd backend && pytest tests/integration/test_plazos_fijos_api.py -v
cd frontend && npm test -- PlazosFijos
```

Casos críticos a cubrir:

- Orden: futuros primero (vencimiento próximo), vencidos al final
- Totales resumen solo plazos no vencidos
- `monto_a_vencimiento` < `monto_ingresado` → 400
- Editar/eliminar plazo antiguo → OK (secretaria)
- Escribano POST/PATCH/DELETE → 403

## 5. Contrato OpenAPI

Validar paridad implementación ↔ contrato:

```text
specs/003-plazos-fijos/contracts/openapi.yaml
```

Swagger UI: http://localhost:8000/docs (tras registrar rutas en `main.py`).

## 6. Despliegue AWS

Sin cambios de infra respecto a `002-aws-deploy`: nueva migración Alembic en deploy (`make migrate` en EC2 o pipeline). Frontend rebuild + sync S3.

## 7. Validación (T028)

Checklist automatizada (ejecutar tras `make up` y `make migrate`):

```bash
make test
```

| Área | Comando | Esperado |
|------|---------|----------|
| Backend plazos fijos | `docker compose exec backend pytest tests/integration/test_plazos_fijos_api.py tests/unit/test_plazo_fijo_order.py tests/unit/test_plazo_fijo_validation.py -v` | Todos green |
| Frontend US1 | `cd frontend && npm test -- PlazosFijosPage` | 6 tests |
| Frontend US2 | `cd frontend && npm test -- ConsultaPlazosFijos` | 1 test |

Walkthrough manual UI (secretaria `admin` / escribano `escribano`):

1. `/plazos-fijos` — crear plazo, ver resumen, editar/eliminar, paginar
2. `/consulta-plazos-fijos` — Consulta → resumen + tabla sin acciones
3. Escribano: sin links Registro / Plazos fijos; consulta plazos OK

Walkthrough curl: secciones 2 de este documento (login, POST, resumen, list, escribano 403).
