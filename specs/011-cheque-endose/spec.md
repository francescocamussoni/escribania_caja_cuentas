# Feature Specification: Endose de cheques pendientes

**Feature Branch**: `011-cheque-endose`  
**Created**: 2026-11-04  
**Status**: Draft  
**Input**: User description: "Además del botón de Liquidar, los cheques pendientes deben tener otro botón de Endose, que puede usarse en cualquier momento (el botón Liquidar se habilita recién en la fecha de liquidación). El cheque se liquida en la caja correspondiente, pero al tocar el botón se muestra una ventana con las cajas desplegadas donde se permite seleccionar una; en la caja seleccionada aparece como salida (si el cheque fue de entrada) y como entrada si el cheque fue de salida."

**Depende de**: `specs/010-cheques-instrumento/spec.md` (ciclo de vida del cheque, estados Pendiente/Liquidado, botón Liquidar, sección Cheques, Saldo a futuro, informe de Caja).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Endosar un cheque pendiente a otra caja en cualquier momento (Priority: P1)

La secretaria tiene un cheque pendiente (cargado como Cheque o Echeque) y decide endosarlo, es decir, usarlo como medio de pago/traspaso hacia otra caja sin esperar a su fecha de liquidación. Pulsa el botón **Endose** del cheque, se abre una ventana con las cajas disponibles, selecciona la caja destino y confirma. El cheque queda liquidado en su caja de origen y en la caja destino se registra el movimiento inverso: **salida** si el cheque era de entrada, **entrada** si el cheque era de salida.

**Why this priority**: Es el núcleo del pedido; permite operar con el cheque antes de su fecha de liquidación.

**Independent Test**: Con un cheque pendiente de entrada de ARS 500 en la caja A (fecha de liquidación futura), pulsar **Endose**, elegir la caja B y confirmar; verificar que el cheque pasa a Liquidado en A (A +500), que en B aparece una salida de ARS 500 (B −500) y que el botón **Liquidar** había permanecido deshabilitado antes del endose.

**Acceptance Scenarios**:

1. **Given** un cheque pendiente (de cualquier fecha de liquidación, futura o vencida), **When** la secretaria visualiza el cheque, **Then** ve junto al botón **Liquidar** un botón **Endose** siempre habilitado.
2. **Given** un cheque pendiente cuya fecha de liquidación **aún no llegó**, **When** se visualiza, **Then** el botón **Liquidar** está deshabilitado y el botón **Endose** está habilitado.
3. **Given** un cheque pendiente cuya fecha de liquidación es **hoy o anterior**, **When** se visualiza, **Then** ambos botones (**Liquidar** y **Endose**) están habilitados.
4. **Given** la secretaria pulsa **Endose**, **When** se abre la ventana, **Then** se muestran desplegadas las cajas disponibles para seleccionar una, y la caja de origen del cheque no es seleccionable.
5. **Given** un cheque pendiente de **entrada** de monto M en la caja A, **When** la secretaria endosa seleccionando la caja B, **Then** el cheque pasa a **Liquidado** en A (fecha liquidado = momento del endose, impacto +M en A) y en B se registra una **salida** de monto M en la misma moneda (impacto −M en B).
6. **Given** un cheque pendiente de **salida** de monto M en la caja A, **When** la secretaria endosa seleccionando la caja B, **Then** el cheque pasa a **Liquidado** en A (impacto −M en A) y en B se registra una **entrada** de monto M en la misma moneda (impacto +M en B).
7. **Given** la ventana de endose abierta, **When** la secretaria no selecciona ninguna caja, **Then** no puede confirmar el endose.
8. **Given** la ventana de endose abierta, **When** la secretaria la cancela o la cierra, **Then** el cheque permanece pendiente y ningún saldo cambia.
9. **Given** un endose exitoso, **When** se visualizan ambas cajas, **Then** el cheque endosado figura en la lista cronológica de A como Liquidado con indicación de **Endosado** y la caja destino, y el movimiento de B indica que proviene de un endose y la caja origen.
10. **Given** un cheque ya liquidado o ya endosado, **When** se visualiza, **Then** no aparecen los botones **Liquidar** ni **Endose**.
11. **Given** un usuario con rol Escribano, **When** consulta un cheque pendiente, **Then** no ve ni puede ejecutar la acción **Endose**.

---

### User Story 2 - Endosar desde la sección Cheques (Priority: P2)

La secretaria también puede endosar un cheque desde la sección **Cheques**, tanto en **Aptos para liquidar** como en **Próximos a liquidar este mes**, con el mismo comportamiento que en la vista de registros de la caja.

**Why this priority**: La sección Cheques es el punto de gestión transversal de cheques; depende de que el endose exista (US1).

**Independent Test**: En la sección **Cheques**, pulsar **Endose** sobre un cheque de "Próximos a liquidar este mes", elegir una caja y confirmar; verificar que el cheque desaparece de la sección y los saldos de ambas cajas cambian como en US1.

**Acceptance Scenarios**:

1. **Given** la sección **Cheques**, **When** la secretaria la visualiza, **Then** cada cheque de ambos listados muestra los botones **Liquidar** (según su fecha) y **Endose** (siempre habilitado).
2. **Given** un cheque listado, **When** se endosa, **Then** se aplican los mismos efectos que desde la vista de registros y el cheque desaparece de la sección, actualizándose los listados.
3. **Given** un usuario con rol Escribano, **When** visualiza la sección, **Then** no ve el botón **Endose** (solo lectura).

---

### User Story 3 - Endose y Saldo a futuro / informes consistentes (Priority: P3)

Tras un endose, el cheque deja de figurar como pendiente en todas las vistas derivadas y los saldos reflejan los dos movimientos generados.

**Why this priority**: Garantiza consistencia con las vistas existentes de la feature de cheques; no bloquea el flujo principal.

**Independent Test**: Endosar un cheque pendiente y verificar que desaparece de **Saldo a futuro** de la caja origen, del informe de Caja (sección Cheques pendientes) y que aparece como movimientos liquidados en ambos informes.

**Acceptance Scenarios**:

1. **Given** un cheque endosado, **When** se expande **Saldo a futuro** de la caja origen, **Then** ese cheque ya no figura como proyección futura (su efecto pasó al saldo actual).
2. **Given** un cheque endosado, **When** se genera el informe de Caja de la caja origen o destino con un período que incluya el momento del endose, **Then** el movimiento aparece en el listado con su subtotal, y el cheque no figura en la sección **Cheques pendientes**.
3. **Given** un cheque endosado, **When** se calculan los saldos y el **Valor en conjunto** en Consulta, **Then** se consideran ambos movimientos (origen y destino) como movimientos que impactan el saldo.

---

### Edge Cases

- ¿Qué pasa si se pulsa **Endose** sobre un cheque ya liquidado o ya endosado (doble clic o desde dos pantallas)? → Solo la primera operación tiene efecto; la segunda se rechaza sin duplicar movimientos ni saldos.
- ¿Qué pasa si falla el endose? → Se muestra un mensaje de error genérico, el cheque permanece pendiente y no se crea ningún movimiento en la caja destino (la operación es atómica: o ocurren ambos efectos o ninguno).
- ¿Qué pasa si el cheque se **liquida** normalmente (botón Liquidar)? → No cambia: se liquida en su caja sin generar movimiento en ninguna otra caja.
- ¿Qué pasa si la caja destino está archivada? → No se ofrece como opción seleccionable.
- ¿Qué pasa con las monedas? → El movimiento de la caja destino se registra en la misma moneda y con el mismo monto que el cheque; cada caja maneja sus streams ARS/USD como hasta ahora.
- ¿Qué pasa si se intenta editar o eliminar el cheque endosado o el movimiento generado en la caja destino? → Se rechaza en ambos casos: son registros finales que solo existen como consecuencia del endose y no se modifican por separado.
- ¿Qué pasa con la fecha del endose? → Se usa el momento en que se confirma (zona horaria Argentina, UTC-3), tanto como fecha liquidado del cheque como fecha del movimiento en la caja destino.
- ¿Qué pasa con los cheques pendientes existentes antes de esta feature? → Pasan a mostrar el botón **Endose** sin ninguna migración de datos; no cambian de estado.

## Requirements *(mandatory)*

### Functional Requirements

**Botón Endose**

- **FR-001**: Cada cheque/echeque en estado **Pendiente** DEBE mostrar un botón **Endose** junto al botón **Liquidar**, en la vista de registros de su caja y en la sección **Cheques** (listados "Aptos para liquidar" y "Próximos a liquidar este mes"), visible y operable solo para el rol Secretaria.
- **FR-002**: El botón **Endose** DEBE estar habilitado en cualquier momento mientras el cheque esté pendiente, sin depender de su fecha de liquidación.
- **FR-003**: El botón **Liquidar** DEBE habilitarse únicamente cuando la fecha de liquidación del cheque es igual o anterior a la fecha actual (zona horaria Argentina); antes de esa fecha DEBE mostrarse deshabilitado. El servidor DEBE rechazar una liquidación solicitada antes de la fecha de liquidación.
- **FR-004**: Un cheque liquidado o endosado NO DEBE mostrar ni permitir las acciones **Liquidar** ni **Endose**.

**Ventana de selección de caja**

- **FR-005**: Al pulsar **Endose**, el sistema DEBE mostrar una ventana con las cajas disponibles desplegadas, donde se pueda seleccionar exactamente una caja destino y confirmar o cancelar.
- **FR-006**: La lista de cajas seleccionables DEBE excluir la caja de origen del cheque y las cajas archivadas.
- **FR-007**: El sistema NO DEBE permitir confirmar el endose sin una caja destino seleccionada. Cancelar o cerrar la ventana NO DEBE producir ningún cambio.

**Efecto del endose**

- **FR-008**: Al confirmar, el sistema DEBE, en una única operación atómica: (a) liquidar el cheque en su caja de origen, registrando la **Fecha liquidado** con el momento actual e incorporando su monto al subtotal de la caja y moneda de origen (entrada suma, salida resta, igual que la liquidación de la feature 010); y (b) registrar en la caja destino seleccionada un movimiento de la misma moneda y monto con **sentido inverso** al del cheque: **salida** si el cheque era de entrada, **entrada** si el cheque era de salida.
- **FR-009**: El movimiento generado en la caja destino DEBE impactar de inmediato en el subtotal de esa caja y moneda y ubicarse en su historial según el momento del endose.
- **FR-010**: El cheque endosado DEBE quedar con estado **Liquidado** y conservar la indicación de **Endosado**, la caja destino y el vínculo con el movimiento generado; el movimiento de la caja destino DEBE indicar que proviene de un endose y la caja y el cheque de origen. La descripción de ese movimiento se genera automáticamente (por ejemplo, "Endose cheque: <descripción> (Caja <origen>)") y el movimiento NO DEBE poder editarse ni eliminarse por separado (ni en la interfaz ni en el servidor).
- **FR-011**: Si cualquiera de los dos efectos falla, NO DEBE persistirse ninguno: el cheque permanece pendiente y los saldos no cambian.
- **FR-012**: El sistema DEBE impedir endosar un cheque que ya no esté pendiente (liquidado o endosado), sin duplicar movimientos ni impactos en saldo.
- **FR-013**: La liquidación normal (botón **Liquidar**) DEBE conservar su comportamiento actual y no generar movimientos en otras cajas.

**Vistas derivadas**

- **FR-014**: Tras el endose, el cheque DEBE desaparecer de los cheques pendientes de la caja de origen, de la sección **Cheques** y del **Saldo a futuro**, y pasar a la lista cronológica como Liquidado con la indicación **Endosado**.
- **FR-015**: Los informes de Caja y las vistas de Consulta (Valor de caja, Subtotal general, Valor en conjunto) DEBEN considerar ambos movimientos (cheque liquidado en origen y movimiento en destino) como movimientos que impactan el saldo, y el cheque endosado NO DEBE figurar en la sección **Cheques pendientes** de los informes.

**Permisos, seguridad y compatibilidad**

- **FR-016**: Solo el rol Secretaria PUEDE endosar cheques; el Escribano solo consulta. La autorización DEBE aplicarse en el servidor y rechazar con 403 los intentos no autorizados.
- **FR-017**: Cada endose DEBE registrar el usuario que lo realizó (auditoría mínima) y validar en el servidor que la caja destino exista, esté activa y sea distinta de la caja de origen.
- **FR-018**: Los cheques, movimientos y saldos existentes DEBEN conservar su comportamiento; esta feature no requiere modificar datos históricos.
- **FR-019**: Un cheque endosado NO DEBE poder editarse ni eliminarse (ni en la interfaz ni en el servidor, que DEBE rechazar el intento). Esto aplica también a su movimiento en la caja destino (FR-010); ambos registros son finales.

### Key Entities

- **Cheque / Echeque**: entidad de la feature 010. Se extiende con la posibilidad de resolverse por **endose** además de por liquidación: cuando se endosa conserva estado Liquidado y registra que fue endosado, hacia qué caja y el movimiento asociado.
- **Endose**: operación que liquida un cheque pendiente en su caja de origen y genera un movimiento inverso (misma moneda y monto) en una caja destino elegida por la secretaria; atributos de negocio: cheque, caja origen, caja destino, momento y usuario.
- **Movimiento de endose (caja destino)**: movimiento común (salida si el cheque era de entrada, entrada si era de salida) que impacta el subtotal de la caja destino y referencia el endose que lo originó.
- **Caja**: entidad existente; sus subtotales reflejan tanto el cheque liquidado/endosado (origen) como el movimiento de endose (destino).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: La secretaria puede endosar un cheque pendiente (pulsar Endose, elegir caja y confirmar) en menos de 15 segundos.
- **SC-002**: El 100% de los endoses actualizan el saldo de la caja origen por el monto del cheque (según su sentido) y el de la caja destino por el mismo monto en sentido inverso, en la misma moneda.
- **SC-003**: El 100% de los endoses fallidos o cancelados dejan el cheque pendiente y ambos saldos sin cambios.
- **SC-004**: El botón **Liquidar** permanece deshabilitado en el 100% de los cheques cuya fecha de liquidación es posterior a hoy, mientras que **Endose** está disponible en el 100% de los cheques pendientes.
- **SC-005**: Ningún cheque puede generar más de un endose ni ser liquidado y endosado a la vez (0 duplicados en saldos).
- **SC-006**: El 100% de los intentos de endose por un usuario Escribano son rechazados.
- **SC-007**: La liquidación normal de cheques no presenta regresiones: el 100% de los casos de la feature 010 mantienen su comportamiento.

## Testing Strategy

- **Enfoque elegido:** TDD — tests escritos antes de la implementación, consistente con la feature 010 (misma lógica de integridad financiera: impacto en subtotales por caja y moneda, atomicidad y RBAC).
- **Scope note:** Esta decisión DEBE ser respetada por `/spec-kitti.plan` y `/spec-kitti.tasks`. Los tests de integración de subtotales, atomicidad y RBAC son obligatorios según la constitución.

## Clarifications

### Session 2026-11-04

- Q: ¿Cuál es el efecto contable del endose? → A: La caja origen impacta como una liquidación normal (+M si entrada, −M si salida) y la caja destino recibe el movimiento inverso (−M / +M); el neto entre ambas cajas es 0 (FR-008).
- Q: ¿Cómo se describe y qué se puede hacer con el movimiento generado en la caja destino? → A: Descripción generada automáticamente; el movimiento destino no se puede editar ni eliminar por separado (FR-010).
- Q: ¿Se puede editar o eliminar el cheque ya endosado? → A: No; el cheque endosado es un registro final, igual que su movimiento destino (FR-019).

## Assumptions

- El movimiento en la caja destino es un movimiento común (sin instrumento), con la misma moneda y monto que el cheque, y una descripción que lo identifica como endose (referencia a la caja origen y a la descripción del cheque).
- El endose es total (por el monto completo del cheque), se hace a una única caja destino y no se admite endose parcial.
- La fecha del endose es el momento de la confirmación; no se permite elegir otra fecha.
- No se contempla "deshacer" ni corregir un endose en esta versión (FR-019).
- Las cajas seleccionables son todas las cajas activas distintas de la de origen; el listado es visible solo para la Secretaria, que es quien puede endosar.
- "Fecha actual" se evalúa en zona horaria Argentina (UTC-3), consistente con el resto del sistema.
- Las tareas de UI generadas en `/spec-kitti.tasks` requerirán la referencia de diseño (Figma) correspondiente según las reglas del proyecto; la ventana de selección de caja y los botones se extienden respecto a los wireframes `.drawio` vigentes y esta desviación deberá documentarse en el plan (Principio III de la constitución).
