# Implementation Plan: [FEATURE]

**Branch**: `[###-feature-name]` | **Date**: [DATE] | **Spec**: [link]
**Input**: Feature specification from `/specs/[###-feature-name]/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

[Extract from feature spec: primary requirement + technical approach from research]

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: [e.g., Python 3.11, Swift 5.9, Rust 1.75 or NEEDS CLARIFICATION]  
**Primary Dependencies**: [e.g., FastAPI, UIKit, LLVM or NEEDS CLARIFICATION]  
**Storage**: [if applicable, e.g., PostgreSQL, CoreData, files or N/A]  
**Testing**: [e.g., pytest, XCTest, cargo test or NEEDS CLARIFICATION]  
**Target Platform**: [e.g., Linux server, iOS 15+, WASM or NEEDS CLARIFICATION]
**Project Type**: [single/web/mobile - determines source structure]  
**Performance Goals**: [domain-specific, e.g., 1000 req/s, 10k lines/sec, 60 fps or NEEDS CLARIFICATION]  
**Constraints**: [domain-specific, e.g., <200ms p95, <100MB memory, offline-capable or NEEDS CLARIFICATION]  
**Scale/Scope**: [domain-specific, e.g., 10k users, 1M LOC, 50 screens or NEEDS CLARIFICATION]

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

[Gates determined based on constitution file]

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)
<!--
  ACTION REQUIRED: Replace the placeholder tree below with the concrete layout
  for this feature. Delete unused options and expand the chosen structure with
  real paths (e.g., apps/admin, packages/something). The delivered plan must
  not include Option labels.
-->

```text
# [REMOVE IF UNUSED] Option 1: Single project (DEFAULT)
src/
├── models/
├── services/
├── cli/
└── lib/

tests/
├── contract/
├── integration/
└── unit/

# [REMOVE IF UNUSED] Option 2: Web application (when "frontend" + "backend" detected)
backend/
├── src/
│   ├── models/
│   ├── services/
│   └── api/
└── tests/

frontend/
├── src/
│   ├── components/
│   ├── pages/
│   └── services/
└── tests/

# [REMOVE IF UNUSED] Option 3: Mobile + API (when "iOS/Android" detected)
api/
└── [same as backend above]

ios/ or android/
└── [platform-specific structure: feature modules, UI flows, platform tests]
```

**Structure Decision**: [Document the selected structure and reference the real
directories captured above]

## Plan Jerárquico (para Itti-Kit)

<!--
  🤖 ITTI-KIT INTEGRATION
  
  Esta sección es CRÍTICA para que Itti-Kit pueda generar Work Units estructuradas.
  Si usas el comando /tasks.shape, esta sección debe estar completa y bien estructurada.
  
  ESTRUCTURA REQUERIDA:
  - Agrupa tareas por funcionalidad completa (no tareas atómicas)
  - Cada grupo debe ser testeable independientemente
  - Identifica pruebas legacy relevantes
  - Especifica entidades/archivos afectados
  - Define criterio de éxito claro
-->

### Work Unit 1: [Nombre Descriptivo de Alto Nivel]

**Propósito**: [Qué hace esta unidad completa - una frase]

**Entidades afectadas**: 
- [Entity1] (legacy: tabla/clase original)
- [Entity2] (legacy: tabla/clase original)

**Archivos a crear/modificar**:
- `src/path/file1.py` - [propósito]
- `src/path/file2.py` - [propósito]
- `tests/test_file1.py` - [qué valida]

**Pruebas de Paridad Legacy**:
- `tests/legacy/test_legacy_feature1.py` - [qué comportamiento valida]
- `tests/legacy/test_legacy_feature2.py` - [qué comportamiento valida]

**Subtareas internas** (3-10 tareas concretas):
1. [Tarea específica 1]
2. [Tarea específica 2]
3. [Tarea específica 3]
...

**Criterio de éxito**: [Cómo sabes que está completa - específico y medible]

**Estimación**: [X horas]

---

### Work Unit 2: [Nombre Descriptivo]

**Propósito**: [Descripción breve]

**Entidades afectadas**: 
- [Entity1]
...

**Archivos a crear/modificar**:
- `path/to/file` - [propósito]
...

**Pruebas de Paridad Legacy**:
- `tests/legacy/test_*.py`
...

**Subtareas internas**:
1. [Tarea]
2. [Tarea]
...

**Criterio de éxito**: [Medible]

**Dependencias**: [WU-001] (si depende de otra Work Unit)

**Estimación**: [X horas]

---

[Agregar más Work Units según sea necesario - target: 5-10 WUs totales]

### Notas para Itti-Kit

**Total estimado de Work Units**: [N]  
**Tiempo total estimado**: [X horas]  
**Work Units que pueden ejecutarse en paralelo**: [WU-001, WU-003, WU-006]

---

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
