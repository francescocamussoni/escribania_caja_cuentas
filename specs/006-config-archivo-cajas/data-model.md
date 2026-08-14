# Data Model — Configuración y Archivo de Cajas

## Entity: Caja

**Description**: Recurso operable que puede ser seleccionado en flujos de registro/consulta cuando está activo.

**Fields**:
- `id` (UUID or integer, primary identifier)
- `nombre` (string, visible name)
- `estado` (enum: `activa` | `archivada`)
- `created_at` (datetime)
- `updated_at` (datetime)
- `archived_at` (datetime, nullable)
- `archived_by_user_id` (foreign key to Usuario, nullable)

**Validation Rules**:
- `nombre` es obligatorio y no vacío.
- `nombre` debe ser único según regla de negocio (normalizado por mayúsculas/minúsculas y espacios).
- Solo cajas en estado `activa` pueden transicionar a `archivada`.
- Una caja ya archivada no cambia estado en un segundo archivo (idempotencia).

**State Transitions**:
- `activa -> archivada` (acción autorizada por secretaria)
- `archivada -> archivada` (no-op idempotente)
- No se define reactivación en alcance de esta feature.

## Entity: EventoConfiguracionCaja

**Description**: Registro auditable de acciones de configuración sobre cajas.

**Fields**:
- `id` (UUID or integer, primary identifier)
- `caja_id` (foreign key to Caja)
- `accion` (enum: `crear` | `archivar` | `desarchivar`)
- `resultado` (enum: `exito` | `rechazo` | `error`)
- `actor_user_id` (foreign key to Usuario)
- `created_at` (datetime)
- `detalle` (string, optional reason or context)

**Validation Rules**:
- `accion`, `resultado`, `actor_user_id` son obligatorios.
- Debe existir referencia válida a `caja_id` cuando la acción actúa sobre caja existente.

## Relationships

- `Caja` 1 --- N `EventoConfiguracionCaja`
- `Usuario` 1 --- N `EventoConfiguracionCaja`

## Query/View Model Rules

- **OperativeCajaList**: representa listas usadas por desplegables/boxes y filtra `estado = activa`.
- **HistoricalDataAccess**: la consulta de movimientos históricos no depende del estado actual de la caja.

## Concurrency Considerations

- Archivo concurrente de la misma caja: primera operación muta estado; siguientes reciben resultado consistente sin doble cambio.
- Alta concurrente con mismo nombre: una creación efectiva; las demás fallan por unicidad.
