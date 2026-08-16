# Feature Specification: Adaptacion Responsive Mobile

**Feature Branch**: `007-responsive-mobile`  
**Created**: 2026-08-15  
**Status**: Draft  
**Input**: User description: "la pagina se ve muy bien en computadora pero no se adpata bien a dispositivos mobiles, hagmaos que se vea tal y como esta en pc pero que se vea bien tambien en mobil"

## Clarifications

### Session 2026-08-15

- Q: Alcance de pantallas a adaptar en movil → A: Todas las pantallas de la aplicacion (login, menu, registro, consulta, plazos fijos, impresion y configuracion).
- Q: Como se muestran las tablas en celular → A: En celular, cada fila se muestra como bloque apilado con los mismos campos y el mismo orden que en PC.
- Q: Do you want to apply TDD (Test-Driven Development) and/or strict Unit Tests for this feature? Options: (A) Yes — generate tasks with a TDD-first approach (tests authored before implementation), (B) No — prioritize delivery speed, no mandatory test tasks for this feature, (C) Hybrid — Unit Tests required for core logic only, no strict TDD. → A: Hybrid — Unit Tests required for core logic only, no strict TDD.
- Q: Navegacion en celular → A: En celular, el menu se compacta (boton o panel) y muestra las mismas opciones que en PC.
- Q: Textos largos (descripciones) → A: El texto largo se muestra completo, partiendo en varias lineas.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Operacion Completa en Movil (Priority: P1)

Como secretaria o escribano, quiero usar todas las pantallas de la aplicacion desde un celular sin perder informacion ni controles para poder operar (login, navegacion, registro, consulta, plazos fijos, impresion y configuracion) en cualquier momento.

**Why this priority**: Si la operacion principal no es usable en movil, el sistema pierde utilidad en situaciones reales fuera de escritorio.

**Independent Test**: Puede validarse recorriendo cada pantalla de la aplicacion desde un telefono y completando las tareas principales sin zoom horizontal ni elementos inaccesibles.

**Acceptance Scenarios**:

1. **Given** un usuario autenticado desde un celular, **When** abre la pantalla de Registro de Caja, **Then** puede seleccionar caja, escribir descripcion, cargar monto y accionar Entrada/Salida sin que se oculten controles.
2. **Given** un usuario autenticado desde un celular, **When** abre la pantalla de Consulta de Caja, **Then** visualiza y recorre el historial sin perdida de legibilidad ni superposicion de elementos.
3. **Given** un usuario en un celular, **When** recorre login, menu, plazos fijos, impresion y configuracion (segun su rol), **Then** cada pantalla es usable y muestra las mismas acciones disponibles en PC para ese rol.
4. **Given** un usuario autenticado en un celular, **When** abre el menu compacto, **Then** ve las mismas destinos de navegacion que en PC y puede cambiar de pantalla.

---

### User Story 2 - Consistencia Visual Entre Dispositivos (Priority: P2)

Como usuario habitual, quiero que la estructura visual en movil conserve el mismo orden y sentido que en PC para no reaprender el flujo de trabajo.

**Why this priority**: La consistencia reduce errores operativos y acelera la adopcion del sistema entre perfiles no tecnicos.

**Independent Test**: Puede probarse comparando la secuencia de secciones y controles en PC y en movil, verificando que ambas interfaces siguen la misma logica de uso.

**Acceptance Scenarios**:

1. **Given** la misma pantalla abierta en PC y movil, **When** el usuario revisa el flujo de arriba hacia abajo, **Then** encuentra los mismos bloques funcionales en orden equivalente.
2. **Given** el usuario cambia entre PC y movil durante una jornada, **When** retoma una tarea iniciada, **Then** completa la accion sin requerir instrucciones adicionales.

---

### User Story 3 - Lectura Clara de Datos Financieros (Priority: P3)

Como usuario de caja, quiero que montos, subtotales, fechas y descripciones sean faciles de leer en movil para evitar errores de interpretacion.

**Why this priority**: La legibilidad en datos financieros impacta directamente en la confianza y precision operativa.

**Independent Test**: Puede validarse mostrando listados largos en pantallas pequenas y confirmando que cada dato critico permanece visible y distinguible.

**Acceptance Scenarios**:

1. **Given** un historial con multiples movimientos, **When** el usuario lo visualiza desde un celular, **Then** identifica correctamente descripcion, monto, subtotal y fecha en cada registro, en el mismo orden de campos que en PC.
2. **Given** un listado tabular en PC, **When** el mismo listado se abre en celular, **Then** cada fila se presenta como un bloque apilado (no como tabla de columnas lado a lado) sin omitir campos.
3. **Given** un movimiento con descripcion extensa, **When** el usuario lo ve en celular, **Then** el texto se muestra completo en varias lineas.

---

### Edge Cases

- Que ocurre cuando la descripcion del movimiento es extensa y supera una linea en pantalla pequena: el texto se muestra completo, partiendo en varias lineas, sin recorte ni accion extra para leerlo.
- Como se comporta la interfaz cuando hay listados con muchas filas y el usuario necesita paginar desde movil: la paginacion permanece visible y cada fila se muestra como bloque apilado.
- Que ocurre cuando el dispositivo cambia de orientacion (vertical/horizontal) durante una carga o edicion: la pantalla se reacomoda y conserva el trabajo en curso sin perder datos ingresados.
- Como se muestran mensajes de validacion y error en formularios compactos: aparecen cerca del campo o accion afectada, sin tapar las acciones principales.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema MUST adaptar a movil todas las pantallas de la aplicacion (login, menu, registro, consulta, plazos fijos, impresion y configuracion) y permitir usar todas las acciones actualmente disponibles en PC, sin eliminar capacidades funcionales.
- **FR-002**: El sistema MUST mantener en movil la misma jerarquia de informacion y secuencia de pasos operativos definida para PC.
- **FR-003**: El sistema MUST presentar formularios y controles tactiles con tamano y separacion suficientes para evitar selecciones accidentales.
- **FR-004**: El sistema MUST asegurar que la informacion financiera critica (descripcion, monto, subtotal, fecha) sea legible en pantallas pequenas sin requerir zoom.
- **FR-005**: El sistema MUST evitar desbordes horizontales que oculten contenido o acciones principales en anchos de pantalla de smartphone comunes.
- **FR-010**: En dispositivos moviles, el sistema MUST presentar cada fila de un listado tabular como un bloque apilado que conserve los mismos campos y el mismo orden que las columnas de PC; no MUST recortar campos ni exigir desplazamiento horizontal de pagina para leerlos.
- **FR-006**: El sistema MUST conservar permisos y restricciones por rol (Secretaria/Escribano) de forma consistente en movil y PC.
- **FR-007**: El sistema MUST mantener disponibles las acciones de paginacion y navegacion de historiales en movil.
- **FR-008**: El sistema MUST mostrar estados de error, vacio y carga de forma entendible en pantallas pequenas.
- **FR-009**: El sistema MUST soportar uso en orientacion vertical y horizontal sin romper la experiencia principal.
- **FR-011**: En dispositivos moviles, el sistema MUST compactar la navegacion en un boton o panel que exponga las mismas opciones de menu que en PC, sin ocultar destinos segun el rol del usuario.
- **FR-012**: El sistema MUST mostrar textos largos (descripciones y equivalentes) completos en movil, partiendo en varias lineas; no MUST recortarlos ni exigir una accion extra para leerlos.

### Key Entities *(include if feature involves data)*

- **Vista de Pantalla**: Representa la presentacion de cada modulo (login, menu, registro, consulta, plazos fijos, impresion y configuracion) segun tipo de dispositivo y orientacion.
- **Bloque Funcional de Interfaz**: Representa grupos de controles e informacion (selector, formulario, acciones, historial, paginacion) que deben conservar orden y disponibilidad.
- **Elemento de Dato Financiero Visible**: Representa cada dato critico mostrado al usuario (descripcion, monto, subtotal, fecha) cuya legibilidad debe mantenerse.
- **Fila de Listado**: En PC es una fila de tabla; en movil es el mismo registro mostrado como bloque apilado con campos en el mismo orden.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Al menos 95% de usuarios internos completa una carga simple de movimiento desde celular en menos de 2 minutos durante pruebas de aceptacion.
- **SC-002**: Al menos 95% de usuarios internos completa una consulta de historial desde celular en menos de 90 segundos durante pruebas de aceptacion.
- **SC-003**: En pruebas funcionales sobre pantallas de smartphone comunes, 100% de las acciones principales de todas las pantallas (login, menu, registro, consulta, plazos fijos, impresion y configuracion) permanece accesible sin desplazamiento horizontal obligatorio.
- **SC-004**: En validacion comparativa PC vs movil, 100% de los bloques funcionales obligatorios de cada pantalla aparece en el mismo orden logico operativo.
- **SC-005**: Se reduce en al menos 70% la cantidad de reportes internos vinculados a problemas de visualizacion en movil durante el primer mes de uso posterior al despliegue.

## Testing Strategy

- Chosen approach: Hybrid (Unit Tests for core logic, no strict TDD)
- Rationale: La feature es de presentacion; no cambia reglas de caja ni permisos. Las pruebas unitarias cubren la logica de adaptacion de listados (campos y orden en bloques). El resto se valida con verificacion visual y aceptacion en dispositivo.
- Scope note: This decision MUST be honored by `/spec-kitti.plan` (test contracts) and `/spec-kitti.tasks` (TDD / unit-test tasks generated or omitted accordingly).

## Assumptions

- La funcionalidad de negocio actual no cambia; solo se mejora la adaptacion visual y de uso en movil.
- El alcance incluye todas las pantallas de la aplicacion: login, menu, registro, consulta, plazos fijos, impresion y configuracion.
- Los usuarios objetivo utilizan smartphones modernos con navegadores actualizados.
- No se introduce un nuevo flujo exclusivo para movil; se conserva un unico flujo funcional coherente entre dispositivos.
- En movil, los listados tabulares se reorganizan visualmente (bloque por fila) sin cambiar datos, filtros, paginacion ni acciones de cada registro.
- En movil, la navegacion se compacta; no se reducen las destinos disponibles respecto de PC para el mismo rol.
- Los textos largos se muestran completos con salto de linea; no se recortan.
