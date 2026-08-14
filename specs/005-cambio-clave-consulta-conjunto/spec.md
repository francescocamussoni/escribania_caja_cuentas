# Feature Specification: Cambio de Contraseña y Consulta Conjunta de Cajas

**Feature Branch**: `005-cambio-clave-consulta-conjunto`  
**Created**: 2026-08-14  
**Status**: Draft  
**Input**: User description: "Necesito agregar que cada usuario pueda modificar su contraseña, tanto en el menu de inicio (cuando se loggea) como dentro de la pagina en la sección de usuario (tocando arriba a la derecha donde aparece el nombre de usuario). Necesito que cuando se consulta por los valores de cajas, se permita consultar mas de una caja con un box de selección. La UI se mantiene (un desplegable para elegir una caja) pero con una sección debajo que diga 'Ver en conjunto con otras cajas' donde se permita seleccionar cada caja. En ese caso se mostrará el subtotal de cada caja y N solapas desplegables cada caja en particular. Cuando se selecciona una caja el comportamiento sigue el que ya existe."

## Clarifications

### Session 2026-08-14

- Q: ¿Aplicar TDD y/o Unit Tests estrictos para esta feature? → A: **TDD** — enfoque TDD-first (tests escritos antes de la implementación).
- Q: Tras pulsar Consulta con varias cajas, ¿qué solapas deben estar abiertas al inicio? → A: **Todas cerradas**; el orden de aparición pone primero la caja del desplegable principal.
- Q: ¿En qué orden se listan las cajas adicionales (después de la del desplegable)? → A: **Orden del catálogo**, saltando la caja principal.
- Q: Si al consultar en conjunto falla la carga de una caja, ¿qué debe verse? → A: **Falla toda la consulta** — mensaje de error y ningún resultado de ese intento.
- Q: En la pantalla de inicio de sesión, ¿cómo se presenta el cambio de contraseña? → A: **Enlace «Cambiar contraseña»** que reemplaza el formulario de ingreso por el de cambio.

### Session 2026-08-14 (amend — total conjunto)

- Q: Tras una consulta conjunta exitosa, ¿debe verse un total que sume los saldos de todas las cajas incluidas? → A: **Sí** — arriba de las solapas, el **Valor en conjunto** es la suma aritmética de los `saldo_actual` de cada caja incluida (los mismos valores que ya devolvió el backend). No se mezclan movimientos.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Cambiar contraseña desde el menú de inicio (Priority: P1)

Como usuario de la escribanía (secretaria o escribano), necesito cambiar mi
contraseña desde la pantalla de inicio de sesión, para poder actualizarla sin
depender de un administrador ni de intervención en la base de datos.

**Why this priority**: Hoy el cambio de contraseña es un proceso operativo externo.
Habilitarlo en el login desbloquea autoservicio para todos los roles y reduce el
riesgo de credenciales compartidas o desactualizadas.

**Independent Test**: Desde la pantalla de login, un usuario existente pulsa
**Cambiar contraseña**, ingresa usuario, contraseña actual y nueva contraseña
(con confirmación). Tras el éxito vuelve el formulario de ingreso y solo la
nueva contraseña funciona.

**Acceptance Scenarios**:

1. **Given** un usuario existente en la pantalla de inicio de sesión,
   **When** pulsa el enlace **Cambiar contraseña**, completa usuario, contraseña
   actual, nueva contraseña y confirmación válidas, y confirma,
   **Then** el sistema acepta el cambio, muestra un mensaje de éxito y vuelve a
   mostrar el formulario de ingreso para que entre con la nueva contraseña.
2. **Given** un usuario en el flujo de cambio de contraseña del login,
   **When** ingresa una contraseña actual incorrecta,
   **Then** el sistema rechaza el cambio con un mensaje genérico (sin indicar si
   el usuario existe o cuál dato falló) y la contraseña anterior sigue vigente.
3. **Given** un usuario que acaba de cambiar su contraseña desde el login,
   **When** intenta iniciar sesión con la contraseña anterior,
   **Then** el acceso se rechaza; con la nueva contraseña el acceso se concede.
4. **Given** un usuario en el flujo de cambio de contraseña del login,
   **When** la nueva contraseña y su confirmación no coinciden, o la nueva no
   cumple las reglas de fortaleza, o es igual a la actual,
   **Then** el sistema rechaza el cambio con un mensaje claro y no modifica la
   contraseña.

---

### User Story 2 - Cambiar contraseña desde la sección de usuario (Priority: P2)

Como usuario autenticado, necesito cambiar mi contraseña tocando mi nombre de
usuario arriba a la derecha, para actualizarla sin salir del trabajo cotidiano
en el sistema.

**Why this priority**: Completa el autoservicio una vez dentro de la aplicación.
Es el acceso natural para quien ya está logueado y no quiere volver al login.

**Independent Test**: Un usuario autenticado abre la sección de usuario desde su
nombre (arriba a la derecha), cambia la contraseña con la actual y la nueva
confirmada, y verifica que debe volver a identificarse y que solo la nueva
contraseña funciona.

**Acceptance Scenarios**:

1. **Given** un usuario autenticado (secretaria o escribano),
   **When** toca su nombre de usuario arriba a la derecha,
   **Then** se abre la sección de usuario con la acción de cambiar contraseña
   (además de lo que ya exista para identificar al usuario y salir).
2. **Given** un usuario autenticado en la sección de usuario,
   **When** completa contraseña actual, nueva contraseña y confirmación válidas
   y confirma,
   **Then** el cambio se aplica, las sesiones abiertas de ese usuario dejan de
   ser válidas y debe iniciar sesión de nuevo con la nueva contraseña.
3. **Given** un usuario autenticado en el cambio de contraseña,
   **When** ingresa una contraseña actual incorrecta,
   **Then** el sistema rechaza el cambio, la sesión actual permanece y la
   contraseña no cambia.
4. **Given** un usuario autenticado,
   **When** intenta cambiar la contraseña de otro usuario (por cualquier medio),
   **Then** el sistema lo rechaza; cada usuario solo puede cambiar la propia.

---

### User Story 3 - Consultar una sola caja (comportamiento existente) (Priority: P3)

Como secretaria o escribano, necesito consultar el valor y el historial de **una**
caja con el desplegable y el botón Consulta, igual que hoy, cuando no quiero
ver otras cajas al mismo tiempo.

**Why this priority**: Es el flujo diario actual. La consulta conjunta no debe
romper ni complicar el caso más frecuente.

**Independent Test**: En Consulta de Caja, elegir una caja en el desplegable, no
marcar cajas adicionales (o dejar la sección conjunta vacía), pulsar Consulta y
verificar valor de caja, historial paginado y columnas iguales al comportamiento
vigente.

**Acceptance Scenarios**:

1. **Given** un usuario autenticado en Consulta de Caja, con una caja elegida en
   el desplegable y **ninguna** caja marcada en «Ver en conjunto con otras cajas»,
   **When** pulsa **Consulta**,
   **Then** ve el valor actual de esa caja y su historial (Descripción, Monto,
   Subtotal, Fecha, más recientes primero, 20 por página), como hasta ahora.
2. **Given** una consulta de una sola caja ya mostrada,
   **When** cambia el desplegable a otra caja y vuelve a consultar sin cajas
   adicionales,
   **Then** el resultado corresponde solo a la nueva caja (sin paneles de otras
   cajas).
3. **Given** un escribano en Consulta de Caja (una sola caja),
   **When** consulta,
   **Then** ve la misma información de lectura que la secretaria y no puede
   registrar, editar ni eliminar movimientos.

---

### User Story 4 - Consultar varias cajas en conjunto (Priority: P4)

Como secretaria o escribano, necesito ver el valor de varias cajas a la vez:
mantengo el desplegable de la caja principal y, debajo, marco otras cajas en
«Ver en conjunto con otras cajas». Quiero ver el **valor en conjunto** (suma de
los saldos de esas cajas), el subtotal de cada una y abrir una solapa
desplegable por caja para revisar su historial.

**Why this priority**: Es el valor nuevo de consulta. Depende de que el flujo de
una sola caja siga intacto (US3).

**Independent Test**: Elegir una caja en el desplegable, marcar dos o más cajas
adicionales, pulsar Consulta y verificar: un **Valor en conjunto** igual a la
suma de los saldos incluidos, un subtotal por cada caja y una solapa
desplegable por cada una con su historial propio. El escribano sigue en solo
lectura.

**Acceptance Scenarios**:

1. **Given** un usuario en Consulta de Caja,
   **When** observa los controles,
   **Then** ve el desplegable de una caja (como hoy), el botón **Consulta**, y
   debajo una sección titulada **Ver en conjunto con otras cajas** con una
   casilla seleccionable por cada caja del catálogo distinta de la del
   desplegable.
2. **Given** el desplegable en «Ebel» y marcadas «Martin» y «Gabriel» en conjunto,
   **When** pulsa **Consulta**,
   **Then** ve el **Valor en conjunto** (suma de los tres saldos), el **subtotal
   (valor actual)** de Ebel, Martin y Gabriel, y **tres solapas desplegables
   todas cerradas**. La **primera** solapa es **Ebel** (caja del desplegable);
   las siguientes siguen el **orden del catálogo** (Martin antes que Gabriel).
   Al expandir una solapa ve el historial de esa caja (mismas columnas, orden y
   paginación de 20 que la consulta individual).
3. **Given** una consulta en conjunto ya mostrada,
   **When** el usuario expande una solapa y contrae otra,
   **Then** el historial de cada caja permanece independiente; expandir o paginar
   una no altera los datos de las demás.
4. **Given** una consulta en conjunto,
   **When** el usuario compara el valor mostrado de cada caja con una consulta
   individual de esa misma caja,
   **Then** el subtotal y cada movimiento coinciden.
5. **Given** el desplegable en «Bambina» y al menos una caja adicional marcada,
   **When** cambia el desplegable a una caja que estaba marcada como adicional,
   **Then** esa caja deja de figurar como adicional (pasa a ser la principal) y
   no aparece duplicada.
6. **Given** un escribano en consulta conjunta,
   **When** visualiza las solapas,
   **Then** puede leer subtotales e historiales de todas las cajas elegidas y no
   puede modificar movimientos.
7. **Given** un usuario que consulta Ebel más Martin,
   **When** falla la carga de cualquiera de las dos,
   **Then** ve un mensaje de error y **no** ve subtotales ni solapas de ese
   intento; puede volver a pulsar Consulta.
8. **Given** el desplegable en «Ebel» (saldo 16800) y marcadas «Chovet» (0) y
   «Maria Teresa» (0),
   **When** pulsa **Consulta** y los tres saldos cargan,
   **Then** ve **Valor en conjunto** `$ 16800.00` **arriba** de las solapas, y
   cada solapa sigue mostrando su propio saldo.

---

### Edge Cases

- Si el cambio de contraseña en el login se intenta con un usuario inexistente o
  contraseña actual incorrecta, el mensaje DEBE ser genérico (igual que un login
  fallido); no se revela si el usuario existe.
- Si la nueva contraseña es igual a la actual, el sistema DEBE rechazar el cambio.
- Si la confirmación no coincide, el sistema DEBE rechazar el cambio sin persistir.
- Si la nueva contraseña no cumple la longitud mínima, el sistema DEBE rechazar
  el cambio.
- Tras un cambio exitoso estando autenticado, cualquier intento de seguir usando
  la sesión anterior DEBE exigir un nuevo inicio de sesión.
- Si en «Ver en conjunto» no hay ninguna caja marcada, la consulta DEBE comportarse
  exactamente como la consulta de una sola caja.
- Si se marcan todas las cajas restantes del catálogo, la consulta conjunta DEBE
  incluir la principal más las 14 adicionales (15 cajas).
- Si una caja del conjunto no tiene movimientos, su subtotal DEBE ser 0 y su
  solapa mostrar historial vacío (sin error).
- Si falla la carga de **cualquiera** de las cajas del conjunto, **falla toda la
  consulta**: mensaje de error claro y **ningún** resultado de ese intento (ni
  subtotales ni solapas parciales). El usuario puede volver a pulsar Consulta.
- Cambiar la caja del desplegable o las marcas de conjunto **antes** de pulsar
  Consulta no DEBE mezclar resultados de una consulta anterior; el usuario debe
  consultar de nuevo para ver el nuevo conjunto.
- Esta feature no introduce recuperación de contraseña olvidada ni alta de
  usuarios por pantalla.

## Requirements *(mandatory)*

### Functional Requirements

**Cambio de contraseña**

- **FR-001**: Todo usuario existente (secretaria o escribano) DEBE poder cambiar
  **su propia** contraseña.
- **FR-002**: El cambio de contraseña DEBE estar disponible en la **pantalla de
  inicio de sesión** mediante un enlace **Cambiar contraseña**. Al activarlo, el
  formulario de ingreso se **reemplaza** por el de cambio (usuario, contraseña
  actual, nueva y confirmación). Tras un cambio exitoso (o si el usuario cancela),
  DEBE volver el formulario de ingreso.
- **FR-003**: El cambio desde el inicio de sesión DEBE exigir: nombre de usuario,
  contraseña actual, nueva contraseña y confirmación de la nueva contraseña.
- **FR-004**: El usuario autenticado DEBE poder abrir una **sección de usuario**
  al tocar su **nombre de usuario** mostrado arriba a la derecha.
- **FR-005**: Esa sección DEBE permitir cambiar la contraseña exigiendo:
  contraseña actual, nueva contraseña y confirmación (el usuario ya está
  identificado; no se pide otro nombre de usuario).
- **FR-006**: La nueva contraseña DEBE tener al menos **8 caracteres**, ser
  distinta de la actual, y coincidir con la confirmación.
- **FR-007**: El sistema DEBE almacenar la nueva contraseña de forma segura (nunca
  en texto plano) y dejar de aceptar la contraseña anterior de inmediato.
- **FR-008**: Un cambio de contraseña **exitoso mientras el usuario está
  autenticado** DEBE invalidar las sesiones de ese usuario; el siguiente acceso
  requiere iniciar sesión con la nueva contraseña.
- **FR-009**: Un cambio **exitoso desde el login** DEBE dejar al usuario en la
  pantalla de inicio de sesión, listo para ingresar con la nueva contraseña (no
  inicia sesión automáticamente).
- **FR-010**: Intentos fallidos de cambio DEBEN registrarse como evento de
  seguridad **sin** incluir la contraseña ni revelar si el usuario existe (en el
  flujo del login).
- **FR-011**: El sistema NO DEBE permitir que un usuario cambie la contraseña de
  otro. No hay recuperación de contraseña olvidada ni auto-registro en esta
  feature.

**Consulta de Caja — una caja (sin cambio de comportamiento)**

- **FR-012**: La pantalla Consulta de Caja DEBE conservar el **desplegable** de
  una caja y el botón **Consulta**.
- **FR-013**: Si el usuario consulta **sin** cajas marcadas en conjunto, el
  sistema DEBE mostrar el valor actual y el historial de **solo** la caja del
  desplegable, con las mismas columnas, orden (más reciente primero) y
  paginación de **20** registros que ya existen.

**Consulta de Caja — conjunto**

- **FR-014**: Debajo del desplegable DEBE existir una sección titulada **Ver en
  conjunto con otras cajas**.
- **FR-015**: Esa sección DEBE listar cada caja del catálogo **excepto** la
  seleccionada en el desplegable, con un control de selección (casilla) por caja.
- **FR-016**: El usuario DEBE poder marcar o desmarcar cualquier combinación de
  esas cajas antes de consultar.
- **FR-017**: Al pulsar **Consulta** con al menos una caja adicional marcada, el
  sistema DEBE incluir en el resultado la caja del desplegable **más** todas las
  marcadas.
- **FR-018**: En consulta conjunta el sistema DEBE mostrar el **subtotal (valor
  actual)** de **cada** caja incluida.
- **FR-018a**: En consulta conjunta el sistema DEBE mostrar, **arriba** de las
  solapas, el **Valor en conjunto**: la suma de los `saldo_actual` de **todas**
  las cajas incluidas en ese intento. La suma se deriva de los saldos ya
  obtenidos del backend (no recalcula movimientos ni inventa un saldo). Si el
  intento falla (FR-021a), no se muestra ese total.
- **FR-019**: En consulta conjunta el sistema DEBE mostrar **una solapa
  desplegable por cada caja** incluida (N solapas para N cajas). El **orden**
  DEBE poner **primero** la caja del desplegable principal y a continuación las
  adicionales en el **orden del catálogo** (el mismo de las 15 cajas del
  sistema), omitiendo la principal. Cada solapa se identifica con el nombre de
  la caja y, al expandirse, muestra el historial de **esa** caja (Descripción,
  Monto, Subtotal, Fecha).
- **FR-019a**: Tras una consulta conjunta, **todas** las solapas DEBEN iniciar
  **cerradas** (visibles el nombre de cada caja y su subtotal; el historial solo
  al expandir).
- **FR-020**: Cada solapa DEBE paginar su historial de forma independiente (20
  por página, página 1 = más recientes), igual que la consulta individual.
- **FR-021**: Los valores e historiales en conjunto DEBEN ser los mismos que se
  obtendrían consultando cada caja por separado; no se mezclan movimientos de
  distintas cajas en una sola tabla.
- **FR-021a**: Si falla la obtención de datos de **cualquier** caja incluida en
  una consulta conjunta, el sistema DEBE **rechazar todo el intento**: mensaje de
  error y sin mostrar subtotales ni solapas de ese intento.
- **FR-022**: Si la caja del desplegable coincide con una marcada como adicional,
  esa caja DEBE quedar solo como principal (sin duplicar).
- **FR-023**: Secretaria y Escribano DEBEN poder usar la consulta conjunta. El
  Escribano permanece en **solo lectura**.
- **FR-024**: Esta feature NO modifica el registro de movimientos ni la sección
  «Registrar también en otras cajas» de Registro de Caja. NO aplica a consulta
  de plazos fijos ni a impresión.

### Key Entities

- **Usuario**: Persona autenticada. Atributos relevantes: nombre de usuario,
  contraseña (almacenada de forma segura), rol (Secretaria | Escribano).
- **Sesión**: Acceso autenticado vigente. Se invalida al cambiar la contraseña
  estando logueado, al cerrar sesión o al cumplirse las 8 horas desde el login
  (regla ya existente).
- **Caja**: Cuenta del catálogo fijo de 15 nombres.
- **Consulta de caja**: Lectura del valor actual y del historial de una caja.
- **Consulta conjunta**: Lectura simultánea de una caja principal (desplegable)
  más un conjunto de cajas adicionales elegidas por el usuario. Cada caja
  conserva su propio subtotal e historial. El **Valor en conjunto** es la suma
  de esos subtotales para el intento actual.

## Assumptions

- «Menú de inicio (cuando se loggea)» se interpreta como la **pantalla de login**,
  con un enlace **Cambiar contraseña** que sustituye el formulario de ingreso por
  el de cambio (usuario + contraseña actual + nueva + confirmación). No es
  recuperación por correo ni por administrador.
- «Sección de usuario» se interpreta como un menú o panel que se abre al tocar el
  **nombre de usuario** arriba a la derecha (hoy el nombre se muestra pero no
  abre un menú).
- Longitud mínima de 8 caracteres es el umbral de fortaleza para esta feature;
  no se exige un alfabeto especial adicional salvo que se enmiende después.
- Tras cambiar la contraseña logueado, invalidar la sesión es la regla de
  seguridad del producto (el usuario vuelve a ingresar).
- «Subtotal de cada caja» en consulta conjunta es el **valor actual** de esa caja
  (el mismo indicador que «Valor de caja» en la consulta individual).
- «Valor en conjunto» es la **suma** de esos valores actuales, mostrada encima
  de las solapas; no sustituye el saldo por caja ni fusiona historiales.
- «Solapas desplegables» son paneles expandibles/colapsables, uno por caja, no
  una fusión de movimientos. Tras Consulta inician **todas cerradas**; la primera
  en la lista es siempre la caja del desplegable principal y las demás siguen el
  orden del catálogo.
- El título visible de la sección adicional es exactamente **Ver en conjunto con
  otras cajas**.
- El alcance de consulta conjunta es **solo Consulta de Caja**, no Registro, no
  plazos fijos, no impresión.
- Sigue vigente: usuarios creados fuera de esta pantalla; sin auto-registro; sin
  olvido de contraseña.

## Testing Strategy

- **Enfoque elegido**: `TDD` — tests escritos antes de la implementación.
- **Rationale**: El cambio de contraseña es superficie de seguridad y la consulta
  conjunta debe preservar la integridad de subtotales e historiales por caja;
  TDD reduce regresiones en ambos.
- **Alcance**: Tests antes de implementar cambio de contraseña (login y sección
  de usuario), invalidación de sesión, consulta individual sin regresiones y
  consulta conjunta (subtotales, solapas independientes, paginación, RBAC de
  solo lectura para escribano).
- **Nota para downstream**: This decision MUST be honored by `/spec-kitti.plan`
  (test contracts) and `/spec-kitti.tasks` (TDD / unit-test tasks generated or
  omitted accordingly).

## Out of Scope

- Recuperación de contraseña olvidada (email, token, administrador).
- Alta, baja o cambio de rol de usuarios desde la interfaz.
- Consulta conjunta en Registro de Caja, plazos fijos o impresión PDF.
- Tabla única que mezcle movimientos de varias cajas.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El 100% de los usuarios de prueba (secretaria y escribano) pueden
  completar un cambio de contraseña desde el login en menos de 2 minutos y
  entrar después solo con la nueva clave.
- **SC-002**: El 100% de los usuarios autenticados de prueba encuentran el cambio
  de contraseña al tocar su nombre arriba a la derecha y completan el flujo en
  menos de 2 minutos.
- **SC-003**: Tras un cambio exitoso, la contraseña anterior falla en el 100% de
  los intentos de acceso; la nueva funciona en el 100%.
- **SC-004**: El 100% de los intentos de cambiar la contraseña de otro usuario, o
  de cambiarla sin la contraseña actual correcta, son rechazados sin alterar la
  clave.
- **SC-005**: Con una sola caja (sin marcas en conjunto), un usuario obtiene el
  mismo resultado que el flujo de consulta vigente (valor + historial paginado)
  en menos de 10 segundos tras pulsar Consulta.
- **SC-006**: Con N cajas en conjunto (2 ≤ N ≤ 15), el usuario ve el **Valor en
  conjunto** igual a la suma de los N saldos, N subtotales y N solapas, y cada
  subtotal e historial coincide con la consulta individual de esa caja en el
  100% de los casos de prueba.
- **SC-007**: Un escribano puede usar login, cambio de contraseña y consulta
  conjunta sin poder modificar movimientos en el 100% de las pruebas.
