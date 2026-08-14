# Feature Specification: Configuracion de cajas archivables

**Feature Branch**: `006-config-archivo-cajas`  
**Created**: 2026-08-14  
**Status**: Draft  
**Input**: User description: "Quiero que exista una solapa de configuracion donde solo los usuarios tipo secretaria puedan agregar o archivar cajas. Las que se archivan siguen con su informacion persistida en la base de datos pero ya no quedan seleccionables en los desplegables o en los boxes."

## Clarifications

### Session 2026-08-14

- Q: Do you want to apply TDD (Test-Driven Development) and/or strict Unit Tests for this feature? Options: (A) Yes — generate tasks with a TDD-first approach (tests authored before implementation), (B) No — prioritize delivery speed, no mandatory test tasks for this feature, (C) Hybrid — Unit Tests required for core logic only, no strict TDD. → A: Yes — generate tasks with a TDD-first approach (tests authored before implementation).

## User Scenarios & Testing *(mandatory)*

<!--
  IMPORTANT: User stories should be PRIORITIZED as user journeys ordered by importance.
  Each user story/journey must be INDEPENDENTLY TESTABLE - meaning if you implement just ONE of them,
  you should still have a viable MVP (Minimum Viable Product) that delivers value.
  
  Assign priorities (P1, P2, P3, etc.) to each story, where P1 is the most critical.
  Think of each story as a standalone slice of functionality that can be:
  - Developed independently
  - Tested independently
  - Deployed independently
  - Demonstrated to users independently
-->

### User Story 1 - Gestion de cajas por secretaria (Priority: P1)

Como secretaria, quiero una solapa de configuracion para agregar cajas nuevas y archivar cajas existentes, asi puedo mantener actualizado el catalogo operativo sin depender de soporte tecnico.

**Why this priority**: Sin esta capacidad no se puede administrar el ciclo de vida de cajas desde el negocio, lo que bloquea la operacion diaria.

**Independent Test**: Puede probarse iniciando sesion como secretaria, agregando una caja y archivando otra, y verificando que ambas operaciones quedan registradas y reflejadas en la configuracion.

**Acceptance Scenarios**:

1. **Given** una usuaria con rol secretaria autenticada, **When** accede a la solapa de configuracion y completa los datos requeridos de una nueva caja, **Then** la caja se crea como activa y queda disponible para operar.
2. **Given** una caja activa existente, **When** la secretaria ejecuta la accion de archivar, **Then** la caja cambia a estado archivada sin perder su historial previo.

---

### User Story 2 - Exclusión de cajas archivadas en operación (Priority: P2)

Como usuaria operativa, quiero que las cajas archivadas no aparezcan en desplegables ni en boxes de trabajo, para evitar seleccionar cajas fuera de uso por error.

**Why this priority**: Evita errores operativos y mantiene la interfaz alineada con el catalogo vigente.

**Independent Test**: Puede probarse archivando una caja y luego revisando todos los puntos de seleccion de cajas para confirmar que solo aparecen cajas activas.

**Acceptance Scenarios**:

1. **Given** que una caja esta archivada, **When** cualquier usuario navega a pantallas con desplegables o boxes de cajas, **Then** esa caja no figura entre las opciones seleccionables.
2. **Given** que existen cajas activas y archivadas, **When** se visualizan listados operativos de seleccion, **Then** solo se muestran cajas activas.

---

### User Story 3 - Proteccion por rol en configuracion (Priority: P3)

Como escribano, quiero que la solapa de configuracion no me permita crear ni archivar cajas, para mantener la separacion de responsabilidades del sistema.

**Why this priority**: Refuerza las reglas de permisos y reduce riesgo de cambios no autorizados.

**Independent Test**: Puede probarse iniciando sesion como escribano e intentando acceder o ejecutar acciones de alta/archivo, verificando rechazo consistente.

**Acceptance Scenarios**:

1. **Given** un usuario con rol distinto de secretaria, **When** intenta crear o archivar una caja, **Then** el sistema rechaza la operacion por falta de permisos.

---

### Edge Cases

- Intento de crear una caja con un nombre ya existente (activo o archivado): el sistema debe evitar duplicados y mostrar un mensaje claro.
- Archivo de una caja que ya se encuentra archivada: la operacion debe ser idempotente y no generar inconsistencias.
- Solicitud concurrente de archivo sobre la misma caja por dos sesiones de secretaria: solo un cambio efectivo y resultado consistente para ambas sesiones.
- Existencia de movimientos historicos vinculados a una caja archivada: deben seguir siendo consultables en historial sin rehabilitar la caja para seleccion operativa.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE exponer una solapa de configuracion de cajas para usuarios autenticados con rol secretaria.
- **FR-002**: El sistema DEBE permitir que la secretaria agregue una nueva caja indicando los datos obligatorios definidos por negocio.
- **FR-003**: El sistema DEBE permitir que la secretaria archive una caja activa sin eliminar su informacion historica.
- **FR-003b**: El sistema DEBE permitir que la secretaria desarchive una caja archivada para que vuelva a estado activa y sea seleccionable en flujos operativos.
- **FR-004**: El sistema DEBE persistir el estado de cada caja (activa o archivada) de forma que sobreviva reinicios y despliegues.
- **FR-005**: El sistema DEBE excluir todas las cajas archivadas de los desplegables y boxes donde se seleccionan cajas para operar.
- **FR-006**: El sistema DEBE mantener visibles y consultables los datos historicos asociados a cajas archivadas.
- **FR-007**: El sistema DEBE impedir operaciones de alta, archivo y desarchivo a usuarios que no tengan rol secretaria.
- **FR-008**: El sistema DEBE registrar eventos de alta, archivo y desarchivo de cajas con usuario, fecha y resultado de la operacion para trazabilidad.
- **FR-009**: El sistema DEBE validar que no se creen cajas duplicadas segun la regla de unicidad de negocio.
- **FR-010**: El sistema DEBE devolver confirmaciones claras de exito o error para cada accion de configuracion.

### Key Entities *(include if feature involves data)*

- **Caja**: Unidad operativa seleccionable en registro y consulta; incluye identificador, nombre visible, estado (activa/archivada), fecha de alta y metadatos de auditoria.
- **Estado de Caja**: Condicion funcional de una caja para uso operativo; determina si puede ser seleccionada en UI operativa.
- **Evento de Configuracion de Caja**: Registro de acciones de crear o archivar caja con actor, marca temporal y resultado, usado para control y auditoria.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El 100% de las cajas archivadas dejan de aparecer como seleccionables en desplegables y boxes operativos inmediatamente despues de confirmar el archivo.
- **SC-002**: El 100% de las altas de cajas realizadas por secretarias autorizadas quedan disponibles para seleccion operativa en menos de 30 segundos.
- **SC-003**: El 100% de los intentos de crear o archivar cajas por usuarios no secretaria son rechazados.
- **SC-004**: Al menos el 95% de las secretarias completa la accion de agregar o archivar una caja en menos de 1 minuto durante pruebas de aceptacion.

## Testing Strategy

- Chosen approach: TDD
- Rationale: La feature afecta control de acceso y consistencia operativa sobre entidades de caja, por lo que conviene fijar expectativas de comportamiento antes de implementar para minimizar regresiones.
- Scope note: This decision MUST be honored by `/spec-kitti.plan` (test contracts) and `/spec-kitti.tasks` (TDD / unit-test tasks generated or omitted accordingly).

## Assumptions

- El modelo de roles actual ya distingue de forma confiable entre secretaria y escribano.
- Existe un atributo o mecanismo equivalente para determinar si una caja esta activa o archivada.
- "Desplegables o boxes" refiere a todos los controles de seleccion de cajas dentro de las pantallas operativas actuales.
