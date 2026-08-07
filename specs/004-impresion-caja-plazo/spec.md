# Feature Specification: Impresión de Caja y Plazos Fijos

**Feature Branch**: `004-impresion-caja-plazo`  
**Created**: 2026-08-06  
**Status**: Draft  
**Input**: User description: "Agregar sección de impresión para caja y plazo fijo. En dicha sección se debe poder seleccionar si se imprimirá una caja o un plazo fijo y elegir una de todas las opciones disponibles (Ebel, Martin, Etc) además de una temporalidad para imprimir: Selección por mes y año (todos los registros / plazos fijos que se registraron en ese mes y año); Selección por periodo específico (fecha inicio y fecha finalización). La información a imprimir debe ser la misma que se refleja cuando se hace la consulta. Se debe generar un archivo PDF para imprimir con letra legible y típica de un documento formal."

## Clarifications

### Session 2026-08-06

- Q: ¿Qué valor de caja debe mostrar el PDF filtrado por período? → A: **Ambos** — saldo al cierre del período impreso y saldo actual vigente (como Consulta de Caja).
- Q: ¿Cómo calcular los totales del resumen en PDF de Plazos Fijos con filtro temporal? → A: **Solo del período filtrado** — totales sobre plazos no vencidos creados en el rango seleccionado.
- Q: ¿Cómo distinguir ingresos y egresos en el PDF de Caja? → A: **Etiquetas o signos** — indicar Entrada/Salida o usar +/− junto al monto (legible en impresión B/N).
- Q: ¿Cómo debe nombrarse el archivo PDF generado? → A: Formato **`<TIPO>-<NOMBRE_CAJA>-<PERIODO>`** — ver FR-021a (`YYYY-MM` mes único; `YYYY-MM-01_YYYY-MM-DD` mes + hasta hoy; `YYYY-MM-DD_YYYY-MM-DD` período).
- Q: ¿Qué debe mostrar el encabezado visible dentro del cuerpo del PDF? → A: **Encabezado operativo** — tipo de informe, nombre de caja, período y fecha/hora de generación.

### Session 2026-08-06 (amend)

- Q: ¿Debe existir opción "hasta hoy" al elegir período? → A: **Sí** — en modo mes/año y en período específico; el rango va desde el mes o fecha de inicio elegido **hasta la fecha de hoy** (calendario AR). Ej.: abril + hasta hoy con hoy 17/jul → abril, mayo y junio completos + del 1 al 17 de julio inclusive.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Imprimir Informe de Caja (Priority: P1)

Como secretaria o escribano de la escribanía, necesito generar un documento PDF con el
historial de movimientos de una caja filtrado por un período de tiempo, para archivar o
entregar un informe formal sin depender de capturas de pantalla.

**Why this priority**: Es el flujo principal de impresión y reutiliza los datos ya
existentes de Consulta de Caja. Entrega valor inmediato para reportes mensuales o por
rango de fechas.

**Independent Test**: Puede probarse con un usuario autenticado (Secretaria o
Escribano): acceder a Impresión, elegir tipo **Caja**, seleccionar una caja del
catálogo, definir mes/año o período específico, generar PDF y verificar columnas
Descripción, Monto, Subtotal y Fecha más el indicador de valor de caja, con los mismos
valores que la consulta para los registros del período.

**Acceptance Scenarios**:

1. **Given** un usuario autenticado con rol Secretaria o Escribano en la sección
   Impresión,
   **When** selecciona tipo **Caja**, la caja "Ebel", modo **Mes y año** (marzo 2026)
   y confirma la generación,
   **Then** obtiene un PDF que lista todos los movimientos de esa caja cuya **fecha del
   movimiento** cae en marzo 2026, con las columnas Descripción, Monto, Subtotal y
   Fecha, en el mismo orden que Consulta de Caja (más reciente primero).
2. **Given** un usuario en Impresión con tipo **Caja** y caja "Martin",
   **When** selecciona modo **Período específico** con fecha inicio 2026-01-15 y fecha
   fin 2026-02-28 y genera el informe,
   **Then** el PDF incluye únicamente movimientos con fecha del movimiento entre ambas
   fechas inclusive.
3. **Given** un PDF generado para una caja con movimientos en el período,
   **When** el usuario compara fila por fila con Consulta de Caja,
   **Then** cada registro impreso coincide en descripción, monto, subtotal y fecha con
   el mismo registro en consulta.
4. **Given** un PDF de caja con al menos un movimiento en el período,
   **When** el usuario revisa el encabezado del informe,
   **Then** ve el nombre de la caja, el período aplicado, la fecha de generación del
   documento, el **saldo al cierre del período impreso** (subtotal del último movimiento
   incluido en el filtro) y el **saldo actual** de la caja (mismo valor que el banner
   Valor de caja en Consulta de Caja al momento de generar el informe).
5. **Given** un usuario en Impresión,
   **When** intenta generar sin seleccionar caja o sin completar la temporalidad,
   **Then** el sistema rechaza la acción con mensaje claro y no produce archivo.
6. **Given** un usuario en Impresión con tipo **Caja**, modo **Mes y año** (abril 2026)
   y opción **Hasta hoy** activada, siendo hoy 17 de julio de 2026,
   **When** genera el informe,
   **Then** el PDF incluye movimientos desde el 1 de abril de 2026 hasta el 17 de julio
   de 2026 inclusive (abril, mayo y junio completos más julio hasta hoy).
7. **Given** un usuario en Impresión con modo **Período específico**, fecha inicio
   2026-04-01 y opción **Hasta hoy** activada, siendo hoy 17 de julio de 2026,
   **When** genera el informe,
   **Then** el PDF incluye registros del 1 de abril al 17 de julio de 2026 inclusive
   (mismo alcance que el escenario anterior).

---

### User Story 2 - Imprimir Informe de Plazos Fijos (Priority: P2)

Como secretaria o escribano de la escribanía, necesito generar un PDF con los plazos
fijos de una caja filtrados por período, para documentar inversiones a plazo fijo con el
mismo detalle que la consulta en pantalla.

**Why this priority**: Complementa la impresión de caja con el segundo dominio de datos
(plazos fijos). Depende de la misma pantalla de Impresión pero es independiente en su
flujo de validación y contenido del PDF.

**Independent Test**: Puede probarse eligiendo tipo **Plazo fijo**, una caja, un
período con plazos registrados, generando PDF y verificando panel de resumen (dos
totales de plazos activos) y tabla con Monto ingresado, Fecha de vencimiento y Monto a
vencimiento, con la misma regla de orden que Consulta Plazos Fijos.

**Acceptance Scenarios**:

1. **Given** un usuario autenticado en Impresión,
   **When** selecciona tipo **Plazo fijo**, la caja "Gabriel", modo **Mes y año**
   (agosto 2026) y genera el informe,
   **Then** el PDF lista todos los plazos fijos de esa caja cuya **fecha de creación**
   cae en agosto 2026.
2. **Given** un usuario en Impresión con tipo **Plazo fijo**,
   **When** define un período específico con fecha inicio y fecha fin válidas,
   **Then** el PDF incluye solo plazos fijos creados en ese rango inclusive.
3. **Given** un PDF de plazos fijos con plazos activos (vencimiento futuro) en el
   conjunto filtrado,
   **When** el usuario revisa el panel de resumen,
   **Then** ve los dos totales — dinero ingresado en plazos activos y dinero a cobrar
   al vencer — calculados **únicamente** sobre plazos no vencidos **creados dentro del
   rango temporal del informe** (no incluye plazos activos de la caja fuera del filtro),
   con los mismos valores que obtendría sumando manualmente esos plazos de la tabla
   impresa.
4. **Given** un PDF de plazos fijos,
   **When** el usuario revisa la tabla,
   **Then** las columnas son Monto ingresado, Fecha de vencimiento y Monto a
   vencimiento, ordenadas como en Consulta Plazos Fijos: vencimientos futuros primero
   (más próximo primero), vencidos al final (más recientemente vencidos primero).
5. **Given** un usuario con rol Escribano,
   **When** genera un informe de plazos fijos,
   **Then** el sistema permite la operación (solo lectura de datos; sin modificar
   registros).
6. **Given** un usuario en Impresión con tipo **Plazo fijo**, modo **Mes y año**
   (abril 2026) y **Hasta hoy** activado (hoy 17/jul/2026),
   **When** genera el informe,
   **Then** el PDF lista plazos creados entre el 1/abr/2026 y el 17/jul/2026 inclusive.

---

### User Story 3 - Documento PDF Formal y Descargable (Priority: P3)

Como usuario de la escribanía, necesito que el informe generado sea un PDF legible y
con aspecto de documento formal, listo para imprimir o archivar.

**Why this priority**: La calidad del documento es requisito explícito del negocio;
sin un PDF usable el resto de la funcionalidad no cumple el objetivo de impresión.

**Independent Test**: Generar cualquier informe válido y verificar formato PDF,
tipografía legible, encabezado identificativo y que el archivo se descarga o abre para
impresión sin pasos adicionales.

**Acceptance Scenarios**:

1. **Given** un informe generado correctamente,
   **When** el usuario abre el archivo,
   **Then** recibe un documento PDF (no otro formato) con texto en tipografía formal
   legible y tamaño adecuado para impresión en papel A4.
2. **Given** un informe con muchos registros en el período,
   **When** se genera el PDF,
   **Then** todos los registros del período aparecen en el documento (sin paginación
   de pantalla de 20 en 20); el PDF puede ocupar varias páginas si es necesario.
3. **Given** un informe generado,
   **When** el usuario lo imprime en impresora estándar,
   **Then** tablas y montos permanecen legibles sin zoom manual.

---

### Edge Cases

- ¿Qué ocurre si no hay registros en el período seleccionado? El sistema genera un PDF
  con encabezado (tipo, caja, período, fecha de generación) y mensaje explícito de que
  no hay registros en ese período; no debe fallar ni mostrar tabla vacía sin contexto.
- ¿Qué ocurre si fecha inicio es posterior a fecha fin en período específico? El
  sistema rechaza la generación con mensaje claro.
- ¿Qué ocurre si solo se completa mes sin año o viceversa? El sistema rechaza hasta que
  ambos estén definidos en modo mes/año.
- ¿Qué ocurre si el usuario cambia de tipo Caja a Plazo fijo? Los controles de
  temporalidad se mantienen; la caja seleccionada se conserva si ya estaba elegida.
- ¿Qué ocurre con movimientos en el límite del período (primer o último día)? Se
  incluyen si la fecha del movimiento (caja) o fecha de creación (plazo fijo) cae
  dentro del rango inclusive.
- ¿Qué ocurre si un visitante no autenticado accede a Impresión? Redirección a login;
  no se generan informes.
- ¿Qué ocurre con montos negativos de subtotal en caja? Se imprimen tal como en
  consulta, sin alteración.
- ¿Cómo se distinguen ingresos y egresos en el PDF? Mediante etiqueta Entrada/Salida
  o signo +/− en cada fila; no se requiere color verde/rojo (optimizado para
  impresión en blanco y negro).
- ¿Qué ocurre con **Hasta hoy** en mes/año sin activar? El filtro sigue siendo **solo
  ese mes** (del día 1 al último día del mes seleccionado).
- ¿Qué ocurre si se activa **Hasta hoy** y el mes/año o fecha de inicio es posterior a
  hoy? El sistema rechaza la generación con mensaje claro.
- ¿Qué ocurre con **Hasta hoy** en período específico? `fecha_fin` se fija automáticamente
  a hoy (AR); el usuario solo elige `fecha_inicio` (no debe ingresar fecha fin).

## Requirements *(mandatory)*

### Functional Requirements

**Sección Impresión (acceso y pantalla)**

- **FR-001**: El sistema DEBE ofrecer una sección **Impresión** accesible desde la
  navegación principal para usuarios con rol **Secretaria** y **Escribano**.
- **FR-002**: Visitantes no autenticados NO DEBEN acceder a Impresión ni generar
  informes.
- **FR-003**: La pantalla DEBE permitir elegir el **tipo de informe**: **Caja** o
  **Plazo fijo** (selección mutuamente excluyente).
- **FR-004**: La pantalla DEBE incluir un selector de **caja** con las **15 cajas**
  del catálogo existente (Bambina, Ebel, Martin, Gimnasio, Gabriel, Costanza, Guille,
  Intimayu, Amelia, Entre Rios, Chovet, Maria Teresa, Barat Hermanos, General Lagos,
  Fideicomiso).
- **FR-005**: La pantalla DEBE ofrecer dos modos de **temporalidad** (selección
  mutuamente excluyente):
  - **Mes y año**: selector de mes y año calendario.
  - **Período específico**: fecha de inicio y fecha de finalización (salvo con
    **Hasta hoy** — ver FR-005a).
- **FR-005a**: En **ambos** modos de temporalidad, la pantalla DEBE ofrecer una opción
  **Hasta hoy** (checkbox o equivalente). Si está activa:
  - **Mes y año**: el rango es desde el **primer día** del mes/año seleccionado hasta
    **hoy** (fecha calendario Argentina inclusive).
  - **Período específico**: el rango es desde `fecha_inicio` hasta **hoy** inclusive;
    `fecha_fin` no se solicita al usuario (el sistema la fija a hoy).
  Si **Hasta hoy** no está activa, el comportamiento previo se mantiene (mes único o
  rango explícito inicio–fin).
- **FR-006**: La pantalla DEBE incluir una acción explícita para **generar** o
  **imprimir** el informe (equivalente a disparar la creación del PDF).
- **FR-007**: La estética y disposición de la pantalla DEBEN ser consistentes con
  Consulta de Caja y Consulta Plazos Fijos (misma familia visual del producto).

**Filtros temporales**

- **FR-008**: En modo **Mes y año** **sin** **Hasta hoy**, para informes de **Caja**,
  el sistema DEBE incluir movimientos cuya **fecha del movimiento** pertenezca a ese
  mes y año calendario (zona horaria Argentina).
- **FR-008a**: En modo **Mes y año** **con** **Hasta hoy**, para informes de **Caja**,
  el sistema DEBE incluir movimientos con fecha del movimiento **≥ primer día del
  mes/año seleccionado** y **≤ hoy** (AR, inclusive). Ej.: abril 2026 + hasta hoy
  17/jul/2026 → 1/abr/2026–17/jul/2026.
- **FR-009**: En modo **Mes y año** **sin** **Hasta hoy**, para informes de **Plazo
  fijo**, el sistema DEBE incluir plazos cuya **fecha de creación** pertenezca a ese
  mes y año calendario.
- **FR-009a**: En modo **Mes y año** **con** **Hasta hoy**, para **Plazo fijo**, el
  sistema DEBE aplicar el mismo rango que FR-008a sobre `created_at`.
- **FR-010**: En modo **Período específico** **sin** **Hasta hoy**, para **Caja**, el
  sistema DEBE incluir movimientos con fecha del movimiento **≥ fecha inicio** y
  **≤ fecha fin** (ambas inclusive).
- **FR-010a**: En modo **Período específico** **con** **Hasta hoy**, para **Caja**, el
  sistema DEBE incluir movimientos con fecha **≥ fecha_inicio** y **≤ hoy** (AR,
  inclusive).
- **FR-011**: En modo **Período específico** **sin** **Hasta hoy**, para **Plazo
  fijo**, el sistema DEBE incluir plazos cuya fecha de creación esté en el rango
  inclusive.
- **FR-011a**: En modo **Período específico** **con** **Hasta hoy**, para **Plazo
  fijo**, el sistema DEBE aplicar el mismo rango que FR-010a sobre `created_at`.
- **FR-012**: El sistema DEBE validar que fecha inicio no sea posterior a fecha fin
  (modo período sin **Hasta hoy**); si **Hasta hoy** está activo, que inicio (o
  primer día del mes/año) no sea posterior a hoy; en caso contrario, rechazar con
  mensaje claro.
- **FR-013**: En modo mes/año, mes y año son obligatorios antes de generar. En modo
  período sin **Hasta hoy**, `fecha_inicio` y `fecha_fin` son obligatorios. En modo
  período con **Hasta hoy**, solo `fecha_inicio` es obligatorio.

**Contenido del informe — paridad con Consulta de Caja**

- **FR-014**: El PDF de **Caja** DEBE mostrar las mismas columnas que Consulta de
  Caja: **Descripción**, **Monto**, **Subtotal** y **Fecha**.
- **FR-014a**: Cada movimiento en el PDF de caja DEBE indicar explícitamente si es
  **Entrada** o **Salida** mediante etiqueta textual o signo (+/−) junto al monto,
  de forma legible en impresión monocroma (sin depender de color verde/rojo).
- **FR-015**: El orden de filas en el PDF de caja DEBE coincidir con Consulta de Caja:
  cronológico descendente por fecha del movimiento (más reciente primero).
- **FR-016**: El PDF de caja DEBE incluir **dos indicadores de saldo** claramente
  diferenciados: (1) **Saldo al cierre del período** — subtotal del último movimiento
  incluido en el filtro temporal; (2) **Saldo actual** — valor vigente de la caja al
  momento de generar el informe (paridad con el banner Valor de caja en Consulta de
  Caja). Si no hay movimientos en el período, el saldo al cierre del período no se
  muestra con valor numérico engañoso; el saldo actual sí se muestra si la caja tiene
  historial.
- **FR-017**: Los montos y subtotales impresos DEBEN coincidir con los almacenados en
  el sistema para cada movimiento (misma fuente de verdad que consulta).

**Contenido del informe — paridad con Consulta Plazos Fijos**

- **FR-018**: El PDF de **Plazo fijo** DEBE mostrar las mismas columnas que Consulta
  Plazos Fijos: **Monto ingresado**, **Fecha de vencimiento** y **Monto a
  vencimiento**.
- **FR-019**: El PDF DEBE incluir el panel de resumen con **dos totales** calculados
  **solo** sobre plazos **no vencidos creados dentro del rango temporal del informe**
  (período filtrado): (1) dinero ingresado en plazos activos del período; (2) dinero a
  cobrar al vencer esos plazos activos del período. Los plazos vencidos no participan
  en esos totales. Los plazos activos de la caja **fuera del filtro temporal** NO se
  incluyen en el resumen.
- **FR-020**: El orden de filas en el PDF de plazos fijos DEBE seguir Consulta Plazos
  Fijos: vencimientos futuros primero (ascendente, más próximo primero); vencidos al
  final (descendente por vencimiento, más recientemente vencidos primero).

**Formato PDF y entrega**

- **FR-021**: El sistema DEBE entregar el resultado como archivo **PDF** descargable
  o abrible en el navegador.
- **FR-021a**: El nombre del archivo PDF DEBE seguir el patrón
  **`<TIPO>-<NOMBRE_CAJA>-<PERIODO>.pdf`**, donde:
  - `TIPO` = `CAJA` o `PLAZO_FIJO` según el informe elegido;
  - `NOMBRE_CAJA` = nombre de la caja del catálogo, normalizado para nombre de archivo
    (espacios reemplazados por guión, sin caracteres inválidos);
  - `PERIODO` según modo resuelto:
    - Mes/año **sin** hasta hoy: `YYYY-MM`
    - Mes/año **con** hasta hoy: `YYYY-MM-01_YYYY-MM-DD` (inicio mes → hoy)
    - Período (con o sin hasta hoy): `YYYY-MM-DD_YYYY-MM-DD` (rango efectivo inclusive)
  Ejemplos: `CAJA-Ebel-2026-03.pdf`, `CAJA-Ebel-2026-04-01_2026-07-17.pdf`,
  `PLAZO_FIJO-Gabriel-2026-01-15_2026-02-28.pdf`.
- **FR-022**: El PDF DEBE usar tipografía formal legible (estilo documento
  administrativo), tamaño de cuerpo adecuado para lectura e impresión en A4, y un
  **encabezado operativo** visible con: tipo de informe (Caja / Plazo fijo), nombre de
  caja, período aplicado y fecha/hora de generación. No se requiere texto institucional
  adicional (ej. razón social) en v1.
- **FR-023**: El PDF DEBE listar **todos** los registros del período en un solo
  documento (varias páginas si hace falta), sin límite artificial de 20 registros por
  archivo.
- **FR-024**: La generación de informes es **solo lectura**; no debe crear, editar ni
  eliminar movimientos ni plazos fijos.

**Seguridad y permisos**

- **FR-025**: La validación de roles y autenticación DEBE aplicarse en el servidor al
  generar informes; el frontend solo refleja permisos.
- **FR-026**: Secretaria y Escribano DEBEN poder generar informes de **cualquiera** de
  las 15 cajas (sin restricción por caja asignada al usuario).
- **FR-027**: El rol Escribano NO DEBE obtener capacidades de escritura adicionales
  por usar Impresión.

### Key Entities

- **Solicitud de impresión**: Parámetros elegidos por el usuario: tipo (caja | plazo
  fijo), caja, modo temporal (mes/año | período específico), flag **hasta_hoy**
  (opcional, default false), y valores de filtro correspondientes.
- **Informe PDF**: Documento generado a partir de la solicitud; no se persiste como
  entidad de negocio obligatoria (descarga bajo demanda).
- **Movimiento / Plazo fijo / Caja**: Reutilizan las entidades y reglas de las features
  001-registro-cajas y 003-plazos-fijos.

## Testing Strategy

- **Enfoque elegido**: `TDD` — tests escritos antes de la implementación, alineado con
  las features 001 y 003 y la constitución del proyecto.
- **Rationale**: Los informes deben coincidir con consulta; TDD reduce regresiones en
  filtros temporales, totales y RBAC.
- **Alcance**: Tests de filtrado por mes/año y por rango (incl. **hasta hoy**),
  paridad de columnas y orden con consulta, cálculo de totales de plazos activos,
  PDF vacío con mensaje, rechazo de fechas inválidas, y acceso denegado sin
  autenticación o rol no permitido.

## Assumptions

- Requiere que existan las funcionalidades de Consulta de Caja y Consulta Plazos Fijos
  (features 001 y 003).
- Filtro por **fecha del movimiento** para caja y por **fecha de creación** para plazo
  fijo, según el pedido de “registros que se registraron en ese mes y año”.
- Zona horaria para límites de mes y día: **Argentina** (consistente con presentación
  de fechas en el producto).
- Moneda ARS; formato de montos con hasta 2 decimales, igual que consulta.
- No se almacena historial de PDFs generados en v1; cada generación es bajo demanda.
- No se requiere impresión directa a impresora del sistema operativo; basta entrega
  PDF para que el usuario imprima desde el visor o descarga.
- El nombre del archivo sigue `<TIPO>-<NOMBRE_CAJA>-<PERIODO>.pdf` (ver FR-021a).
- Sesión autenticada: 8 horas desde login (feature 001).
- No se requieren wireframes nuevos; paridad visual con pantallas de consulta existentes.
- El PDF de caja muestra **ambos saldos**: saldo al cierre del período impreso y saldo
  actual vigente (como Consulta de Caja). Pueden diferir si hay movimientos fuera del
  período seleccionado.
- **Hasta hoy** usa `today_ar()` del servidor al momento de generar; no es una fecha
  fija en el cliente.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Un usuario (Secretaria o Escribano) puede generar un PDF de caja con mes/año
  o período específico en menos de 30 segundos desde que completa los campos obligatorios.
- **SC-002**: El 100% de las filas impresas en informes de caja coinciden con los mismos
  registros visibles en Consulta de Caja para esa caja y fechas de movimiento.
- **SC-003**: El 100% de las filas impresas en informes de plazo fijo coinciden con los
  registros de Consulta Plazos Fijos para esa caja y fechas de creación en el período.
- **SC-004**: Los dos totales del resumen en PDF de plazos fijos coinciden con el cálculo
  manual sobre plazos no vencidos **del período filtrado** en el 100% de casos de prueba.
- **SC-005**: El 100% de solicitudes con fecha inicio posterior a fecha fin o temporalidad
  incompleta son rechazadas sin generar archivo.
- **SC-006**: Informes sin registros en el período producen PDF válido con mensaje claro
  en el 100% de casos de prueba (sin error del sistema).
- **SC-007**: Usuarios no autenticados no obtienen PDF en el 100% de intentos de acceso
  directo a generación.
- **SC-008**: En revisión con usuarios, al menos el 90% califica el PDF como legible y
  apropiado para un documento formal sin ajustes manuales de formato.
- **SC-009**: Con **Hasta hoy** activo (mes abril, hoy 17/jul), el 100% de registros
  impresos caen en el rango 1/abr–17/jul inclusive y ningún registro de agosto o
  posterior aparece en el informe.
