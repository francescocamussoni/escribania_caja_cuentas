# Research: Registro de Cajas para Escribanía

**Feature**: `001-registro-cajas`  
**Date**: 2026-08-03

## R1 — Stack backend

**Decision**: Python 3.12 + FastAPI + SQLAlchemy 2 + Alembic

**Rationale**:
- FastAPI expone OpenAPI nativo (constitución: contratos explícitos).
- pytest + httpx permiten TDD e integración HTTP declarados en el spec.
- SQLAlchemy maduro para transacciones y recálculo de subtotales en PostgreSQL.
- Ecosistema familiar para equipos Python; despliegue en AWS ECS Fargate o App Runner.

**Alternatives considered**:
- **Node.js + Express**: válido, pero menos ergonomía para tests de integración financiera.
- **Django**: más pesado de lo necesario para API REST acotada.

## R2 — Base de datos

**Decision**: PostgreSQL 16 (local via Docker Compose; producción AWS RDS `db.t4g.micro`)

**Rationale**:
- Recomendación explícita del stakeholder; extrapolación directa a RDS.
- ACID para integridad de subtotales acumulados.
- `NUMERIC(15,2)` para montos ARS sin errores de punto flotante.
- Costo mínimo en AWS alineado con principio VI de la constitución.

**Alternatives considered**:
- **SQLite**: más simple localmente, pero migración a RDS menos representativa.
- **DynamoDB**: sobrecomplejo para consultas cronológicas paginadas y recálculo en cadena.

## R3 — Autenticación y sesión

**Decision**: JWT firmado (HS256) con expiración de 8 horas desde el login; contraseñas con bcrypt (cost ≥ 12)

**Rationale**:
- Cumple FR-001, FR-005, FR-005a sin estado de sesión en servidor (stateless, bajo costo).
- Validación en cada request cumple RBAC server-side (FR-021).
- Usuario bootstrap `admin`/`admin` sembrado por migración/seed (solo dev).

**Alternatives considered**:
- **Sesión en Redis**: más seguro para revocación, pero añade infra y costo innecesario en v1.
- **Cookies HttpOnly**: válido en producción; el frontend puede adoptar cookie en despliegue AWS.

## R4 — Frontend

**Decision**: React 18 + TypeScript + Vite

**Rationale**:
- Build estático desplegable en S3 + CloudFront (costo mínimo AWS).
- TypeScript alinea con contratos OpenAPI (generación opcional de tipos).
- Componentes mapean wireframes `registro_de_caja.drawio` y `consulta_de_caja.drawio`.

**Alternatives considered**:
- **Next.js**: SSR innecesario para app interna de baja escala.
- **Vue**: válido; React tiene mayor disponibilidad de tooling OpenAPI.

## R5 — Cálculo de subtotales

**Decision**: Subtotal calculado en backend al crear movimiento; almacenado en columna `subtotal` por fila; recálculo en transacción DB si se añade edición futura

**Rationale**:
- Cumple principio I (integridad financiera) y FR-010.
- El frontend solo muestra valores devueltos por la API (principio V).
- Orden cronológico por `created_at` + `id` como desempate.

**Alternatives considered**:
- **Subtotal solo calculado en lectura**: más costoso en listados paginados.
- **Event sourcing**: excesivo para v1.

## R6 — Desarrollo local y despliegue AWS

**Decision**: `docker-compose.yml` en raíz con servicios `postgres`, `backend`, `frontend`; variables de entorno en `.env` (gitignored)

**Rationale**:
- Un comando reproduce entorno completo (constitución V).
- Misma imagen/config backend extrapolable a ECS Fargate + RDS.
- Frontend build → S3; API detrás de ALB o API Gateway.

**Alternatives considered**:
- **Serverless Lambda**: viable post-MVP; FastAPI en Lambda requiere adaptador Mangum.
- **EC2 única**: más barata inicialmente pero peor separación de capas.

## R7 — Testing (TDD)

**Decision**: pytest en backend (unit + integration); Vitest + React Testing Library en frontend; contract tests contra OpenAPI

**Rationale**:
- Spec define enfoque `TDD` explícito.
- Constitución exige tests de integración para subtotales y RBAC.
- Orden: test rojo → implementación → verde.

**Alternatives considered**:
- **Solo tests manuales**: rechazado por dominio financiero.

## R8 — Zona horaria y paginación

**Decision**: Timestamps en UTC en DB; presentación en `America/Argentina/Buenos_Aires`; paginación offset-based `page` + `page_size=20`

**Rationale**:
- FR-018/FR-019: 20 registros, página 1 = más recientes.
- Offset simple para volumen bajo (<10k movimientos/caja estimado).

**Alternatives considered**:
- **Cursor-based pagination**: mejor a escala; innecesario en v1.
