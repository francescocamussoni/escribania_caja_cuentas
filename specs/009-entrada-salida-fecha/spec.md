# Feature Specification: Botón Entrada+Salida Simultáneo y Selector de Fecha

**Feature Branch**: `009-entrada-salida-fecha`  
**Created**: 2026-09-14  
**Status**: Draft  

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Registrar movimiento como Entrada y Salida simultáneamente (Priority: P1)

La secretaria necesita registrar un monto que afecta a dos streams de una misma caja al mismo tiempo (por ejemplo: entra USD y sale ARS, o viceversa). Actualmente esto requiere confirmar un diálogo emergente. La nueva funcionalidad expone un botón dedicado **"Entrada y Salida"** que efectúa ambas operaciones sin interrupciones adicionales.

**Por qué P1**: Es el cambio más disruptivo en UX y el núcleo del pedido; sin él la feature no tiene sentido. También es la pieza sobre la que se asienta la deprecación del diálogo actual.

**Independent Test**: Se puede probar en aislamiento seleccionando cualquier caja, ingresando descripción y monto, pulsando el botón **"Entrada y Salida"** y verificando que se crean dos movimientos: uno de tipo `entrada` y uno de tipo `salida` en la misma caja, con la misma descripción y monto, en la moneda seleccionada, con los subtotales correctamente recalculados.

**Acceptance Scenarios**:

1. **Given** la secretaria tiene una caja seleccionada con moneda ARS o USD, descripción y monto válidos, **When** pulsa **"Entrada y Salida"**, **Then** el sistema registra dos movimientos (entrada y salida) en la misma caja y moneda sin mostrar ningún diálogo de confirmación adicional.
2. **Given** se pulsó **"Entrada y Salida"**, **When** ambos movimientos se crean correctamente, **Then** los subtotales de la caja y moneda reflejan ambas operaciones en orden cronológico (el neto queda igual que antes de la operación).
3. **Given** la secretaria tiene cajas adicionales seleccionadas (via CajasAdicionalesSelector), **When** pulsa **"Entrada y Salida"**, **Then** el movimiento simultáneo se replica también en cada caja adicional seleccionada.
4. **Given** uno de los dos movimientos falla en el backend, **When** ocurre el error, **Then** el sistema muestra un mensaje de error claro, el formulario vuelve a su estado editable, y **ninguno** de los dos movimientos queda persistido (rollback atómico).

---

### User Story 2 - Deprecar el diálogo de confirmación complementario (Priority: P1)

El diálogo modal que aparece al registrar una entrada o salida con moneda USD preguntando "¿Registrar también como salida?" / "¿Registrar también como entrada?" será eliminado. El nuevo botón **"Entrada y Salida"** reemplaza completamente esa funcionalidad.

**Por qué P1**: Va de la mano con US1 — ambos deben entregarse juntos para no dejar la UX en un estado inconsistente.

**Independent Test**: Seleccionar moneda USD, ingresar descripción y monto, pulsar **"Entrada"** o **"Salida"** y verificar que el movimiento se registra directamente sin que aparezca ningún diálogo modal.

**Acceptance Scenarios**:

1. **Given** moneda seleccionada es USD, **When** la secretaria pulsa **"Entrada"**, **Then** el movimiento de entrada se registra inmediatamente sin mostrar el diálogo de complementario.
2. **Given** moneda seleccionada es USD, **When** la secretaria pulsa **"Salida"**, **Then** el movimiento de salida se registra inmediatamente sin mostrar el diálogo de complementario.
3. **Given** moneda seleccionada es ARS, **When** la secretaria pulsa **"Entrada"** o **"Salida"**, **Then** el comportamiento no cambia respecto a la versión anterior (sin diálogo, registro directo).
4. **Given** el campo `registrar_complementario` existe en el backend, **When** se presiona **"Entrada"** o **"Salida"**, **Then** ese campo se envía siempre en `false` (el campo puede mantenerse para compatibilidad pero no se usa en la UI).

---

### User Story 3 - Selector de fecha para registrar movimientos en fecha específica (Priority: P2)

La secretaria puede necesitar registrar un movimiento con una fecha distinta a la actual (por ejemplo, para corregir un olvido del día anterior). El formulario expone un selector de fecha opcional; si se usa, el movimiento se guarda con esa fecha a las 09:00 AM. Si se deja vacío, el comportamiento actual se mantiene (fecha y hora exacta del momento del registro).

**Por qué P2**: Es independiente de US1/US2 y agrega valor operativo sin bloquear la entrega del núcleo. Se puede implementar y probar por separado.

**Independent Test**: Seleccionar una caja, completar descripción y monto, elegir una fecha del pasado en el selector, pulsar **"Entrada"** y verificar que el movimiento aparece con la fecha seleccionada a las 09:00 AM (no la fecha/hora actual).

**Acceptance Scenarios**:

1. **Given** el selector de fecha está vacío (estado por defecto), **When** la secretaria registra cualquier movimiento, **Then** el movimiento se guarda con la fecha y hora exacta del momento del registro (comportamiento actual preservado).
2. **Given** la secretaria seleccionó una fecha específica en el selector, **When** pulsa **"Entrada"**, **"salida"** o **"Entrada y Salida"**, **Then** el movimiento se guarda con esa fecha a las 09:00 AM.
3. **Given** se registra un movimiento con fecha específica, **When** el movimiento aparece en la tabla de historial, **Then** la columna **Fecha** muestra la fecha seleccionada (no la fecha actual del servidor).
4. **Given** la secretaria selecciona una fecha futura, **When** intenta registrar el movimiento, **Then** el sistema acepta la operación (no hay restricción sobre fechas futuras).
5. **Given** la secretaria usó el selector de fecha y luego lo limpia (deja vacío), **When** registra el siguiente movimiento, **Then** ese movimiento vuelve a registrarse con la fecha/hora actual.
6. **Given** el botón **"Entrada y Salida"** se usa con fecha seleccionada, **When** se crean los dos movimientos, **Then** ambos comparten la misma fecha seleccionada a las 09:00 AM.

---

### Edge Cases

- ¿Qué pasa si la secretaria envía el formulario sin descripción o monto con el nuevo botón? → La validación existente aplica igual que para Entrada/Salida simples.
- ¿Qué pasa si se selecciona una fecha con el selector y luego se cambia de caja? → El selector de fecha no se resetea al cambiar de caja (es una preferencia de sesión).
- ¿Qué pasa si el backend rechaza la fecha (formato inválido)? → El sistema muestra un mensaje de error genérico y el formulario permanece editable.
- ¿Qué pasa con el recálculo de subtotales cuando se inserta un movimiento en una fecha pasada? → El backend ya ordena por fecha; insertar en el pasado puede reordenar el historial y recalcular subtotales. Este comportamiento es responsabilidad del backend y no del alcance de esta feature (fuera de scope definir la regla de recalculo retroactivo; la feature solo permite enviar la fecha).
- ¿Qué pasa si el botón **"Entrada y Salida"** se usa con cajas adicionales y una de las cajas adicionales falla? → Se muestra error y el usuario debe reintentar. No hay rollback parcial garantizado en esta versión.
- ¿Qué pasa si uno de los dos movimientos del par falla en el backend? → El par Entrada+Salida DEBE ejecutarse dentro de una única transacción de base de datos (atómico). Si falla cualquiera de los dos, ninguno se persiste; el sistema muestra un mensaje de error genérico y el formulario vuelve a estado editable.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El formulario de registro DEBE mostrar un tercer botón de acción etiquetado **"Entrada y Salida"** ubicado a la derecha del botón **"Salida"** (o en posición equivalente según el layout acordado).
- **FR-002**: Al pulsar **"Entrada y Salida"**, el sistema DEBE registrar simultáneamente un movimiento de tipo `entrada` y uno de tipo `salida` en la misma caja, misma moneda, misma descripción y mismo monto. Ambos movimientos DEBEN crearse dentro de una única transacción atómica — si uno falla, ninguno se persiste.
- **FR-003**: El botón **"Entrada y Salida"** DEBE funcionar para ambas monedas: ARS y USD.
- **FR-004**: El diálogo modal de confirmación de movimiento complementario (USD) DEBE ser eliminado del frontend. Los botones **"Entrada"** y **"Salida"** DEBEN registrar el movimiento directamente sin abrir ningún diálogo.
- **FR-005**: El botón **"Entrada y Salida"** DEBE invocar el endpoint existente de creación de movimientos con `registrar_complementario: true`. El backend DEBE eliminar la restricción que limita este campo a moneda USD, permitiendo su uso también con ARS. La atomicidad del par DEBE garantizarse mediante una única transacción de base de datos.
- **FR-006**: El formulario de registro DEBE incluir un campo de selector de fecha opcional.
- **FR-007**: Cuando el selector de fecha está vacío, el sistema DEBE registrar el movimiento con la fecha y hora exacta del servidor en el momento de la solicitud (comportamiento actual).
- **FR-008**: Cuando la secretaria selecciona una fecha en el selector, el frontend DEBE enviar solo la fecha en formato `YYYY-MM-DD`. El backend DEBE construir el datetime `YYYY-MM-DDT09:00:00-03:00` (09:00 AM hora Argentina) y persistirlo como fecha del movimiento.
- **FR-009**: La fecha seleccionada en el selector DEBE aplicarse tanto a movimientos simples (Entrada / Salida) como al movimiento doble (Entrada y Salida).
- **FR-010**: El selector de fecha DEBE tener como estado por defecto "vacío" (sin fecha preseleccionada) al cargar el formulario.
- **FR-011**: El selector de fecha NO DEBE resetearse automáticamente al cambiar la caja seleccionada.
- **FR-012**: La columna **Fecha** en la tabla de historial DEBE mostrar la fecha almacenada del movimiento, independientemente de si fue ingresada manualmente o generada por el servidor.
- **FR-013**: Toda validación de formulario existente (descripción requerida, monto requerido y con formato válido) DEBE aplicarse al nuevo botón **"Entrada y Salida"** de forma idéntica a los botones simples.
- **FR-014**: Todos los movimientos son editables por la secretaria en cualquier momento, independientemente de su fecha almacenada. Los movimientos registrados con fecha manual NO tienen restricción adicional de editabilidad.

### Key Entities

- **Movimiento**: entidad existente. Se extiende conceptualmente para soportar una fecha explícita opcionalmente provista por el cliente (en lugar de siempre usar `created_at` del servidor).
- **CreateMovimientoRequest**: esquema de backend. Puede requerir un campo opcional `fecha_manual` (date) para transportar la fecha elegida por el usuario.
- **MovimientoForm**: componente de frontend. Se modifica para añadir el botón "Entrada y Salida" y el selector de fecha, y para eliminar el estado/diálogo de `pendingTipo`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: La secretaria puede registrar un movimiento como entrada y salida simultáneos en menos de 10 segundos desde que completa el formulario, sin interacción adicional (clic en diálogo).
- **SC-002**: El diálogo de confirmación complementario no aparece en ningún flujo de moneda USD después del despliegue de esta feature.
- **SC-003**: El 100% de los movimientos registrados con fecha seleccionada muestran esa fecha a las 09:00 AM en la tabla de historial.
- **SC-004**: El 100% de los movimientos registrados sin fecha seleccionada mantienen la fecha y hora exacta del servidor (sin regresión).
- **SC-005**: Los subtotales de caja y moneda son correctos después de un registro simultáneo de Entrada y Salida (el neto de la caja no cambia).
- **SC-006**: El tiempo de respuesta de la operación "Entrada y Salida" no supera el doble del tiempo de una operación simple (dado que implica dos registros en el backend).

## Testing Strategy

- **Enfoque elegido:** TDD — tests escritos antes de la implementación para toda la feature.
- **Rationale:** La feature modifica lógica de integridad financiera (cálculo de subtotales en par entrada/salida) y el esquema de datos de `Movimiento` (campo de fecha manual). TDD reduce el riesgo de regresiones silenciosas en los streams de moneda ARS/USD.
- **Scope note:** Esta decisión DEBE ser respetada por `/spec-kitti.plan` (contratos de test) y `/spec-kitti.tasks` (generar tareas TDD-first antes de cada tarea de implementación).

## Clarifications

### Session 2026-09-14

- Q: ¿Querés aplicar TDD y/o Unit Tests estrictos para esta feature? → A: TDD-first — tests escritos antes de la implementación para toda la feature.
- Q: ¿Qué comportamiento de atomicidad querés para el par Entrada+Salida? → A: Atómico (todo o nada) — ambos movimientos en una sola transacción de base de datos; si falla uno, no se crea ninguno.
- Q: ¿Cómo debe funcionar la ventana de edición para movimientos con fecha manual? → A: Siempre editable — en el sistema actual todos los movimientos son editables en cualquier momento, sin ventana de 24h. La fecha manual no cambia este comportamiento.
- Q: ¿Dónde debe aplicarse la hora 09:00 AM al campo de fecha manual? → A: Backend — el frontend envía solo `YYYY-MM-DD`; el backend construye `YYYY-MM-DDT09:00:00` con la zona horaria del servidor (UTC-3 Argentina).
- Q: ¿Cómo debe el frontend invocar la operación "Entrada y Salida" en el backend? → A: Reutilizar `registrar_complementario: true` — mismo campo existente, se elimina la restricción USD-only del backend para permitir ARS también.

## Assumptions

- El backend reutiliza el campo `registrar_complementario: true` para el par Entrada+Salida. La validación `validate_complementario_only_for_usd` DEBE eliminarse para permitir ARS también. No se crea un endpoint nuevo.
- La zona horaria de las 09:00 AM para fechas manuales es **UTC-3 (Argentina)**. El frontend envía solo `YYYY-MM-DD`; el backend construye `YYYY-MM-DDT09:00:00-03:00` antes de persistir.
- El selector de fecha del frontend enviará solo la fecha (`YYYY-MM-DD`); el backend aplicará la hora `09:00:00` en la zona horaria del servidor (UTC-3 Argentina), resultando en `YYYY-MM-DDT09:00:00-03:00`.
- No se requiere restricción de fechas mínimas o máximas en el selector (cualquier fecha es válida).
- La regla de "editable en las últimas 24 horas" **no aplica** en el sistema actual — todos los movimientos son siempre editables por la secretaria, independientemente de su fecha. Los movimientos con fecha manual siguen el mismo comportamiento: siempre editables.
- El botón "Entrada y Salida" reemplaza funcionalmente al diálogo actual; no coexistirán ambos mecanismos.
