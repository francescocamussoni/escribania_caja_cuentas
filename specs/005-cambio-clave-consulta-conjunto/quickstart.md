# Quickstart: Cambio de Contraseña y Consulta Conjunta de Cajas

**Feature**: `005-cambio-clave-consulta-conjunto`  
**Branch**: `005-cambio-clave-consulta-conjunto`  
**Depends on**: `001-registro-cajas` (auth, consulta individual)

> Documentación operativa: [docs/README.md](../../docs/README.md) · [usuarios y contraseñas](../../docs/usuarios-y-contraseñas.md)

## Prerequisites

- Stack local (`make up`, migraciones aplicadas — incluye `005_usuario_password_changed_at`)
- Usuarios seed: `admin` / `admin` (secretaria), `escribano` / `escribano`

## 1. Levantar entorno

```bash
git checkout 005-cambio-clave-consulta-conjunto
make up
make migrate
```

## 2. Verificar API — cambio de contraseña (tras implementación)

Cambio **público** (login), luego login con la nueva clave:

```bash
curl -s -o /dev/null -w "%{http_code}\n" -X POST http://localhost:8000/api/v1/auth/change-password \
  -H 'Content-Type: application/json' \
  -d '{
    "username": "escribano",
    "current_password": "escribano",
    "new_password": "NuevaClave1",
    "new_password_confirm": "NuevaClave1"
  }'
# Esperado: 204

TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"escribano","password":"NuevaClave1"}' | jq -r .access_token)
echo "$TOKEN" | wc -c   # token no vacío
```

Cambio **autenticado** e invalidación del token anterior:

```bash
OLD=$TOKEN
curl -s -o /dev/null -w "%{http_code}\n" -X POST http://localhost:8000/api/v1/auth/me/password \
  -H "Authorization: Bearer $OLD" \
  -H 'Content-Type: application/json' \
  -d '{
    "current_password": "NuevaClave1",
    "new_password": "OtraClave12",
    "new_password_confirm": "OtraClave12"
  }'
# Esperado: 204

curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/api/v1/cajas \
  -H "Authorization: Bearer $OLD"
# Esperado: 401
```

Credenciales inválidas (mensaje genérico, sin enumerar usuario):

```bash
curl -s -w "\n%{http_code}\n" -X POST http://localhost:8000/api/v1/auth/change-password \
  -H 'Content-Type: application/json' \
  -d '{
    "username": "no-existe",
    "current_password": "x",
    "new_password": "NuevaClave1",
    "new_password_confirm": "NuevaClave1"
  }'
# Esperado: 401 y detail igual al de login fallido
```

## 3. Verificar UI

1. Abrir `http://localhost:5173/login`.
2. Pulsar **Cambiar contraseña** → el formulario de ingreso se reemplaza.
3. Completar cambio de `admin` (o restaurar seed si se cambió en el paso 2) y **Cancelar** o éxito → vuelve el login.
4. Ingresar; tocar el **nombre de usuario** arriba a la derecha → cambiar clave → redirige a login; el token viejo no accede.
5. **Consulta**: una caja, sin marcas adicionales → mismo valor + historial de siempre.
6. Marcar otras cajas en **Ver en conjunto con otras cajas**, Consulta:
   - **Valor en conjunto** arriba = suma de los saldos mostrados.
   - Solapas **cerradas**; primera = desplegable; resto orden catálogo.
   - Expandir una: historial de esa caja; paginar no afecta las demás.

## 4. Tests

```bash
make test-backend
make test-frontend
```

Criterio: suites verdes; escenarios de `spec.md` US1–US4 cubiertos por tests TDD.

## 5. Restaurar usuarios de desarrollo

Si se cambiaron claves en esta guía, volver a `make seed` (solo `ENVIRONMENT=development`) o actualizar hashes según [usuarios-y-contraseñas.md](../../docs/usuarios-y-contraseñas.md).
