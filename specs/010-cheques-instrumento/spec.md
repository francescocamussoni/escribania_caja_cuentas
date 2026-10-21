# Feature Specification: Instrumento Cheque/Echeque, Sección Cheques y Saldo a Futuro

**Feature Branch**: `010-cheques-instrumento`  
**Created**: 2026-10-21  
**Status**: Draft  
**Input**: User description: "Agregar en Registro un desplegable Instrumento (-, Cheque, Echeque) entre Fecha (opcional) y Entrada; los cheques tienen fecha de carga, fecha de liquidación (estimada, futura) y fecha liquidado; no impactan en el subtotal hasta que se los liquida con un botón Liquidar; nueva sección Cheques entre Consulta plazos fijos e Impresión con los cheques próximos a liquidar del mes y los ya aptos para liquidar; en Valor de caja (Registro y Consulta) un desplegable Saldo a futuro que proyecta el saldo según las fechas de liquidación de los cheques pendientes."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Registrar un cheque/echeque sin afectar el subtotal (Priority: P1)

La secretaria recibe (o emite) un cheque o echeque cuyo cobro/pago se hará en una fecha futura. En el formulario de Registro elige **Instrumento = Cheque** (o **Echeque**), completa descripción, monto, moneda y la **Fecha de liquidación** estimada, y pulsa **Entrada** (cheque recibido) o **Salida** (cheque emitido). El cheque aparece en la lista de registros de la caja pero **no modifica el subtotal ni el valor de caja** mientras esté pendiente.

**Why this priority**: Es el núcleo del pedido: sin la posibilidad de cargar un cheque pendiente que no impacte en el saldo, el resto de la feature no tiene sentido.

**Independent Test**: Seleccionar una caja con saldo conocido, elegir Instrumento = Cheque, completar descripción, monto y una fecha de liquidación futura, pulsar **Entrada**; verificar que el cheque aparece en la lista con estado pendiente y que el Valor de caja no cambió.

**Acceptance Scenarios**:

1. **Given** el desplegable **Instrumento** está en su valor por defecto **"-"**, **When** la secretaria registra una entrada o salida, **Then** el movimiento se registra exactamente como hasta ahora (con fecha opcional y descripción) e impacta en el subtotal inmediatamente.
2. **Given** el formulario de Registro, **When** se visualiza, **Then** el desplegable **Instrumento** aparece a la derecha de **Fecha (opcional)** y a la izquierda del botón **Entrada**, con las opciones **"-"** (por defecto), **Cheque** y **Echeque**.
3. **Given** se selecciona **Cheque** o **Echeque**, **When** cambia el formulario, **Then** aparece el campo obligatorio **Fecha de liquidación**.
4. **Given** se selecciona **Cheque** o **Echeque**, **When** se vuelve a seleccionar **"-"**, **Then** el campo **Fecha de liquidación** desaparece y se descarta su valor.
5. **Given** Instrumento = Cheque/Echeque y una Fecha de liquidación **posterior a la fecha actual**, **When** la secretaria pulsa **Entrada** o **Salida**, **Then** se crea el cheque en estado pendiente, aparece en la lista de registros de la caja y el subtotal y el Valor de caja **no cambian**.
6. **Given** Instrumento = Cheque/Echeque y una Fecha de liquidación **igual o anterior a hoy**, o vacía, **When** la secretaria intenta registrar, **Then** el sistema rechaza la operación con un mensaje claro y no se crea ningún registro.
7. **Given** se registró un cheque pendiente, **When** se mira la vista de registros de la caja, **Then** el cheque aparece en un bloque de **cheques pendientes** ubicado arriba de la lista cronológica, con su instrumento (Cheque/Echeque), fechas (carga y liquidación estimada), monto, estado **Pendiente**, **sin subtotal**, y un botón **Liquidar** (solo para la secretaria).
8. **Given** Instrumento = Cheque/Echeque, **When** se usa el formulario, **Then** el botón **"Entrada y Salida"** no está disponible (un cheque es una única operación en un único sentido).

---

### User Story 2 - Liquidar un cheque y registrar la fecha de liquidado (Priority: P1)

Cuando el cheque efectivamente se cobra (o se debita), la secretaria pulsa el botón **Liquidar** en ese registro. El sistema registra la **fecha liquidado** (el momento en que se pulsó) y recién entonces el monto del cheque impacta en el subtotal de la caja.

**Why this priority**: Completa el ciclo de vida del cheque; sin liquidación el dinero nunca llegaría al saldo.

**Independent Test**: Con un cheque pendiente de entrada, pulsar **Liquidar** y verificar que queda registrada la fecha liquidado, que el estado pasa a **Liquidado**, que el botón desaparece y que el subtotal/Valor de caja aumentan por el monto del cheque.

**Acceptance Scenarios**:

1. **Given** un cheque pendiente de tipo entrada con monto M, **When** la secretaria pulsa **Liquidar**, **Then** se guarda la **fecha liquidado**, el estado pasa a **Liquidado**, el Valor de caja de esa moneda aumenta en M y el registro muestra su subtotal.
2. **Given** un cheque pendiente de tipo salida con monto M, **When** se pulsa **Liquidar**, **Then** el Valor de caja de esa moneda disminuye en M.
3. **Given** llegó (o pasó) la fecha de liquidación de un cheque, **When** no se pulsó **Liquidar**, **Then** el cheque sigue pendiente y **no** impacta en el subtotal (la llegada de la fecha no liquida automáticamente).
4. **Given** un cheque ya liquidado, **When** se visualiza, **Then** el botón **Liquidar** no aparece y no puede liquidarse una segunda vez.
5. **Given** un cheque liquidado, **When** se calculan los subtotales de la caja, **Then** el cheque se ubica en el historial según su **fecha liquidado** (no según su fecha de carga) y los subtotales de los movimientos posteriores de esa caja y moneda se mantienen consistentes.
6. **Given** un usuario con rol Escribano, **When** consulta un cheque pendiente, **Then** no ve ni puede ejecutar la acción **Liquidar**.
7. **Given** la secretaria está en la sección **Cheques**, **When** pulsa **Liquidar** sobre un cheque (de cualquier listado), **Then** se aplican los mismos efectos que desde la vista de registros y el cheque desaparece de la sección.

---

### User Story 3 - Sección Cheques: próximos a liquidar y aptos para liquidar (Priority: P2)

Una nueva sección **Cheques** en la barra de navegación, ubicada a la derecha de **Consulta plazos fijos** y a la izquierda de **Impresión**, muestra de **todas las cajas** los cheques/echeques pendientes que requieren atención: los **próximos a liquidar este mes** y los **ya aptos para liquidar** (cuya fecha de liquidación ya llegó o pasó).

**Why this priority**: Da visibilidad transversal a las cajas de los cheques que hay que gestionar, pero depende de que existan cheques cargados (US1).

**Independent Test**: Cargar cheques pendientes en distintas cajas con fechas de liquidación dentro del mes y otros con fecha ya vencida; abrir la sección **Cheques** y verificar que aparecen agrupados en las dos categorías correctas con caja, moneda, monto y fechas.

**Acceptance Scenarios**:

1. **Given** el menú de navegación, **When** se visualiza, **Then** existe la entrada **Cheques** entre **Consulta plazos fijos** e **Impresión**, visible para los roles Secretaria y Escribano.
2. **Given** cheques pendientes en varias cajas, **When** se abre la sección **Cheques**, **Then** se muestran en dos listados diferenciados: **Aptos para liquidar** (fecha de liquidación igual o anterior a hoy) y **Próximos a liquidar este mes** (fecha de liquidación posterior a hoy y dentro del mes calendario actual).
3. **Given** cada cheque listado, **When** se visualiza, **Then** se muestran al menos: caja, instrumento (Cheque/Echeque), descripción, tipo (entrada/salida), moneda, monto, fecha de carga y fecha de liquidación.
4. **Given** un cheque pendiente con fecha de liquidación en un mes posterior al actual, **When** se abre la sección, **Then** ese cheque no aparece.
5. **Given** un cheque ya liquidado, **When** se abre la sección, **Then** ese cheque no aparece.
6. **Given** no hay cheques en ninguna de las dos categorías, **When** se abre la sección, **Then** se muestra un mensaje de lista vacía para cada categoría.
7. **Given** los cheques de la sección, **When** se ordenan, **Then** cada listado se ordena por fecha de liquidación ascendente.

---

### User Story 4 - Saldo a futuro en Valor de caja (Priority: P2)

En la sección **Valor de caja** (tanto en **Registro** como en **Consulta**) se agrega un desplegable **Saldo a futuro**. Al expandirlo muestra el saldo de la caja al día de hoy y, por cada fecha de liquidación en que haya cheques pendientes de esa caja, cuál sería el saldo proyectado considerando el saldo actual y el efecto acumulado (entrada suma, salida resta) de los cheques con fecha de liquidación hasta esa fecha.

**Why this priority**: Aporta planificación financiera sobre los cheques cargados; depende de US1 y es independiente de US3.

**Independent Test**: En una caja con saldo ARS 1000, cargar un cheque de entrada de 500 con liquidación el día D1 y un cheque de salida de 200 con liquidación el día D2 (D2 > D1); expandir **Saldo a futuro** y verificar: Hoy 1000; D1 1500; D2 1300.

**Acceptance Scenarios**:

1. **Given** una caja sin cheques pendientes, **When** se expande **Saldo a futuro**, **Then** se muestra solamente el saldo al día de hoy (por moneda) y un mensaje indicando que no hay cheques pendientes.
2. **Given** una caja con saldo actual S y cheques pendientes en distintas fechas de liquidación, **When** se expande **Saldo a futuro**, **Then** se muestra una fila "Hoy" con S y una fila por cada fecha de liquidación distinta, ordenadas ascendentemente, con el saldo proyectado **acumulado** (S + efecto de todos los cheques pendientes con fecha de liquidación menor o igual a esa fecha).
3. **Given** dos o más cheques pendientes con la misma fecha de liquidación, **When** se expande **Saldo a futuro**, **Then** se muestra una única fila para esa fecha cuyo saldo incluye el efecto de todos ellos.
4. **Given** la caja maneja ARS y USD, **When** se muestra el saldo a futuro, **Then** las proyecciones de ARS y USD se calculan y muestran por separado, sin mezclarse.
5. **Given** un cheque de tipo salida, **When** entra en la proyección, **Then** resta de la proyección; un cheque de tipo entrada suma.
6. **Given** cheques pendientes cuya fecha de liquidación ya llegó o pasó, **When** se expande **Saldo a futuro**, **Then** siguen incluidos en la proyección y se identifican como **vencidos / aptos para liquidar**, sin ocultarse.
7. **Given** se liquida un cheque, **When** se vuelve a expandir **Saldo a futuro**, **Then** ese cheque ya no figura como proyección futura (su efecto pasó a formar parte del saldo actual).
8. **Given** el usuario está en **Consulta** (Escribano o Secretaria) con una caja consultada, **When** expande **Saldo a futuro**, **Then** ve la misma información que en **Registro** para esa caja.

---

### User Story 5 - Gestión de cheques pendientes: edición y eliminación (Priority: P3)

La secretaria puede corregir o eliminar un cheque pendiente cargado por error (monto, descripción, tipo, instrumento entre Cheque y Echeque, fecha de liquidación), sin afectar subtotales porque aún no impacta en el saldo.

**Why this priority**: Es una necesidad operativa de corrección; no bloquea el flujo principal.

**Independent Test**: Cargar un cheque pendiente, editar su monto y fecha de liquidación, verificar que se actualiza sin cambios en el Valor de caja; luego eliminarlo y verificar que desaparece de la lista y del Saldo a futuro.

**Acceptance Scenarios**:

1. **Given** un cheque pendiente, **When** la secretaria edita su monto, descripción, tipo o fecha de liquidación, **Then** los cambios se guardan y el subtotal de la caja no se altera.
2. **Given** se edita la fecha de liquidación de un cheque pendiente, **When** la nueva fecha es igual o anterior a hoy, **Then** el sistema rechaza el cambio con un mensaje claro.
3. **Given** un cheque pendiente, **When** la secretaria lo elimina, **Then** desaparece de la lista de registros, de la sección **Cheques** y del **Saldo a futuro**, sin cambiar subtotales.
4. **Given** un cheque ya liquidado, **When** se edita o elimina, **Then** se aplican las mismas reglas que hoy rigen para cualquier movimiento (incluido el recálculo en cascada de subtotales de esa caja y moneda).
5. **Given** un cheque o echeque, **When** la secretaria cambia su instrumento entre **Cheque** y **Echeque**, **Then** el cambio se guarda sin alterar subtotales ni su estado.
6. **Given** un cheque o echeque, **When** se intenta cambiar su instrumento a **"-"**, o un movimiento común se intenta convertir en Cheque/Echeque, **Then** el sistema no lo permite (la edición no ofrece esa opción y el servidor rechaza el intento); para corregirlo se debe eliminar el registro y cargarlo de nuevo.

---

### User Story 6 - Informe impreso de caja con cheques pendientes y saldo a futuro (Priority: P3)

Al generar el informe PDF de una caja en **Impresión**, el documento incluye una sección separada con los **cheques pendientes** de esa caja y el **saldo a futuro**, para que el documento entregado o archivado refleje también lo que está por liquidarse sin alterar los saldos reales.

**Why this priority**: Complementa la visibilidad de cheques en un entregable formal; depende de US1 (cheques) y US4 (saldo a futuro).

**Independent Test**: En una caja con saldo ARS 1000, un cheque pendiente de entrada de 500 (liquidación D1) y movimientos en el período, generar el informe de Caja y verificar: movimientos del período sin el cheque pendiente, saldos al cierre y actual sin cambios, sección **Cheques pendientes** con el cheque, y **Saldo a futuro** con Hoy 1000 y D1 1500.

**Acceptance Scenarios**:

1. **Given** una caja con cheques pendientes, **When** se genera el informe de tipo **Caja**, **Then** el PDF muestra una sección **Cheques pendientes** separada del listado de movimientos, con los datos de cada cheque, y los cheques pendientes no figuran en el listado de movimientos ni afectan los saldos del informe.
2. **Given** una caja con cheques pendientes de fechas distintas, **When** se genera el informe, **Then** el PDF incluye el **Saldo a futuro** con la misma información que el desplegable en pantalla (Hoy y una fila acumulada por cada fecha de liquidación, separado por ARS y USD).
3. **Given** el informe se genera con un período pasado (por ejemplo un mes anterior), **When** se revisa el PDF, **Then** la sección **Cheques pendientes** y el **Saldo a futuro** reflejan el estado actual de la caja (no el del período) y se indica la fecha/hora de generación.
4. **Given** una caja sin cheques pendientes, **When** se genera el informe, **Then** la sección **Cheques pendientes** indica que no hay y el **Saldo a futuro** muestra solo el saldo de hoy.
5. **Given** un cheque liquidado cuya fecha liquidado cae dentro del período del informe, **When** se genera el informe, **Then** aparece en el listado de movimientos con la indicación Cheque/Echeque y su subtotal.
6. **Given** el informe de tipo **Plazos Fijos**, **When** se genera, **Then** no incluye cambios por esta feature.

---

### Edge Cases

- ¿Qué pasa si se elige Instrumento = Cheque pero se deja vacía la Fecha de liquidación? → Se rechaza con mensaje de campo obligatorio.
- ¿Qué pasa si la Fecha de liquidación es hoy? → Se rechaza: debe ser estrictamente posterior a la fecha actual.
- ¿Qué pasa si el cheque se registra con la **Fecha (opcional)** completada? → Esa fecha se toma como **fecha de carga** del cheque (misma regla actual: 09:00 hora Argentina); si está vacía, la fecha de carga es el momento del registro. La validación de Fecha de liquidación se hace siempre contra la fecha actual real.
- ¿Qué pasa si se usan **cajas adicionales** al registrar un cheque? → El cheque se replica en cada caja adicional con los mismos datos, igual que los movimientos comunes; cada uno es un cheque pendiente independiente.
- ¿Qué pasa si un cheque pendiente no se liquida nunca? → Permanece pendiente y visible en **Aptos para liquidar** y en **Saldo a futuro** (como vencido) hasta que se liquide o se elimine.
- ¿Qué pasa si se pulsa **Liquidar** dos veces seguidas o desde dos pantallas? → Solo la primera liquidación tiene efecto; la segunda se rechaza sin duplicar el impacto en el saldo.
- ¿Qué pasa si falla la liquidación? → Se muestra un mensaje de error genérico, el cheque permanece pendiente y el saldo no cambia.
- ¿Qué pasa con los registros históricos existentes (previos a esta feature)? → Se consideran con Instrumento "-": comportamiento y subtotales sin cambios.
- ¿Qué pasa con **Subtotal general** y **Valor en conjunto** en Consulta? → Solo consideran cheques liquidados; los pendientes nunca impactan.
- ¿Qué pasa con el historial al filtrar por fechas (Desde/Hasta) o por moneda? → El bloque de cheques pendientes se filtra por moneda y por fecha de carga; la lista cronológica filtra los liquidados por su fecha liquidado.
- ¿Qué pasa con la zona horaria al determinar "hoy" y "este mes"? → Se usa la fecha de Argentina (UTC-3).

## Requirements *(mandatory)*

### Functional Requirements

**Formulario de Registro (Instrumento)**

- **FR-001**: El formulario de Registro DEBE mostrar un desplegable **Instrumento** ubicado a la derecha de **Fecha (opcional)** y a la izquierda del botón **Entrada**, con las opciones **"-"**, **Cheque** y **Echeque**.
- **FR-002**: El valor por defecto de **Instrumento** DEBE ser **"-"**. Con ese valor el comportamiento DEBE ser idéntico al actual (movimiento con descripción, monto, moneda y fecha opcional que impacta en el subtotal de inmediato).
- **FR-003**: Al seleccionar **Cheque** o **Echeque**, el formulario DEBE mostrar el campo obligatorio **Fecha de liquidación**; al volver a **"-"** DEBE ocultarlo y descartar su valor.
- **FR-004**: El sistema DEBE validar en el servidor que la **Fecha de liquidación** sea estrictamente posterior a la fecha actual (zona horaria Argentina) al crear un cheque, y rechazar la operación con un mensaje claro en caso contrario.
- **FR-005**: Cuando **Instrumento** sea Cheque o Echeque, el botón **"Entrada y Salida"** NO DEBE estar disponible. Los botones **Entrada** y **Salida** DEBEN seguir funcionando indicando el sentido del cheque (recibido / emitido).
- **FR-006**: Tras un registro exitoso, el formulario DEBE volver a su estado inicial de Instrumento (**"-"**) y limpiar la Fecha de liquidación; la Fecha (opcional) se comporta como hoy.
- **FR-007**: Las validaciones existentes (descripción y monto obligatorios, monto válido, moneda ARS/USD) DEBEN aplicarse igual a los cheques.

**Ciclo de vida del cheque**

- **FR-008**: Cada cheque/echeque DEBE conservar tres fechas: **Fecha de carga** (cuando se registra, o la Fecha (opcional) si se informó), **Fecha de liquidación** (estimada de cobro/pago, futura al cargarlo) y **Fecha liquidado** (vacía hasta que se liquide).
- **FR-009**: Un cheque DEBE tener un estado: **Pendiente** (sin fecha liquidado) o **Liquidado** (con fecha liquidado).
- **FR-010**: Un cheque **Pendiente** NO DEBE impactar en el subtotal ni en el Valor de caja de su caja y moneda, ni al cargarse ni al llegar o superarse su fecha de liquidación.
- **FR-011**: Cada cheque pendiente DEBE mostrar un botón **Liquidar** en la vista de registros de su caja y en la sección **Cheques** (FR-021), disponible solo para el rol Secretaria.
- **FR-012**: Al pulsar **Liquidar**, el sistema DEBE registrar la **Fecha liquidado** con el momento actual, cambiar el estado a Liquidado e incorporar el monto del cheque al subtotal de su caja y moneda (entrada suma, salida resta), ubicándolo en el historial según su fecha liquidado (momento de pulsar **Liquidar**, es decir al final del historial) y no según su fecha de carga; los subtotales de movimientos anteriores no se modifican. La fecha de carga se conserva como dato informativo.
- **FR-013**: El sistema DEBE impedir liquidar un cheque que ya está liquidado (sin duplicar el impacto en el saldo).
- **FR-014**: La liquidación DEBE ser atómica: si falla, el cheque permanece pendiente y el saldo no cambia.
- **FR-015**: La vista de registros de la caja DEBE mostrar los cheques **pendientes** en un bloque separado ubicado **arriba de la lista cronológica** de movimientos, con instrumento, estado, fecha de carga, fecha de liquidación, monto y botón **Liquidar**, sin subtotal numérico. Al liquidarse, el cheque pasa a la lista cronológica con su fecha liquidado y su subtotal, distinguiéndose visualmente (instrumento Cheque/Echeque, estado Liquidado) de los movimientos comunes.
- **FR-016**: La secretaria DEBE poder editar y eliminar cheques pendientes sin afectar subtotales; al editar la Fecha de liquidación se aplica la regla de FR-004. El instrumento de un registro SOLO PUEDE cambiarse entre Cheque y Echeque; NO DEBE permitirse cambiarlo hacia o desde "-" (ni en la interfaz ni en el servidor). Para cheques liquidados rigen las reglas actuales de edición/eliminación de movimientos, incluido el recálculo en cascada.

**Sección Cheques**

- **FR-017**: La barra de navegación DEBE incluir la sección **Cheques** ubicada entre **Consulta plazos fijos** e **Impresión**, visible para los roles Secretaria y Escribano.
- **FR-018**: La sección **Cheques** DEBE mostrar los cheques pendientes de **todas las cajas** en dos listados: **Aptos para liquidar** (fecha de liquidación igual o anterior a hoy) y **Próximos a liquidar este mes** (fecha de liquidación posterior a hoy y dentro del mes calendario actual).
- **FR-019**: Cada cheque listado DEBE mostrar caja, instrumento, descripción, tipo, moneda, monto, fecha de carga y fecha de liquidación; cada listado DEBE ordenarse por fecha de liquidación ascendente y estar paginado o acotado de forma razonable.
- **FR-020**: Los cheques liquidados y los pendientes con fecha de liquidación en meses posteriores NO DEBEN aparecer en la sección **Cheques**.
- **FR-021**: Cada cheque de la sección **Cheques** (tanto en **Aptos para liquidar** como en **Próximos a liquidar este mes**) DEBE incluir un botón **Liquidar**, visible y operable solo para el rol Secretaria; para el Escribano la sección es de solo lectura. La acción es la misma que en la vista de registros (FR-011 a FR-014). Tras liquidar, el cheque desaparece de la sección y los listados se actualizan.

**Saldo a futuro**

- **FR-022**: Las secciones **Valor de caja** de **Registro** y de **Consulta** DEBEN incluir un desplegable **Saldo a futuro**, colapsado por defecto.
- **FR-023**: Al expandirse, el desplegable DEBE mostrar el saldo al día de hoy y, por cada fecha de liquidación distinta entre los cheques pendientes de la caja, una fila con el **saldo proyectado acumulado** (saldo actual + efecto neto de todos los cheques pendientes con fecha de liquidación menor o igual a esa fecha), ordenadas por fecha ascendente.
- **FR-024**: La proyección DEBE calcularse de forma independiente por moneda (ARS y USD), sin mezclarlas, y DEBE agrupar en una sola fila los cheques con la misma fecha de liquidación.
- **FR-025**: Los cheques pendientes con fecha de liquidación vencida DEBEN incluirse en la proyección e identificarse como vencidos / aptos para liquidar.
- **FR-026**: El cálculo del saldo a futuro DEBE realizarse en el servidor (el frontend solo lo presenta) y DEBE reflejar de inmediato altas, ediciones, eliminaciones y liquidaciones de cheques.

**Permisos, seguridad y compatibilidad**

- **FR-027**: Solo el rol Secretaria PUEDE crear, editar, eliminar y liquidar cheques; el Escribano solo consulta. La autorización DEBE aplicarse en el servidor y rechazar con 403 los intentos no autorizados.
- **FR-028**: Toda creación, edición, eliminación y liquidación de un cheque DEBE registrar el usuario que la realizó (auditoría mínima).
- **FR-029**: **Subtotal general**, **Valor en conjunto** y los saldos (al cierre del período y actual) de los informes de **Impresión** DEBEN basarse solo en movimientos que impactan el saldo (los cheques pendientes no se contabilizan en ellos).
- **FR-030**: Los movimientos existentes DEBEN conservar su comportamiento y subtotales sin ninguna modificación; se tratan como Instrumento "-".

**Informe de Impresión (tipo Caja)**

- **FR-031**: El informe PDF de tipo **Caja** DEBE listar en el cuerpo del informe los movimientos que impactan el saldo (comunes y cheques liquidados, estos últimos con la indicación Cheque/Echeque y su fecha liquidado) y, a continuación, una **sección aparte "Cheques pendientes"** claramente separada, que NO se suma a ningún saldo. Esa sección lista todos los cheques/echeques pendientes de la caja al momento de generar el informe (no se filtra por el período elegido), con instrumento, descripción, tipo, moneda, monto, fecha de carga y fecha de liquidación. Si no hay cheques pendientes, la sección indica que no hay.
- **FR-032**: El informe PDF de tipo **Caja** DEBE incluir además el **Saldo a futuro** de la caja con el mismo cálculo y los mismos criterios que el desplegable de FR-023 a FR-025 (saldo actual y saldo proyectado acumulado por cada fecha de liquidación, separado por ARS y USD, con los vencidos identificados), calculado al momento de generar el informe y a partir del **saldo actual** (no del saldo al cierre del período). Si no hay cheques pendientes, solo se muestra el saldo de hoy.
- **FR-033**: El resto del informe (encabezado, saldo al cierre del período impreso, saldo actual, orden y formato) y el informe de Plazos Fijos DEBEN conservar su comportamiento actual.

### Key Entities

- **Movimiento**: entidad existente (entrada/salida de una caja y moneda). Se extiende con un **instrumento** (ninguno, cheque o echeque).
- **Cheque / Echeque**: un movimiento con instrumento Cheque o Echeque. Atributos de negocio: caja, descripción, tipo (entrada = recibido / salida = emitido), moneda, monto, fecha de carga, fecha de liquidación (estimada), fecha liquidado (opcional hasta liquidar), estado derivado (Pendiente / Liquidado), usuario que lo registró.
- **Saldo a futuro (proyección)**: vista calculada, no persistida, de la evolución esperada del saldo de una caja por moneda: saldo actual y saldos acumulados por cada fecha de liquidación de cheques pendientes.
- **Caja**: entidad existente; sus subtotales por moneda solo reflejan movimientos comunes y cheques liquidados.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: La secretaria puede cargar un cheque (instrumento, fecha de liquidación, descripción y monto) en menos de 30 segundos.
- **SC-002**: El 100% de los cheques pendientes dejan inalterado el Valor de caja de la caja y moneda correspondiente, antes y después de llegar su fecha de liquidación.
- **SC-003**: El 100% de las liquidaciones actualizan el Valor de caja por exactamente el monto del cheque (suma si es entrada, resta si es salida) y registran la fecha liquidado.
- **SC-004**: El 100% de los intentos de cargar un cheque con fecha de liquidación vacía, de hoy o pasada son rechazados con un mensaje claro.
- **SC-005**: La sección **Cheques** muestra el 100% de los cheques pendientes que ya son aptos para liquidar o vencen en el mes actual, en todas las cajas, y ninguno que no cumpla esas condiciones.
- **SC-006**: Para cualquier caja, el saldo proyectado en la última fila de **Saldo a futuro** es igual al saldo actual más el efecto neto de todos los cheques pendientes de esa caja (verificable por cálculo manual).
- **SC-007**: El flujo de registro sin instrumento ("-") no presenta ninguna regresión: el 100% de los movimientos comunes mantienen su comportamiento y subtotales.
- **SC-008**: El desplegable **Saldo a futuro** se muestra en menos de 2 segundos para una caja con hasta 100 cheques pendientes.
- **SC-009**: El 100% de los informes de Caja generados incluyen la sección **Cheques pendientes** y el **Saldo a futuro**, con valores idénticos a los mostrados en pantalla al momento de generarlos, y sin alterar los saldos al cierre ni actual.

## Testing Strategy

- **Enfoque elegido:** TDD — tests escritos antes de la implementación para toda la feature.
- **Rationale:** La feature modifica la lógica de integridad financiera (exclusión de cheques pendientes del subtotal, impacto al liquidar y proyección de saldo a futuro por moneda). TDD reduce el riesgo de regresiones silenciosas en los streams ARS/USD. Los tests de integración de subtotales y RBAC siguen siendo obligatorios según la constitución.
- **Scope note:** Esta decisión DEBE ser respetada por `/spec-kitti.plan` (contratos de test) y `/spec-kitti.tasks` (generar tareas TDD-first antes de cada tarea de implementación).

## Clarifications

### Session 2026-10-21

- Q: ¿Querés aplicar TDD y/o Unit Tests estrictos para esta feature? → A: TDD-first — tests escritos antes de la implementación para toda la feature.
- Q: Al liquidar, ¿en qué posición del historial se ubica el cheque? → A: Según la fecha liquidado (momento de pulsar Liquidar), es decir al final del historial; la fecha de carga queda como dato informativo.
- Q: ¿Cómo se tratan en Saldo a futuro los cheques pendientes con fecha de liquidación vencida? → A: Se incluyen en la proyección, marcados como vencidos / aptos para liquidar, en una fila por cada fecha original de liquidación.
- Q: ¿Dónde se ubican los cheques pendientes en la lista de registros? → A: En un bloque separado arriba de la lista cronológica (con fecha de carga y de liquidación); al liquidarse pasan a la lista cronológica con su fecha liquidado.
- Q: ¿Se puede liquidar desde la sección Cheques? → A: Sí, botón Liquidar en cada cheque de ambos listados (Aptos y Próximos), solo visible para la Secretaria.
- Q: ¿Se puede cambiar el instrumento al editar un registro? → A: Solo entre Cheque y Echeque; no hacia ni desde "-" (para corregirlo se elimina y se vuelve a cargar).
- Q: ¿Cómo aparecen los cheques pendientes en los informes de Impresión? → A: El informe de Caja incluye los movimientos que impactan el saldo más una sección aparte "Cheques pendientes" (sin sumarse a saldos), y además el Saldo a futuro de la caja (a partir del saldo actual, al momento de generar el informe).

## Assumptions

- Un cheque se registra como **Entrada** (cheque recibido) o **Salida** (cheque emitido) usando los botones existentes; no se agrega un tercer tipo.
- Los cheques usan las monedas existentes (ARS / USD) y cada uno pertenece a una sola caja y a un solo stream (caja, moneda).
- "Fecha actual" y "este mes" se evalúan en zona horaria Argentina (UTC-3), consistente con el resto del sistema.
- Al liquidar, la fecha liquidado es el momento en que se pulsa **Liquidar**; no se permite elegir otra fecha en esta versión.
- No se contempla "deshacer" una liquidación ni el rechazo/rebote de cheques en esta versión.
- La sección **Cheques** es visible para ambos roles; la acción **Liquidar** está disponible tanto en la vista de registros de la caja como en la sección **Cheques**, y solo para la Secretaria.
- El **Saldo a futuro** solo proyecta cheques pendientes; no considera plazos fijos ni otros conceptos.
- En **Consulta**, el **Saldo a futuro** aplica a la consulta de una caja individual (Valor de caja); la vista en conjunto y el Subtotal general no incluyen proyección.
- Los cheques pendientes de cajas archivadas siguen apareciendo en la sección **Cheques** hasta que se liquiden o eliminen.
- El informe de **Impresión** de tipo **Caja** se extiende con la sección **Cheques pendientes** y con el **Saldo a futuro** (FR-031 y FR-032). Ambos reflejan el estado de la caja al momento de generar el informe y no se filtran por el período elegido. El informe de Plazos Fijos no cambia.
- La disposición del formulario de Registro, la barra de navegación y los paneles de Valor de caja se extienden respecto a los wireframes `.drawio` vigentes; esta desviación de layout deberá documentarse en el plan (Principio III de la constitución).
- Las tareas de UI generadas en `/spec-kitti.tasks` requerirán la referencia de diseño correspondiente según las reglas del proyecto.
