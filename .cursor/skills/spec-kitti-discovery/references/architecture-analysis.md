# Skill: Discovery — Analyze Architecture

## Purpose
Analyze `graph.json` + `modules.md` and produce `architecture.md` documenting the system's architectural pattern, layers, and infrastructure.

## Input
- `.spec-kitti/discovery/graph.json`
- `.spec-kitti/discovery/raw_index.json`
- `.spec-kitti/discovery/modules.md` (already generated)

## Output
- `.spec-kitti/discovery/architecture.md`

## Instructions

### 1. Detect architectural pattern
From `graph.json.module_level.edges` and weights, identify the pattern:
- **Layered** — clear top-down dependency chain (api → services → domain → infra)
- **Hexagonal/Ports & Adapters** — a core domain with inbound/outbound adapters
- **Modular monolith** — multiple independent modules with a shared kernel
- **Microservices** — multiple entry points, minimal shared code
- **Pipeline** — linear chain of processing stages

Justify your choice with the actual edge weights.

### 2. Main request flow
Trace the path from entry point(s) to external systems:
- Find `entry_point` files in `raw_index.json.file_tree`
- Follow edges in `graph.json.file_level.edges`
- Map the flow: HTTP in → layer by layer → external calls

### 3. Infrastructure & external systems
From `import_aggregation` (non-stdlib packages), identify:
- **Databases**: `sqlalchemy`, `pymongo`, `redis`, `boto3.dynamodb`, `opensearchpy`, etc.
- **Cloud**: `boto3`, `azure-*`, `google-cloud-*`
- **AI/ML**: `langchain*`, `openai`, `anthropic`, `transformers`
- **Messaging**: `kafka`, `pika`, `celery`
- **HTTP**: `fastapi`, `flask`, `django`, `httpx`, `aiohttp`

### 4. Abstractions & patterns
Look for base classes / ABCs in file names:
- `base_*`, `abstract_*`, `*_interface` → abstraction layer
- `*_factory`, `*_strategy`, `*_decorator` → design patterns
- `*_mock`, `*_test` → testability patterns

## Output Format

```markdown
# Architecture — [project name]

> Discovery generated: [date]

## Architectural Pattern
**[Pattern Name]** — [one paragraph justification with edge weights]

## Request Flow
```
[entry_point] → [layer] → [layer] → [external system]
```
[description]

## Infrastructure
| System | Package | Usage |
|--------|---------|-------|
| ...    | ...     | ...   |

## Key Abstractions
- `BaseX` in `src/x/base/` — [purpose]

## Tech Stack Summary
- **Language**: [lang] [version hint if detectable]
- **Framework**: [framework]
- **External services**: [list]
```

## Constraints
- Do NOT read source code — use only JSON inputs and modules.md
- Edge weights = coupling strength, use them to justify pattern detection
- Be concise — bullet points only, no prose paragraphs

