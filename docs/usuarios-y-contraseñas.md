# Gestión de usuarios y contraseñas

La aplicación tiene dos roles. **No existe panel de administración de usuarios** ni
endpoints REST para crear, editar o eliminar usuarios; la gestión es por bootstrap,
seed de desarrollo o intervención directa en base de datos.

Cada usuario **sí** puede cambiar **su propia** contraseña desde la UI (login o menú
del nombre). El alta inicial y el reset operativo se hacen con
`scripts/aws-create-user.sh` (o `python -m app.create_user` en el contenedor).

## Roles

| Rol | Permisos en la app | Pantallas |
|-----|-------------------|-----------|
| **secretaria** | Registrar, editar y eliminar movimientos; consultar; alta/archivo de cajas | `/registro`, `/consulta`, `/configuracion` |
| **escribano** | Solo consulta (saldo e historial) | `/consulta` |

El rol se almacena en `usuario.rol` y viaja en el JWT (`rol` claim). El backend
aplica RBAC con `require_role("secretaria")` en rutas de escritura.

## Usuarios por entorno

### Desarrollo local

Tras `make seed` (`backend/src/app/seed.py`):

| Usuario | Contraseña | Rol | Notas |
|---------|------------|-----|-------|
| `admin` (o `ADMIN_USERNAME`) | `admin` (o `ADMIN_PASSWORD`) | secretaria | Configurable en `.env` |
| `escribano` | `escribano` | escribano | Fijo en seed; solo dev |

`seed.py` **falla** si `ENVIRONMENT=production`.

Además, cada arranque del contenedor ejecuta `bootstrap_production`, que crea el
admin y las cajas si no existen (idempotente).

### Producción (AWS)

Tras el primer deploy, `bootstrap_production` crea:

- Las **15 cajas** iniciales del catálogo de seed (altas posteriores vía Configuración)
- **Un usuario admin** con credenciales de SSM:
  - `ADMIN_USERNAME` ← `/escribania/prod/admin_username`
  - `ADMIN_PASSWORD` ← `/escribania/prod/admin_password`

**No se crea** el usuario `escribano` de desarrollo. Las credenciales `admin`/`admin`
**no funcionan** en producción (smoke test ST-004).

## Dónde viven las contraseñas

| Entorno | Almacenamiento | Rotación |
|---------|----------------|----------|
| Local | `.env` → variables del contenedor | Editar `.env` y recrear usuario en BD |
| AWS | SSM Parameter Store (`SecureString`) | AWS Console / CLI + actualizar BD si aplica |

El hash bcrypt está en PostgreSQL (`usuario.password_hash`). SSM guarda la contraseña
en texto para bootstrap inicial; **cambiar la contraseña de un usuario existente**
por autoservicio actualiza la tabla `usuario` (hash + `password_changed_at`). Un
cambio solo en SSM **no** actualiza al usuario ya creado (`bootstrap_production` no
sobrescribe).

## Autoservicio (recomendado)

Secretaria y escribano cambian **solo su** clave. No hay recuperación por correo ni
reset por otro usuario desde la app.

| Dónde | Cómo |
|-------|------|
| Pantalla de **login** | Enlace **Cambiar contraseña** (sustituye el formulario). Body: `username`, `current_password`, `new_password`, `new_password_confirm` → `POST /api/v1/auth/change-password` |
| **Dentro de la app** | Clic en el nombre (arriba a la derecha) → misma terna de claves → `POST /api/v1/auth/me/password` (JWT). Luego logout y volver a ingresar |

Reglas: mínimo **8** caracteres; distinta de la actual; confirmación igual. 401 genérico
si usuario o clave actual no coinciden (flujo público). Tras éxito se setea
`password_changed_at` y los JWT con `iat` anterior dejan de valer.

No hay que tocar EC2 ni SSM para un cambio rutinario. Si se cambia el admin de
bootstrap, conviene alinear SSM `admin_password` para documentación y futuros
reprocesos.

## Alta de usuarios (producción)

No hay API. Crear secretaria o escribano con el script operativo. **Pedirá la
contraseña dos veces** (no se ve en pantalla ni se pasa con `--password`).

El script corre contra el contenedor que ya está en EC2 (no hace falta un
deploy previo). Tras desplegar esta versión, también podés usar
`python -m app.create_user` si estás en la instancia.

### Desde tu máquina (recomendado)

```bash
./scripts/aws-create-user.sh --username juan.perez --rol escribano
# o
make create-user-aws ARGS='--username juan.perez --rol escribano'

# Secretaria adicional:
./scripts/aws-create-user.sh --username maria.secretaria --rol secretaria
```

El script:

1. Pide **Contraseña** y **Confirmar contraseña**.
2. La guarda unos segundos en SSM Parameter Store (`SecureString` bajo
   `/escribania/prod/ops/…`) y la borra al terminar.
3. En EC2, el contenedor `escribania-api` crea el usuario con hash bcrypt.
4. Entregá la clave al usuario por un canal aparte; puede cambiarla después
   desde el login.

Roles: `escribano` (consulta) o `secretaria` (registro + consulta).

### Si ya estás en la instancia (Session Manager)

```bash
docker exec -it escribania-api python -m app.create_user \
  --username juan.perez --rol escribano
```

También pide la contraseña de forma interactiva.

### Reset operativo (usuario bloqueado)

Usar el autoservicio salvo que el usuario no pueda autenticarse. El reset
**debe** actualizar `password_changed_at` para invalidar sesiones JWT vigentes.

```bash
./scripts/aws-create-user.sh --username juan.perez --reset

# o en EC2:
docker exec -it escribania-api python -m app.create_user \
  --username juan.perez --reset
```

Si cambiás la contraseña del admin de bootstrap, actualizá también SSM
(`admin_password`) para que documentación y futuros reprocesos coincidan, aunque
`bootstrap_production` **no sobrescribe** usuarios existentes.

## Cambiar credenciales admin antes del primer deploy

Editar `infra/environments/prod.tfvars`:

```hcl
admin_username = "prod-admin"
admin_password = "<nueva-contraseña>"
```

Luego `terraform apply` (crea/actualiza SSM) y deploy. En el **primer** arranque,
bootstrap crea el usuario con esas credenciales.

## Eliminar un usuario

```sql
-- Solo si no tiene movimientos asociados como created_by
DELETE FROM usuario WHERE username = 'nombre.escribano';
```

Si el usuario creó movimientos, la FK `movimiento.created_by` impide el borrado;
en ese caso desactivar por política de negocio (no implementado) o no eliminar.

## Seguridad

- Contraseñas hasheadas con **bcrypt**; nunca se almacenan en texto plano en BD
- JWT expira en **8 horas** (`JWT_EXPIRE_HOURS`); incluye `iat`. Tras un cambio de clave,
  tokens anteriores reciben 401
- Tokens en **sessionStorage** (frontend); se pierden al cerrar pestaña o al logout post-cambio
- No loguear contraseñas ni tokens en aplicación
- `make check-secrets` antes de cada merge

## Resumen rápido

| Acción | Desarrollo | Producción |
|--------|------------|------------|
| Primer admin | `.env` + `make seed` | SSM + `bootstrap_production` |
| Usuario escribano / secretaria extra | `make seed` | `./scripts/aws-create-user.sh --username … --rol …` |
| Cambiar contraseña | UI login o menú del nombre | Mismo autoservicio; `--reset` solo como rescate |
| Panel de usuarios | No existe | No existe (futuro) |
