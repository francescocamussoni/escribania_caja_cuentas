# Feature Specification: Registro de Cajas para Escribanía

**Feature Branch**: `001-registro-cajas`  
**Created**: 2026-08-03  
**Status**: Draft  
**Input**: User description: "Implementa lo dado en el constitution. Autenticación usuario/contraseña con usuarios creados manualmente en el backend; usuario inicial admin/admin. Paginación de 20 registros por página."

## Clarifications

### Session 2026-08-03

- Q: ¿Aplicar TDD y/o Unit Tests estrictos para esta feature? → A: **TDD** — enfoque TDD-first (tests escritos antes de la implementación).
- Q: ¿Qué registros muestra la página 1 del historial? → A: **Más recientes primero** — página 1 = últimos 20 movimientos; páginas siguientes = movimientos más antiguos.
- Q: ¿Permitir subtotal negativo tras una salida mayor al saldo? → A: **Permitir** — acepta la salida y el subtotal puede quedar negativo.
- Q: ¿Cuándo expira la sesión del usuario? → A: **8 horas desde el login** — la sesión expira al finalizar la jornada laboral típica.
- Q: ¿Qué cajas puede consultar un Escribano? → A: **Todas las cajas** — cualquier Escribano puede consultar las 15 cajas del catálogo.

### Session 2026-08-03 (amend)

- Q: ¿Puede la secretaria editar o eliminar movimientos? → A: **Sí, dentro de 24h** — solo movimientos creados en las últimas 24 horas; recálculo de subtotales posteriores obligatorio.
- Q: ¿Dónde se persiste la información? → A: **PostgreSQL** — local con Docker; producción en AWS RDS.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Iniciar Sesión (Priority: P1)

Como usuario de la escribanía, necesito iniciar sesión con mi nombre de usuario y
contraseña para acceder de forma segura a las funcionalidades del sistema según mi
rol asignado.

**Why this priority**: Sin autenticación no hay acceso a ninguna funcionalidad.
Es el prerequisito bloqueante para registro y consulta de cajas.

**Independent Test**: Puede probarse accediendo a la pantalla de login, ingresando
credenciales válidas e inválidas, y verificando que solo usuarios autenticados
acceden al sistema.

**Acceptance Scenarios**:

1. **Given** un usuario con credenciales válidas provisionadas en el sistema,
   **When** ingresa usuario y contraseña correctos y confirma el login,
   **Then** accede a la aplicación y ve solo las funcionalidades permitidas para
   su rol.
2. **Given** un usuario en la pantalla de login,
   **When** ingresa credenciales incorrectas,
   **Then** el sistema rechaza el acceso con un mensaje genérico sin revelar si
   el usuario existe o cuál campo falló.
3. **Given** un visitante no autenticado,
   **When** intenta acceder directamente a registro o consulta de caja,
   **Then** el sistema lo redirige al login.
4. **Given** un usuario autenticado hace más de 8 horas,
   **When** intenta realizar cualquier acción,
   **Then** la sesión ha expirado y debe iniciar sesión nuevamente.

---

### User Story 2 - Registrar Movimientos de Caja (Priority: P2)

Como secretaria de la escribanía, necesito registrar ingresos y egresos de dinero
en las distintas cajas o cuentas bancarias para mantener actualizado el saldo de
cada una.

**Why this priority**: Es la operación central del negocio. Sin registro de
movimientos no hay datos que consultar ni subtotales que calcular.

**Independent Test**: Puede probarse con un usuario con rol Secretaria: seleccionar
una caja, registrar entradas y salidas, y verificar que la tabla muestra descripción,
monto, subtotal acumulado y fecha en orden cronológico.

**Acceptance Scenarios**:

1. **Given** una secretaria autenticada en la pantalla de Registro de Caja,
   **When** selecciona la caja "Bambina", ingresa descripción "Pago cliente",
   monto 5000 y presiona **Entrada**,
   **Then** el movimiento se guarda, el monto aparece como ingreso (positivo) y el
   subtotal se incrementa respecto al movimiento anterior de esa caja.
2. **Given** una secretaria con movimientos previos en la caja "Ebel",
   **When** registra una **Salida** de 2000 con descripción "Gastos varios",
   **Then** el monto aparece como egreso, el subtotal disminuye en 2000 respecto
   al subtotal anterior y la fecha del movimiento queda registrada.
3. **Given** una secretaria viendo el historial de una caja con más de 20
   movimientos,
   **When** usa el selector de páginas,
   **Then** ve en la página 1 los 20 movimientos más recientes (más reciente arriba)
   y puede avanzar a páginas siguientes para ver movimientos más antiguos.
4. **Given** una secretaria en Registro de Caja,
   **When** cambia el selector de caja a otra del catálogo,
   **Then** la tabla y el subtotal mostrados corresponden exclusivamente a la caja
   seleccionada.
5. **Given** una secretaria con subtotal 1000 en una caja,
   **When** registra una **Salida** de 1500,
   **Then** el movimiento se guarda y el subtotal resultante es -500.
6. **Given** una secretaria y un movimiento creado hace menos de 24 horas,
   **When** edita la descripción o el monto del movimiento,
   **Then** el cambio se guarda y los subtotales de movimientos posteriores de esa
   caja se recalculan correctamente.
7. **Given** una secretaria y un movimiento creado hace menos de 24 horas,
   **When** elimina el movimiento,
   **Then** desaparece del historial y los subtotales posteriores se recalculan.
8. **Given** una secretaria y un movimiento creado hace más de 24 horas,
   **When** intenta editarlo o eliminarlo,
   **Then** el sistema rechaza la operación sin modificar datos.

---

### User Story 3 - Consultar Estado de Caja (Priority: P3)

Como escribano de la escribanía, necesito consultar el saldo y el historial de
movimientos de una caja sin poder modificarlos, para supervisar la situación
financiera.

**Why this priority**: Complementa el registro con supervisión de solo lectura.
Depende de que existan movimientos (US2) pero es independiente en su flujo de
consulta.

**Independent Test**: Puede probarse con un usuario con rol Escribano: seleccionar
cualquiera de las 15 cajas, presionar **Consulta** y verificar que ve la misma
información que la secretaria sin controles de entrada/salida.

**Acceptance Scenarios**:

1. **Given** un escribano autenticado en la pantalla de Consulta de Caja,
   **When** selecciona la caja "Gabriel" y presiona **Consulta**,
   **Then** ve el valor actual de la caja y el historial con columnas Descripción,
   Monto, Subtotal y Fecha.
2. **Given** un escribano en Consulta de Caja,
   **When** intenta registrar un ingreso o egreso (por interfaz o acción directa),
   **Then** el sistema no permite la operación y no modifica ningún dato.
3. **Given** una secretaria autenticada,
   **When** accede a Consulta de Caja,
   **Then** también puede consultar cualquier caja con el mismo nivel de detalle.
4. **Given** un escribano autenticado,
   **When** selecciona cualquiera de las 15 cajas del catálogo,
   **Then** puede consultar su historial y saldo (sin restricción por caja asignada).

---

### Edge Cases

- ¿Qué ocurre si se intenta registrar un movimiento sin descripción o con monto
  cero/negativo? El sistema debe rechazar el registro con mensaje claro.
- ¿Qué ocurre si una caja no tiene movimientos previos? El primer movimiento debe
  usar subtotal inicial 0.
- ¿Qué ocurre si una salida supera el subtotal actual? El sistema DEBE permitir el
  movimiento y el subtotal puede quedar negativo.
- ¿Qué ocurre si un escribano intenta registrar movimientos por cualquier vía? El
  sistema debe denegar la operación sin alterar datos.
- ¿Qué ocurre al navegar a la última página del historial? Debe mostrar solo los
  registros restantes (menos de 20 si aplica) sin páginas vacías.
- ¿Qué ocurre con montos decimales? El sistema debe aceptar montos con hasta 2
  decimales (centavos) y mostrarlos de forma consistente.
- ¿Qué ocurre si el usuario cierra sesión o expira la sesión? La sesión expira
  automáticamente **8 horas después del login**; en ambos casos debe requerir login
  nuevamente para acceder a cualquier funcionalidad.
- ¿Qué ocurre si la secretaria edita un movimiento con movimientos posteriores? Los
  subtotales de todos los movimientos siguientes en esa caja deben recalcularse en
  cascada.
- ¿Qué ocurre si intenta editar/eliminar un movimiento de más de 24 horas? Rechazo
  con mensaje claro (HTTP 403 o 422).

## Requirements *(mandatory)*

### Functional Requirements

**Autenticación y usuarios**

- **FR-001**: El sistema DEBE requerir autenticación con nombre de usuario y
  contraseña antes de acceder a cualquier funcionalidad.
- **FR-002**: Los usuarios DEBEN crearse manualmente en el backend; no hay
  auto-registro ni recuperación de contraseña en v1.
- **FR-003**: El sistema DEBE incluir un usuario inicial de arranque con usuario
  `admin` y contraseña `admin` (solo para desarrollo y pruebas iniciales).
- **FR-004**: Cada usuario DEBE tener asignado un rol: **Secretaria** o
  **Escribano**.
- **FR-005**: El sistema DEBE registrar intentos fallidos de login sin revelar
  información que facilite ataques (usuario inexistente vs contraseña incorrecta).
- **FR-005a**: La sesión autenticada DEBE expirar **8 horas después del login**;
  tras la expiración, cualquier acción requiere nuevo inicio de sesión.

**Registro de Caja (Secretaria)**

- **FR-006**: El sistema DEBE ofrecer un selector con exactamente las 15 cajas del
  catálogo: Bambina, Ebel, Martin, Gimnasio, Gabriel, Costanza, Guille, Intimayu,
  Amelia, Entre Rios, Chovet, Maria Teresa, Barat Hermanos, General Lagos,
  Fideicomiso.
- **FR-007**: La secretaria DEBE poder ingresar una descripción de texto libre para
  cada movimiento.
- **FR-008**: La secretaria DEBE poder registrar movimientos mediante botones
  **Entrada** (suma al subtotal) y **Salida** (resta al subtotal).
- **FR-009**: Cada movimiento DEBE persistir: descripción, monto, tipo
  (entrada/salida), subtotal resultante, fecha del movimiento y caja asociada.
- **FR-010**: El subtotal DEBE calcularse como acumulado cronológico por caja: cada
  nuevo movimiento parte del subtotal del movimiento inmediatamente anterior de esa
  misma caja. El subtotal PUEDE ser negativo si una salida lo supera.
- **FR-011**: La pantalla de Registro de Caja DEBE seguir la disposición definida en
  `registro_de_caja.drawio` (selector de caja arriba, tabla con columnas
  Descripción/Monto/Subtotal/Fecha, selector de páginas abajo).
- **FR-012**: Los ingresos DEBEN distinguirse visualmente de los egresos (verde =
  ingreso, rojo = egreso, según wireframe).
- **FR-013**: Toda operación de escritura DEBE quedar asociada al usuario que la
  realizó (auditoría mínima).
- **FR-013a**: La secretaria DEBE poder **editar** movimientos creados en las
  **últimas 24 horas** (descripción, monto y/o tipo).
- **FR-013b**: La secretaria DEBE poder **eliminar** movimientos creados en las
  **últimas 24 horas**.
- **FR-013c**: Tras editar o eliminar un movimiento, el sistema DEBE **recalcular**
  los subtotales de todos los movimientos posteriores de la misma caja en orden
  cronológico.
- **FR-013d**: Movimientos con más de 24 horas de antigüedad NO PUEDEN editarse ni
  eliminarse por ningún usuario.
- **FR-013e**: El rol Escribano NO PUEDE editar ni eliminar movimientos.

**Consulta de Caja (Escribano y Secretaria)**

- **FR-014**: El sistema DEBE ofrecer una pantalla de Consulta de Caja con selector
  de caja y botón **Consulta**, siguiendo `consulta_de_caja.drawio`.
- **FR-015**: La consulta DEBE mostrar el mismo historial que ve la secretaria:
  Descripción, Monto, Subtotal y Fecha, con los movimientos más recientes primero
  (misma regla de orden y paginación que Registro de Caja).
- **FR-016**: El rol Escribano NO DEBE poder registrar, editar ni eliminar
  movimientos por ningún medio.
- **FR-016a**: El rol Escribano DEBE poder consultar **todas** las cajas del
  catálogo (15 cajas); no hay restricción por caja asignada al usuario.
- **FR-017**: El rol Secretaria DEBE poder acceder tanto a Registro como a Consulta
  de Caja.

**Paginación y visualización**

- **FR-018**: El historial de movimientos DEBE paginarse con exactamente **20
  registros por página**.
- **FR-019**: La **página 1** DEBE mostrar los 20 movimientos más recientes de la
  caja; el selector de páginas DEBE permitir avanzar hacia movimientos más
  antiguos.
- **FR-020**: Dentro de cada página, los registros DEBEN mostrarse en orden
  cronológico descendente (más reciente primero, más antiguo al final de la página).

**Seguridad y alcance**

- **FR-021**: La validación de roles DEBE aplicarse en el servidor; el frontend solo
  refleja permisos.
- **FR-022**: El sistema NO DEBE integrar con bancos externos ni soportar
  multi-escribanía en v1.
- **FR-023**: Los montos DEBEN expresarse en una única moneda (ARS) con formato
  decimal de hasta 2 decimales.

**Persistencia**

- **FR-024**: Todos los datos DEBEN persistirse en **PostgreSQL** (desarrollo local
  vía Docker; producción extrapolable a AWS RDS).

### Key Entities

- **Usuario**: Persona con acceso al sistema. Atributos: nombre de usuario,
  contraseña (almacenada de forma segura), rol (Secretaria | Escribano).
- **Caja**: Cuenta o caja de la escribanía del catálogo fijo de 15 nombres. No
  admite creación dinámica en v1.
- **Movimiento**: Registro de ingreso o egreso. Atributos: descripción, monto,
  tipo (entrada/salida), subtotal resultante, fecha, caja asociada, usuario que lo
  registró, `updated_at` si fue editado. Editable/eliminable por secretaria solo
  dentro de 24h desde `created_at`.
- **Sesión**: Contexto de usuario autenticado que habilita acceso según rol.
  Duración máxima: 8 horas desde el login.

## Testing Strategy

- **Enfoque elegido**: `TDD` — tests escritos antes de la implementación en toda la
  feature.
- **Rationale**: Dominio financiero con integridad de subtotales y RBAC; TDD
  reduce regresiones en cálculos acumulados y controles de acceso.
- **Alcance**: Tests antes de implementar lógica de subtotales, autorización por
  rol, autenticación, paginación y flujos de registro/consulta. Tests de
  integración para subtotales y RBAC son obligatorios (constitución).
- **Nota para downstream**: Esta decisión DEBE respetarse en `/spec-kitti.plan`
  (contratos de test) y `/spec-kitti.tasks` (tareas TDD generadas antes de
  implementación).

## Assumptions

- El usuario bootstrap `admin`/`admin` tendrá rol **Secretaria** para permitir
  desarrollo y pruebas del flujo completo de registro en v1.
- Para probar el rol Escribano se creará manualmente un segundo usuario en el
  backend (fuera del alcance de esta feature si no se solicita).
- "Su caja" en la constitución se interpreta como la caja seleccionada en consulta;
  no implica asignación exclusiva de caja por escribano en v1.
- La moneda es ARS (pesos argentinos); no se requiere conversión ni multi-moneda.
- Persistencia en **PostgreSQL** (local Docker Compose; AWS RDS en producción).
- Ventana de edición/eliminación: **24 horas** desde `created_at` del movimiento;
  zona horaria UTC en servidor, presentación en hora Argentina.
- Las credenciales `admin`/`admin` son temporales para desarrollo; en despliegue
  productivo deberán reemplazarse por credenciales seguras.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Una secretaria puede registrar un movimiento de entrada o salida en
  menos de 30 segundos desde que selecciona la caja.
- **SC-002**: El subtotal mostrado tras cada movimiento coincide con el cálculo
  manual del acumulado cronológico en el 100% de los casos de prueba.
- **SC-003**: Un escribano puede consultar el estado de cualquiera de las 15 cajas
  en menos de 10 segundos desde que presiona **Consulta**.
- **SC-004**: El 100% de los intentos de escritura por un usuario Escribano son
  rechazados sin modificar datos.
- **SC-005**: El historial pagina correctamente en bloques de 20 registros (página 1
  = más recientes) para cajas con más de 20 movimientos, sin omisiones ni
  duplicados entre páginas.
- **SC-006**: Ningún visitante no autenticado accede a datos de cajas en pruebas de
  acceso directo.
- **SC-007**: El 100% de intentos de edición/eliminación fuera de la ventana de 24h
  son rechazados sin modificar datos.
- **SC-008**: Tras editar o eliminar un movimiento elegible, los subtotales
  posteriores coinciden con el cálculo manual en el 100% de casos de prueba.
