# Feature Specification: Selección de Moneda en Registro de Cajas

**Feature Branch**: `008-caja-monedas`  
**Created**: 2026-09-07  
**Status**: Draft  
**Input**: User description: "Quiero agregar para el registro de cajas la selección de monedas. Por defecto ARS, con opción ARS o USD. En USD, al tocar Entrada preguntar si registrar también como salida; al tocar Salida preguntar si registrar también como entrada. En ARS mantener el comportamiento actual. En la lista, el monto debe indicar la moneda y se debe poder filtrar por fecha y por moneda."

## Clarifications

### Session 2026-09-07

- Q: Al confirmar el cartel de movimiento complementario en USD, ¿qué se guarda? → A: **Dos movimientos en USD** — mismo monto, misma caja y descripción, tipos opuestos (entrada + salida). No es canje a ARS ni un único asiento.
- Q: Do you want to apply TDD (Test-Driven Development) and/or strict Unit Tests for this feature? → A: **Yes — TDD-first** (tests authored before implementation).
- Q: ¿Cómo funciona el filtro por fecha en el listado? → A: **Rango inclusive** — fechas desde y hasta; se puede dejar un extremo vacío.
- Q: ¿Qué muestra Valor de caja cuando el listado está filtrado? → A: **Siempre los dos saldos** (ARS y USD), aunque el listado esté filtrado por moneda o por fechas.
- Q: Si el par USD confirmado no se puede guardar por completo, ¿qué queda? → A: **Todo o nada** — si falla cualquiera de los dos, no queda ninguno y se informa el error.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Registrar movimiento indicando moneda (Priority: P1)

Como secretaria, necesito elegir si un movimiento de caja es en pesos argentinos (ARS) o en dólares (USD), con ARS como valor inicial, para que cada ingreso o egreso quede registrado en la moneda correcta.

**Why this priority**: Sin moneda en el alta no hay historial confiable ni filtros posteriores. Es el cambio mínimo que entrega valor.

**Independent Test**: Con una secretaria autenticada se puede cambiar la moneda, registrar una entrada o salida y verificar que el movimiento queda persistido y visible con esa moneda.

**Acceptance Scenarios**:

1. **Given** una secretaria en Registro de Caja,
   **When** abre el formulario de un movimiento nuevo,
   **Then** el selector de moneda muestra **ARS** por defecto y permite elegir solo **ARS** o **USD**.
2. **Given** una secretaria con moneda **ARS** y datos válidos de descripción y monto,
   **When** presiona **Entrada** o **Salida**,
   **Then** se registra un único movimiento en ARS, sin cartel adicional, igual que el comportamiento actual.
3. **Given** una secretaria con moneda **USD** y datos válidos,
   **When** confirma el registro (aceptando o rechazando el cartel de movimiento complementario),
   **Then** el movimiento principal queda en USD con el tipo elegido (entrada o salida).
4. **Given** una secretaria que cambia de caja o recarga la pantalla de registro,
   **When** vuelve a cargar un movimiento,
   **Then** la moneda del formulario vuelve a **ARS** (valor por defecto de cada alta).

---

### User Story 2 - Movimiento complementario solo en USD (Priority: P1)

Como secretaria, cuando registro un movimiento en dólares necesito que el sistema me pregunte si también debo registrar el tipo opuesto, para no olvidar el par de asientos habitual en USD y sin cambiar el flujo de pesos.

**Why this priority**: Es el comportamiento diferencial pedido para USD; sin él la feature queda incompleta respecto al uso real.

**Independent Test**: Puede probarse registrando en USD una entrada y una salida, aceptando y rechazando el cartel, y verificando cuántos movimientos se crean. En ARS no debe aparecer ningún cartel.

**Acceptance Scenarios**:

1. **Given** una secretaria con moneda **USD**, descripción y monto válidos,
   **When** presiona **Entrada**,
   **Then** aparece un cartel con el texto **¿Registrar también como salida?** y opciones para confirmar o rechazar.
2. **Given** una secretaria con moneda **USD**, descripción y monto válidos,
   **When** presiona **Salida**,
   **Then** aparece un cartel con el texto **¿Registrar también como entrada?** y opciones para confirmar o rechazar.
3. **Given** el cartel de movimiento complementario visible,
   **When** la secretaria confirma y ambos movimientos se guardan,
   **Then** se registran **dos** movimientos independientes en la misma caja, misma descripción, **mismo monto en USD**, misma moneda USD y tipos opuestos (el accionado y el complementario). No se crea movimiento en ARS ni se pide cotización. El saldo USD de esa caja puede no cambiar si ambos montos son iguales.
4. **Given** el cartel de movimiento complementario visible,
   **When** la secretaria confirma y el guardado falla (cualquiera de los dos),
   **Then** no queda ningún movimiento nuevo de ese intento, se muestra un error claro y puede reintentar.
5. **Given** el cartel de movimiento complementario visible,
   **When** la secretaria rechaza o cierra sin confirmar,
   **Then** se registra **solo** el movimiento del botón presionado (entrada o salida), en USD.
6. **Given** una secretaria con moneda **ARS**,
   **When** presiona **Entrada** o **Salida**,
   **Then** no aparece ningún cartel de movimiento complementario y se guarda un único movimiento.

---

### User Story 3 - Ver moneda en el listado y filtrar por fecha y moneda (Priority: P2)

Como secretaria o escribano, necesito ver a qué moneda corresponde cada monto del historial y acotar la lista por fecha y por moneda, para encontrar movimientos sin mezclar pesos y dólares ni recorrer fechas irrelevantes.

**Why this priority**: Completa la operación diaria de consulta; depende de que los movimientos ya tengan moneda (US1).

**Independent Test**: Con un historial que mezcle ARS, USD y distintas fechas, se verifica la etiqueta de moneda en cada monto y que los dos filtros (juntos o por separado) reduzcan la lista de forma correcta, incluyendo consulta de caja.

**Acceptance Scenarios**:

1. **Given** un historial con movimientos ARS y USD,
   **When** la secretaria o el escribano ve la lista de registros de esa caja,
   **Then** cada monto indica de forma explícita si es ARS o USD (no se muestra un número sin moneda).
2. **Given** un historial con movimientos en ambas monedas,
   **When** el usuario filtra por moneda **USD** (o **ARS**),
   **Then** la lista y la paginación muestran solo movimientos de esa moneda.
3. **Given** un historial con movimientos en varios días,
   **When** el usuario filtra con **desde** y/o **hasta** (rango inclusive; un extremo puede quedar vacío),
   **Then** la lista muestra solo movimientos cuya fecha de movimiento cae en ese rango. Un mismo día en ambos extremos equivale a filtrar ese único día.
4. **Given** filtros de fecha y moneda aplicados a la vez,
   **When** el usuario consulta el historial,
   **Then** se aplican ambos criterios (un movimiento debe cumplir fecha y moneda).
5. **Given** filtros activos,
   **When** el usuario los quita o elige “todas las monedas” y deja las fechas vacías,
   **Then** vuelve a ver el historial completo de la caja (paginado como hasta ahora) y el valor de caja sigue mostrando ambos saldos, igual que con los filtros aplicados.
6. **Given** un escribano en Consulta de Caja,
   **When** consulta una caja,
   **Then** ve la misma indicación de moneda en el monto y puede filtrar por fecha y por moneda, sin poder registrar movimientos.

---

### Edge Cases

- ¿Qué ocurre si el usuario cierra el cartel de USD sin responder? Se trata como rechazo: solo se registra el movimiento del botón presionado.
- ¿Qué ocurre si falla el guardado del par USD confirmado? **Todo o nada**: no queda el movimiento principal ni el complementario; se informa el error y la secretaria puede reintentar. No se deja un solo renglón a medias ni un éxito aparente.
- ¿Qué ocurre con movimientos existentes anteriores a esta feature? Se interpretan como **ARS**.
- ¿Qué ocurre si se filtra por un rango de fechas sin movimientos? La lista queda vacía, con mensaje claro, sin páginas inventadas.
- ¿Qué ocurre si el monto es cero, negativo o falta la descripción? Se rechaza el alta **antes** de mostrar el cartel de USD, igual que las validaciones actuales.
- ¿Qué ocurre al editar o eliminar un movimiento (ventana de 24 h)? La moneda forma parte del movimiento; el recálculo de subtotales se hace **por caja y por moneda**, sin mezclar ARS con USD. Editar o borrar un movimiento de un par USD no borra automáticamente el otro.
- ¿Qué ocurre con el valor de caja si hay ARS y USD? No se suman entre sí: se muestran saldos separados por moneda. Los filtros del listado no alteran esos saldos.
- ¿Qué ocurre si se elige una moneda distinta de ARS o USD? No está permitido; el sistema solo acepta esas dos.

## Requirements *(mandatory)*

### Functional Requirements

**Alta de movimientos**

- **FR-001**: En Registro de Caja, el formulario de movimiento DEBE incluir un selector de moneda ubicado junto al monto, según la disposición de `willing.drawio` (Descripción, Monto, Moneda, Entrada, Salida).
- **FR-002**: El selector de moneda DEBE ofrecer únicamente **ARS** y **USD**.
- **FR-003**: El valor inicial del selector DEBE ser **ARS** en cada alta nueva.
- **FR-004**: Cada movimiento DEBE persistir su moneda (ARS o USD) junto con descripción, monto, tipo, subtotal, fecha, caja y usuario.
- **FR-005**: Con moneda **ARS**, **Entrada** y **Salida** DEBEN comportarse como hoy: un solo movimiento, sin confirmación extra.
- **FR-006**: Con moneda **USD**, al accionar **Entrada** el sistema DEBE mostrar un cartel con el texto exacto **¿Registrar también como salida?** antes de completar el flujo.
- **FR-007**: Con moneda **USD**, al accionar **Salida** el sistema DEBE mostrar un cartel con el texto exacto **¿Registrar también como entrada?** antes de completar el flujo.
- **FR-008**: Si la secretaria confirma el cartel, el sistema DEBE registrar el movimiento accionado y un segundo movimiento complementario: misma caja, misma descripción, **mismo monto**, **misma moneda USD** y tipo opuesto. El complementario NO DEBE ser un canje a ARS ni un alta con otro monto.
- **FR-008a**: El alta del par USD confirmado DEBE ser **todo o nada**: si no se pueden persistir ambos movimientos, NO DEBE quedar ninguno de los dos y el sistema DEBE informar el error.
- **FR-009**: Si la secretaria no confirma el cartel, el sistema DEBE registrar únicamente el movimiento accionado.
- **FR-010**: El cartel de movimiento complementario NO DEBE mostrarse cuando la moneda es ARS.
- **FR-011**: Las validaciones de descripción y monto DEBEN aplicarse antes de mostrar el cartel de USD.

**Saldos e integridad**

- **FR-012**: El subtotal de cada movimiento DEBE calcularse como acumulado cronológico **de esa caja y de esa moneda**; ARS y USD NO DEBEN mezclarse en un mismo acumulado.
- **FR-013**: El valor de caja DEBE mostrar el saldo en **ARS** y el saldo en **USD** de forma distinguible (no un único total combinado). Esos dos saldos DEBEN ser los de la caja completa y **NO DEBEN** cambiar al aplicar filtros de listado (fecha o moneda).
- **FR-014**: Tras editar o eliminar un movimiento dentro de la ventana de 24 horas, el recálculo de subtotales posteriores DEBE aplicarse solo a la misma caja y la misma moneda.
- **FR-015**: Los movimientos históricos sin moneda persistida DEBEN tratarse como **ARS**.

**Listado y filtros**

- **FR-016**: En la lista de registros (Registro de Caja y Consulta de Caja), cada monto DEBE indicar la moneda a la que corresponde (ARS o USD).
- **FR-017**: El usuario DEBE poder filtrar el historial de la caja seleccionada **por moneda** (ARS, USD o todas).
- **FR-018**: El usuario DEBE poder filtrar el historial **por fecha** mediante un **rango inclusive** con **desde** y **hasta**. Cualquiera de los dos extremos PUEDE omitirse (solo desde = desde esa fecha en adelante; solo hasta = hasta esa fecha inclusive). No hay un control separado de “un solo día”: para un día concreto se usa la misma fecha en ambos extremos o un solo extremo equivalente según la regla anterior.
- **FR-019**: Fecha y moneda DEBEN poder usarse en conjunto; un movimiento visible DEBE cumplir todos los filtros activos.
- **FR-020**: Con filtros activos, la paginación DEBE aplicarse al conjunto filtrado (20 registros por página, más recientes primero), sin mezclar páginas de distintos filtros.
- **FR-021**: El rol Escribano DEBE ver moneda y filtros en consulta y NO DEBE poder registrar, confirmar carteles de USD ni modificar movimientos.

**Alcance y seguridad**

- **FR-022**: Esta feature aplica a movimientos de **caja**; no cambia plazos fijos ni implica conversión automática entre ARS y USD ni tipo de cambio.
- **FR-023**: La moneda enviada en el alta DEBE validarse en el servidor (solo ARS o USD); el cliente no es la fuente de autorización ni de integridad.
- **FR-024**: El layout de alta DEBE seguir `willing.drawio` como referencia de disposición del selector de moneda; `actual.drawio` documenta el punto de partida.

### Key Entities

- **Movimiento de caja**: Ingreso o egreso asociado a una caja. Atributos relevantes: descripción, monto, **moneda (ARS | USD)**, tipo (entrada/salida), subtotal resultante **en esa moneda**, fecha, caja, usuario. Opcionalmente forma parte de un par USD (principal + complementario) sin fusionarse en un único registro.
- **Moneda**: Catálogo cerrado de dos valores: ARS (peso argentino, predeterminado) y USD (dólar estadounidense). No hay otras monedas en esta feature.
- **Filtro de historial**: Criterios opcionales sobre una caja: rango de fechas del movimiento y/o moneda. No altera los datos, solo la vista paginada.
- **Saldo de caja por moneda**: Valor acumulado de la caja en ARS y valor acumulado de la misma caja en USD, independientes.

## Testing Strategy

- **Enfoque elegido**: `TDD`
- **Rationale**: Dominio financiero: subtotales por caja y moneda, par USD de tipos opuestos y filtros sobre historial. TDD reduce regresiones en integridad de saldos y en el alta doble.
- **Alcance**: Tests antes de implementar moneda en el movimiento, cálculo de subtotales por moneda, cartel USD (confirmar/rechazar), filtros de fecha y moneda, y visibilidad según rol. Tests de integración para subtotales y RBAC siguen siendo obligatorios (constitución).
- **Nota para downstream**: This decision MUST be honored by `/spec-kitti.plan` (test contracts) and `/spec-kitti.tasks` (TDD / unit-test tasks generated or omitted accordingly).

## Assumptions

- El movimiento complementario en USD usa el **mismo monto y la misma moneda USD** (no es un canje a pesos ni pide cotización). Confirmado en clarificación 2026-09-07.
- Confirmar el cartel crea **dos registros independientes** visibles en el listado (no un único asiento doble); rechazar crea uno solo. Los dos renglones pueden anularse en el saldo USD de esa caja. La persistencia del par confirmado es **atómica** (todo o nada). Confirmado en clarificación 2026-09-07.
- El valor de caja muestra **siempre** saldo ARS y saldo USD de la caja completa; los filtros solo afectan el listado paginado. Confirmado en clarificación 2026-09-07.
- El valor por defecto ARS aplica al formulario de alta, no a los filtros del listado (el listado puede mostrar todas las monedas hasta que se filtre).
- El filtro por fecha es un **rango inclusive** (desde/hasta), no un selector de un único día. Usa la fecha del movimiento en la zona horaria de presentación ya usada por el sistema (hora Argentina). Confirmado en clarificación 2026-09-07.
- Consulta de Caja replica visibilidad de moneda y filtros porque muestra el mismo historial; no se rediseña plazos fijos ni impresión en esta feature (si un comprobante de caja muestra montos, deberá al menos no ocultar la moneda; el rediseño de impresión queda fuera de alcance).
- Esta feature **replaza** la regla previa de “una sola moneda ARS” **solo para movimientos de caja**; la constitución actual aún menciona moneda única y deberá alinearse en planificación/enmienda.
- Los wireframes `actual.drawio` y `willing.drawio` son referencia de disposición del formulario; el listado, filtros y carteles se especifican aquí porque no están detallados en esos diagramas.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El 100% de los movimientos nuevos de caja queda etiquetado como ARS o USD; no queda ningún alta nueva sin moneda.
- **SC-002**: En ARS, una secretaria completa una entrada o salida sin carteles extra, en el mismo tiempo operativo habitual (menos de 30 segundos una vez elegida la caja).
- **SC-003**: En USD, el 100% de las pulsaciones de Entrada o Salida muestran el cartel correspondiente antes de persistir el par o el movimiento simple.
- **SC-004**: El 100% de las confirmaciones del cartel con guardado exitoso generan exactamente dos movimientos (tipos opuestos, mismo monto USD); el 100% de los rechazos genera exactamente uno; el 100% de los fallos de persistencia del par no deja movimientos parciales.
- **SC-005**: Un usuario encuentra movimientos de una moneda y un rango de fechas dados filtrando, sin revisar a mano páginas irrelevantes, en menos de 15 segundos una vez abierta la caja.
- **SC-006**: En el 100% de los casos de prueba, los subtotales y el valor de caja no mezclan ARS con USD.
- **SC-007**: Un escribano ve moneda y puede filtrar, y el 100% de sus intentos de escritura siguen rechazados.
- **SC-008**: Movimientos anteriores a la feature se muestran como ARS en el 100% de las muestras de migración/compatibilidad.
