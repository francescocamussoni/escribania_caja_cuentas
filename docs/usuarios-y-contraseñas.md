# Gestión de usuarios y contraseñas

La aplicación tiene dos roles. **No existe panel de administración de usuarios** ni
endpoints REST para crear, editar o eliminar usuarios; la gestión es por bootstrap,
seed de desarrollo o intervención directa en base de datos.

Cada usuario **sí** puede cambiar **su propia** contraseña desde la UI (login o menú
del nombre). El script en EC2 queda como **rescate** (usuario bloqueado, alta inicial,
reset operativo).

## Roles

| Rol | Permisos en la app | Pantallas |
|-----|-------------------|-----------|
| **secretaria** | Registrar, editar y eliminar movimientos; consultar | `/registro`, `/consulta` |
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

- Las **15 cajas** del catálogo
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

## Alta de un escribano (producción)

No hay API. Opción recomendada: script Python dentro del contenedor en EC2.

### Vía SSM Session Manager + Docker

1. Conectarse a la instancia EC2 (Session Manager en consola AWS).
2. Identificar el contenedor: `docker ps`
3. Ejecutar (reemplazar usuario y contraseña):

```bash
docker exec -i <container_id> python <<'PY'
from app.db.session import SessionLocal
from app.models.usuario import Usuario
from app.core.security import hash_password
from sqlalchemy import select

username = "nombre.escribano"
password = "ContraseñaSegura123!"
rol = "escribano"

db = SessionLocal()
try:
    if db.scalar(select(Usuario).where(Usuario.username == username)):
        print(f"Usuario {username} ya existe")
    else:
        db.add(Usuario(
            username=username,
            password_hash=hash_password(password),
            rol=rol,
        ))
        db.commit()
        print(f"Usuario {username} creado ({rol})")
finally:
    db.close()
PY
```

### Vía desarrollo local (misma BD remota — no recomendado)

Solo si tenés `DATABASE_URL` de RDS accesible; preferir el método en EC2.

## Alta de una secretaria adicional

Mismo procedimiento que escribano, con `rol = "secretaria"`.

## Cambiar contraseña (rescate operativo)

Usar el autoservicio salvo que el usuario no pueda autenticarse. El script **debe**
actualizar `password_changed_at` para invalidar sesiones JWT vigentes (igual que la API).

```bash
docker exec -i <container_id> python <<'PY'
from datetime import datetime, timezone

from app.db.session import SessionLocal
from app.models.usuario import Usuario
from app.core.security import hash_password
from sqlalchemy import select

username = "prod-admin"
new_password = "NuevaContraseñaSegura!"

db = SessionLocal()
try:
    user = db.scalar(select(Usuario).where(Usuario.username == username))
    if user is None:
        print(f"Usuario {username} no encontrado")
    else:
        user.password_hash = hash_password(new_password)
        user.password_changed_at = datetime.now(timezone.utc)
        db.commit()
        print(f"Contraseña actualizada para {username}")
finally:
    db.close()
PY
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
| Usuario escribano de prueba | `make seed` | Crear manualmente (script arriba) |
| Cambiar contraseña | UI login o menú del nombre | Mismo autoservicio; script EC2 solo como rescate |
| Panel de usuarios | No existe | No existe (futuro) |
