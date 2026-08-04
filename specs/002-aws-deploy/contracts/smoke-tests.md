# Smoke Test Contract — Post-Despliegue AWS

**Feature**: `002-aws-deploy`  
**Version**: 1.0.0  
**Purpose**: Contrato verificable (FR-011) que define las comprobaciones obligatorias
tras cada despliegue o actualización en producción.

## Variables de entrada

| Variable | Descripción | Ejemplo |
|----------|-------------|---------|
| `BASE_URL` | URL pública HTTPS (sin trailing slash) | `https://d111111abcdef8.cloudfront.net` |
| `ADMIN_USER` | Usuario admin provisionado en producción | `prod-admin` |
| `ADMIN_PASS` | Contraseña admin (desde secret, no loguear) | `***` |

## Casos de prueba

### ST-001 — Health check API

```http
GET {BASE_URL}/api/health
```

**Expect**:
- Status: `200`
- Body JSON: `{ "status": "ok" }`

---

### ST-002 — HTTPS obligatorio

```http
GET http://{cloudfront-host}/login
```

**Expect**:
- Status: `301` o `302` o conexión upgrade a HTTPS
- Location header (si redirect): comienza con `https://`

---

### ST-003 — Frontend accesible

```http
GET {BASE_URL}/login
```

**Expect**:
- Status: `200`
- Body contiene texto `Iniciar sesión` (o equivalente SPA)

---

### ST-004 — Credenciales de desarrollo rechazadas

```http
POST {BASE_URL}/api/v1/auth/login
Content-Type: application/json

{ "username": "admin", "password": "admin" }
```

**Expect**:
- Status: `401`
- No devuelve `access_token`

---

### ST-005 — Login admin de producción

```http
POST {BASE_URL}/api/v1/auth/login
Content-Type: application/json

{ "username": "{ADMIN_USER}", "password": "{ADMIN_PASS}" }
```

**Expect**:
- Status: `200`
- Body contiene: `access_token`, `rol` (valor `secretaria` para admin bootstrap)

---

### ST-006 — Catálogo de 15 cajas

```http
GET {BASE_URL}/api/v1/cajas
Authorization: Bearer {token_from_ST-005}
```

**Expect**:
- Status: `200`
- Body: array de longitud `15`
- Cada elemento tiene `id`, `nombre`, `slug`

---

### ST-007 — Base vacía de movimientos

```http
GET {BASE_URL}/api/v1/cajas/1/movimientos?page=1
Authorization: Bearer {token_from_ST-005}
```

**Expect**:
- Status: `200`
- Body: `total_items` = `0`, `items` = `[]`

---

### ST-008 — Saldo inicial cero

```http
GET {BASE_URL}/api/v1/cajas/1/saldo
Authorization: Bearer {token_from_ST-005}
```

**Expect**:
- Status: `200`
- Body: `saldo_actual` = `"0.00"` (o equivalente sin movimientos)

## Criterio de aprobación

Todos los casos ST-001 a ST-008 deben pasar para considerar el despliegue exitoso.

## Implementación prevista

Script: `scripts/smoke-aws.sh` (bash + curl). Salida exitosa: exit code `0`;
fallo en cualquier caso: exit code `1` con mensaje del caso fallido.

## Fuera de alcance de este contrato

- Tests de regresión funcional completos de `001-registro-cajas` (cubiertos por suite existente).
- Pruebas de carga o penetración.
- Verificación de restauración desde backup RDS.
