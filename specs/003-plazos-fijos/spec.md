# Feature Specification: Plazos Fijos por Caja

**Feature Branch**: `003-plazos-fijos`  
**Created**: 2026-08-06  
**Status**: Draft  
**Input**: User description: "Necesito agregar dos nuevas secciones ademas de Registro y Consulta: Plazos fijos (secretaria carga por caja monto ingresado, fecha de vencimiento, monto a vencimiento; editar/eliminar sin restricción de temporalidad) y Consulta Plazos fijos (usuarios con permisos restringidos consultan como en Consulta). La estética es la misma que antes."

## Clarifications

### Session 2026-08-06

- Q: ¿Por qué campo debe ordenarse el listado de plazos fijos (más recientes primero)? → A: Por **fecha de vencimiento**, con vencimientos **más próximos primero**.
- Q: ¿Cómo se muestran los plazos con fecha de vencimiento ya pasada? → A: **Futuros primero** (vencimiento más próximo en el futuro); **vencidos al final**, ordenados por vencimiento con los más recientemente vencidos primero entre ellos.
- Q: ¿Qué relación debe cumplir monto a vencimiento respecto al monto ingresado? → A: Monto a vencimiento debe ser **≥** monto ingresado.
- Q: ¿Se permite registrar el mismo plazo fijo en múltiples cajas al crear? → A: **No** — un plazo fijo pertenece a una sola caja (sin cajas adicionales).
- Q: ¿Qué panel de resumen mostrar en consulta/gestión (paridad con Valor de caja)? → A: Dos totales solo de plazos **no vencidos**: (1) dinero ingresado en plazos activos; (2) dinero a cobrar al vencer los plazos activos (suma de montos a vencimiento).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Gestionar Plazos Fijos (Priority: P1)

Como secretaria de la escribanía, necesito registrar, editar y eliminar plazos fijos
asociados a cada caja, indicando el monto ingresado, la fecha de vencimiento y el
monto a vencimiento, para llevar un control actualizado de inversiones a plazo fijo
vinculadas a las cuentas de la escribanía.

**Why this priority**: Es la operación central de esta feature. Sin registro de
plazos fijos no hay datos que consultar ni valor de negocio para supervisión.

**Independent Test**: Puede probarse con un usuario con rol Secretaria: seleccionar
una caja, crear un plazo fijo con los tres campos requeridos, editarlo y eliminarlo
(incluso si es antiguo), y verificar que la tabla refleja los cambios.

**Acceptance Scenarios**:

1. **Given** una secretaria autenticada en la pantalla de Plazos Fijos,
   **When** selecciona la caja "Bambina", ingresa monto ingresado 100000, fecha de
   vencimiento 2026-12-31 y monto a vencimiento 105000, y confirma el registro,
   **Then** el plazo fijo se guarda y aparece en la tabla con esos tres valores y la
   caja seleccionada.
2. **Given** una secretaria con plazos fijos previos en la caja "Ebel",
   **When** cambia el selector de caja a otra del catálogo,
   **Then** la tabla muestra exclusivamente los plazos fijos de la caja seleccionada.
3. **Given** una secretaria y un plazo fijo existente (sin importar su antigüedad),
   **When** edita el monto ingresado, la fecha de vencimiento o el monto a
   vencimiento,
   **Then** el cambio se guarda y la tabla refleja los valores actualizados.
4. **Given** una secretaria y un plazo fijo existente (sin importar su antigüedad),
   **When** elimina el plazo fijo,
   **Then** desaparece del historial de esa caja.
5. **Given** una secretaria viendo plazos fijos de una caja con más de 20 registros
   futuros,
   **When** usa el selector de páginas,
   **Then** ve en la página 1 los 20 plazos con vencimiento futuro más próximo y puede
   avanzar a páginas siguientes para ver vencimientos futuros más lejanos; los plazos
   vencidos aparecen solo en páginas posteriores a todos los futuros.
6. **Given** una secretaria en Plazos Fijos con plazos activos en la caja seleccionada,
   **When** carga los datos de la caja,
   **Then** ve el panel de resumen con dinero ingresado en plazos no vencidos y dinero
   a cobrar al vencer (solo plazos activos).

---

### User Story 2 - Consultar Plazos Fijos (Priority: P2)

Como escribano de la escribanía, necesito consultar los plazos fijos de cada caja sin
poder modificarlos, para supervisar las inversiones a plazo fijo con el mismo nivel
de detalle que la secretaria.

**Why this priority**: Complementa el registro con supervisión de solo lectura para
usuarios con permisos restringidos. Depende de que existan plazos fijos (US1) pero
es independiente en su flujo de consulta.

**Independent Test**: Puede probarse con un usuario con rol Escribano: seleccionar
cualquiera de las 15 cajas, presionar **Consulta** y verificar que ve monto ingresado,
fecha de vencimiento y monto a vencimiento sin controles de edición ni eliminación.

**Acceptance Scenarios**:

1. **Given** un escribano autenticado en la pantalla de Consulta Plazos Fijos,
   **When** selecciona la caja "Gabriel" y presiona **Consulta**,
   **Then** ve dos resúmenes de plazos no vencidos (dinero ingresado y dinero a cobrar
   al vencer) y la lista con columnas Monto ingresado, Fecha de vencimiento y Monto a
   vencimiento.
2. **Given** un escribano en Consulta Plazos Fijos,
   **When** intenta crear, editar o eliminar un plazo fijo (por interfaz o acción
   directa),
   **Then** el sistema no permite la operación y no modifica ningún dato.
3. **Given** una secretaria autenticada,
   **When** accede a Consulta Plazos Fijos,
   **Then** también puede consultar cualquier caja con el mismo nivel de detalle.
4. **Given** un escribano autenticado,
   **When** selecciona cualquiera de las 15 cajas del catálogo,
   **Then** puede consultar sus plazos fijos (sin restricción por caja asignada).

---

### Edge Cases

- ¿Qué ocurre si se intenta registrar un plazo fijo sin fecha de vencimiento, con
  monto ingresado cero/negativo, con monto a vencimiento cero/negativo, o con monto
  a vencimiento menor que monto ingresado? El sistema debe rechazar el registro con
  mensaje claro.
- ¿Qué ocurre si una caja no tiene plazos fijos? La consulta debe mostrar tabla vacía
  con mensaje o estado claro, sin error; los dos totales del panel de resumen deben
  mostrar $0.
- ¿Qué ocurre si un escribano intenta crear/editar/eliminar plazos fijos por
  cualquier vía? El sistema debe denegar la operación sin alterar datos.
- ¿Qué ocurre al navegar a la última página del listado? Debe mostrar solo los
  registros restantes (menos de 20 si aplica) sin páginas vacías.
- ¿Qué ocurre con montos decimales? El sistema debe aceptar montos con hasta 2
  decimales (centavos) y mostrarlos de forma consistente.
- ¿Qué ocurre si la fecha de vencimiento es en el pasado al crear o editar? El
  sistema debe permitir el registro (plazos ya vencidos pueden documentarse); en el
  listado aparecen al final y no suman en los totales del panel de resumen.
- ¿Qué ocurre si hay plazos vencidos y futuros en la misma caja? Los futuros se
  listan primero (vencimiento más próximo primero); los vencidos al final (más
  recientemente vencidos primero entre ellos). Solo los futuros alimentan los dos
  totales del panel de resumen.
- ¿Qué ocurre si una caja solo tiene plazos vencidos? Los totales del panel de
  resumen deben ser $0; la tabla lista los vencidos al final según FR-010.
- ¿Qué ocurre si el usuario cierra sesión o expira la sesión? Debe requerir login
  nuevamente (misma regla de 8 horas que el resto de la aplicación).

## Requirements *(mandatory)*

### Functional Requirements

**Alcance general**

- **FR-001**: El sistema DEBE ofrecer dos nuevas secciones navegables además de
  Registro y Consulta de Caja: **Plazos Fijos** y **Consulta Plazos Fijos**.
- **FR-002**: La estética, disposición de pantalla y patrones de interacción de ambas
  nuevas secciones DEBEN ser consistentes con las pantallas existentes de Registro de
  Caja y Consulta de Caja (selector de caja, tabla de datos, paginación, barra de
  navegación y estilos globales).

**Plazos Fijos (Secretaria)**

- **FR-003**: Solo el rol **Secretaria** DEBE poder acceder a la pantalla de
  gestión de Plazos Fijos.
- **FR-004**: La pantalla DEBE ofrecer un selector con las mismas 15 cajas del
  catálogo existente (Bambina, Ebel, Martin, Gimnasio, Gabriel, Costanza, Guille,
  Intimayu, Amelia, Entre Rios, Chovet, Maria Teresa, Barat Hermanos, General Lagos,
  Fideicomiso).
- **FR-005**: La secretaria DEBE poder registrar un plazo fijo para **una sola caja**
  seleccionada indicando: **monto ingresado**, **fecha de vencimiento** y **monto a
  vencimiento**. No se admite registro simultáneo en múltiples cajas.
- **FR-006**: Cada plazo fijo DEBE persistir: monto ingresado, fecha de vencimiento,
  monto a vencimiento, caja asociada, fecha de creación y usuario que lo registró
  (auditoría mínima).
- **FR-007**: La secretaria DEBE poder **editar** cualquier plazo fijo existente sin
  restricción de antigüedad (sin ventana temporal de 24 horas ni equivalente).
- **FR-008**: La secretaria DEBE poder **eliminar** cualquier plazo fijo existente sin
  restricción de antigüedad.
- **FR-009**: La tabla de plazos fijos DEBE mostrar columnas: Monto ingresado, Fecha
  de vencimiento y Monto a vencimiento (más controles de edición/eliminación en
  pantalla de gestión).
- **FR-009a**: Las pantallas de Plazos Fijos (gestión) y Consulta Plazos Fijos DEBEN
  mostrar un panel de resumen con **dos totales** calculados solo sobre plazos con
  vencimiento **futuro** (no vencidos) de la caja consultada: (1) **Dinero ingresado
  en plazos activos** — suma de montos ingresados; (2) **Dinero a cobrar al vencer**
  — suma de montos a vencimiento. Los plazos vencidos no participan en estos
  totales.
- **FR-010**: El listado DEBE paginarse con exactamente **20 registros por página**.
  El orden DEBE ser: (1) plazos con **vencimiento futuro** primero, ascendente por
  fecha de vencimiento (más próximo primero); (2) plazos **vencidos** al final,
  descendente por fecha de vencimiento (más recientemente vencidos primero). Dentro
  del mismo grupo y misma fecha de vencimiento, el orden secundario es por fecha de
  creación descendente (más reciente primero).

**Consulta Plazos Fijos (Escribano y Secretaria)**

- **FR-011**: El sistema DEBE ofrecer una pantalla de Consulta Plazos Fijos con
  selector de caja y botón **Consulta**, siguiendo el mismo patrón que Consulta de
  Caja.
- **FR-012**: Los roles **Escribano** y **Secretaria** DEBEN poder acceder a Consulta
  Plazos Fijos.
- **FR-013**: La consulta DEBE mostrar el mismo listado que ve la secretaria en
  gestión: Monto ingresado, Fecha de vencimiento y Monto a vencimiento, con la misma
  regla de orden (vencimiento más próximo primero) y paginación.
- **FR-014**: El rol **Escribano** NO DEBE poder crear, editar ni eliminar plazos
  fijos por ningún medio.
- **FR-015**: El rol **Escribano** DEBE poder consultar **todas** las cajas del
  catálogo (15 cajas); no hay restricción por caja asignada al usuario.
- **FR-016**: El rol **Secretaria** DEBE poder acceder tanto a Plazos Fijos
  (gestión) como a Consulta Plazos Fijos.

**Validación y datos**

- **FR-017**: Monto ingresado y monto a vencimiento DEBEN ser valores positivos
  mayores que cero, con hasta 2 decimales (ARS). Monto a vencimiento DEBE ser **≥**
  monto ingresado en creación y edición.
- **FR-018**: Fecha de vencimiento es obligatoria en creación y edición.
- **FR-019**: La validación de roles DEBE aplicarse en el servidor; el frontend solo
  refleja permisos.
- **FR-020**: Los nuevos datos DEBEN persistirse en la misma base de datos que el
  resto de la aplicación (PostgreSQL).

**Navegación y acceso**

- **FR-021**: Visitantes no autenticados NO DEBEN acceder a Plazos Fijos ni Consulta
  Plazos Fijos.
- **FR-022**: La barra de navegación DEBE incluir enlaces a las nuevas secciones con
  visibilidad según rol (gestión solo secretaria; consulta secretaria y escribano).

### Key Entities

- **Plazo Fijo**: Inversión a plazo fijo asociada a una caja. Atributos: monto
  ingresado, fecha de vencimiento, monto a vencimiento, caja asociada, usuario que lo
  registró, fecha de creación. Editable y eliminable por secretaria sin límite
  temporal.
- **Caja**: Reutiliza el catálogo fijo de 15 cajas existente; un caja puede tener
  múltiples plazos fijos.
- **Usuario / Rol**: Reutiliza Secretaria y Escribano con las mismas reglas de acceso
  ampliadas a las nuevas secciones.

## Testing Strategy

- **Enfoque elegido**: `TDD` — tests escritos antes de la implementación, alineado
  con la feature 001-registro-cajas y la constitución del proyecto.
- **Rationale**: Dominio financiero con RBAC; TDD reduce regresiones en permisos y
  validación de montos.
- **Alcance**: Tests antes de implementar CRUD de plazos fijos, autorización por rol,
  paginación y flujos de consulta. Tests de integración para RBAC son obligatorios.

## Assumptions

- No se requiere cálculo automático del monto a vencimiento; la secretaria ingresa
  ambos montos manualmente. Monto a vencimiento debe ser siempre ≥ monto ingresado.
- No hay integración con entidades financieras externas; los plazos fijos son registro
  manual.
- La moneda es ARS (pesos argentinos); no se requiere multi-moneda.
- Paginación (20 por página) y formato de montos siguen las convenciones del
  historial de movimientos de caja. Orden: vencimientos futuros primero (ascendente,
  más próximo primero); vencidos al final (descendente, más recientemente vencidos
  primero).
- "Usuarios con permisos restringidos" se interpreta como el rol **Escribano**
  (solo lectura), análogo a Consulta de Caja.
- Las fechas de vencimiento en el pasado son válidas (documentación de plazos ya
  vencidos).
- La sesión autenticada mantiene la duración de 8 horas definida en la feature
  anterior.
- No se requiere selector de “cajas adicionales” ni registro multi-caja; cada plazo
  fijo pertenece a una sola caja.
- No se requieren wireframes nuevos; la UI replica la estética y estructura de
  Registro/Consulta de Caja, incluyendo panel de resumen análogo al “Valor de caja”
  con los dos totales de plazos activos.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Una secretaria puede registrar un plazo fijo completo (tres campos) en
  menos de 45 segundos desde que selecciona la caja.
- **SC-002**: Una secretaria puede editar o eliminar un plazo fijo de cualquier
  antigüedad sin rechazo del sistema en el 100% de los casos de prueba válidos.
- **SC-003**: Un escribano puede consultar los plazos fijos de cualquiera de las 15
  cajas en menos de 10 segundos desde que presiona **Consulta**.
- **SC-004**: El 100% de los intentos de escritura (crear/editar/eliminar) por un
  usuario Escribano son rechazados sin modificar datos.
- **SC-005**: El listado pagina correctamente en bloques de 20 registros; la página 1
  muestra los vencimientos futuros más próximos; los vencidos solo aparecen después
  de todos los futuros, sin omisiones ni duplicados entre páginas.
- **SC-006**: Los valores mostrados en Consulta Plazos Fijos coinciden con los
  registrados por la secretaria en el 100% de los casos de prueba.
- **SC-006a**: Los dos totales del panel de resumen (dinero ingresado activo y dinero
  a cobrar al vencer) coinciden con la suma manual de plazos no vencidos en el 100%
  de los casos de prueba.
- **SC-007**: Las nuevas pantallas son percibidas como parte del mismo producto: en
  revisión con usuarios, al menos el 90% identifica consistencia visual con Registro
  y Consulta de Caja sin guía adicional.
