# Phase 0 Research — Configuración y Archivo de Cajas

## Decision 1: Soft-delete mediante estado `archivada`

- **Decision**: Implementar archivo lógico con estado de caja (`activa`/`archivada`) en lugar de eliminación física.
- **Rationale**: Cumple el requisito de persistir información histórica y evita pérdida de trazabilidad financiera.
- **Alternatives considered**:
  - Eliminación física de cajas: descartada por riesgo de ruptura histórica.
  - Tabla separada de cajas archivadas: descartada por complejidad innecesaria para la escala actual.

## Decision 2: Filtrado por cajas activas en endpoints operativos

- **Decision**: Todos los listados/consultas usados por desplegables y boxes operativos devolverán únicamente cajas activas.
- **Rationale**: Garantiza cumplimiento consistente de FR-005 en toda la aplicación, sin depender de filtros de UI.
- **Alternatives considered**:
  - Filtrar solo en frontend: descartado por riesgo de inconsistencias y violación de backend autoritativo.
  - Mantener endpoint único y flag opcional de filtrado: viable, pero con riesgo de mal uso; se prefiere default seguro.

## Decision 3: RBAC estricto en backend para alta/archivo

- **Decision**: Limitar operaciones de configuración a rol `secretaria`, devolviendo rechazo explícito para otros roles.
- **Rationale**: Alinea con Constitución (Principio II y IV), reduce superficie de abuso y mantiene separación de responsabilidades.
- **Alternatives considered**:
  - Restricción solo por ocultamiento en UI: descartada por insegura.
  - Permitir también `admin` sin especificación explícita: descartada por no estar en alcance funcional.

## Decision 4: TDD-first para core de negocio y contratos

- **Decision**: Aplicar TDD como estrategia de implementación de esta feature.
- **Rationale**: Está explícitamente definido en `spec.md` y es apropiado para lógica de permisos/estado con impacto operativo.
- **Alternatives considered**:
  - Unit-tests posteriores: descartado por mayor riesgo de regresión.
  - Híbrido sin TDD estricto: descartado por decisión explícita del usuario en clarificación.

## Decision 5: Auditoría mínima de eventos de configuración

- **Decision**: Registrar usuario, fecha y resultado para cada alta/archivo de caja.
- **Rationale**: Soporta trazabilidad operativa y seguridad sin introducir requerimientos de observabilidad compleja.
- **Alternatives considered**:
  - Logging sin actor: descartado por insuficiente para auditoría.
  - Event sourcing completo: descartado por sobreingeniería para alcance actual.
