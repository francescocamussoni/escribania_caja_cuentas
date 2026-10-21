# Specification Quality Checklist: Instrumento Cheque/Echeque, Sección Cheques y Saldo a Futuro

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-10-21
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Notes

- Validación realizada en 1 iteración; todos los ítems pasan.
- Decisiones tomadas por defecto (documentadas en *Assumptions*), a confirmar en `/spec-kitti.clarify` si se desea otro comportamiento:
  - "Entrada y Salida" no disponible para cheques.
  - Al liquidar, el cheque impacta el subtotal con la fecha liquidado (momento de pulsar **Liquidar**) y no se puede deshacer.
  - ~~La sección **Cheques** es solo lectura~~ → Resuelto en clarify: la sección es visible para ambos roles y **Liquidar** está disponible también ahí (solo Secretaria).
  - Los cheques vencidos sin liquidar se mantienen en el **Saldo a futuro**, marcados como vencidos.
  - La **Fecha (opcional)** del formulario se usa como fecha de carga del cheque.
- Resuelto en clarify (sesión 2): el instrumento solo cambia entre Cheque y Echeque; el informe de Impresión (Caja) incluye la sección "Cheques pendientes" y el Saldo a futuro (US6, FR-031 a FR-033).
- Las referencias a "servidor" / 403 provienen de la constitución del proyecto (Principios II, IV y V), no son decisiones de implementación nuevas.
