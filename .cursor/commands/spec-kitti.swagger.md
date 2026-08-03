---
description: Scan the repository for controllers, routes, and data models to generate or update an OpenAPI 3.0.0 specification at swagger/openapi.yaml
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## ⚠️ Scope Constraint

**This command ONLY produces the OpenAPI contract file. It MUST NOT generate, create, or modify any application source code files. The only file this command writes is `swagger/openapi.yaml`.**

## Outline

You are an expert Software Architect and API Documenter. Your mission is to scan the current repository, extract every HTTP endpoint, and produce (or update) a complete OpenAPI 3.0.0 specification at `swagger/openapi.yaml`.

Follow this execution flow **strictly**:

### Step 1 — Exhaustive Repository Analysis

Scan the entire source code of the current repository searching for:

- **Route definitions** (endpoints): decorators, router registrations, controller mappings, annotation-based routes.
- **Controllers / Handlers**: classes or functions that handle HTTP requests.
- **Data Models / DTOs / Schemas**: request bodies, response shapes, entities, validation schemas.
- **Middlewares and Guards**: authentication, authorization, rate-limiting, CORS, any security mechanism applied to routes.

You MUST search and map **ALL** HTTP methods without omitting any: **GET, POST, PUT, PATCH, DELETE, OPTIONS, HEAD**.

For each endpoint extract:

| Attribute | Description |
|-----------|-------------|
| URL Path | Full route path including path parameters (e.g. `/v1/users/{id}`) |
| HTTP Method | GET, POST, PUT, PATCH, DELETE, OPTIONS, HEAD |
| Parameters | Headers, Query params, Path params — mark required vs optional |
| Request Body | Payload schema with required and optional fields |
| Responses | All possible status codes (success and error) with response schemas |
| Security | Auth mechanisms applied (Bearer, API Key, OAuth2, etc.) |
| Tags | Module or controller grouping |

Framework-specific patterns to look for:

- **Express/Fastify (Node.js):** `app.get()`, `router.post()`, `@Get()`, `@Post()` (NestJS)
- **Spring (Java/Kotlin):** `@GetMapping`, `@PostMapping`, `@RequestMapping`, `@RestController`
- **FastAPI/Flask/Django (Python):** `@app.route()`, `@router.get()`, `@api_view`, `urlpatterns`
- **ASP.NET (C#):** `[HttpGet]`, `[HttpPost]`, `[Route]`, `[ApiController]`
- **Go (Gin/Echo/Chi):** `r.GET()`, `e.POST()`, `r.Route()`

If the repository does not contain any HTTP endpoints (e.g. it is a CLI tool, a library, or a batch process), **stop immediately** and report:
> "No se encontraron endpoints HTTP en este repositorio. El comando `/spec-kitti.swagger` requiere un proyecto que exponga una API REST o HTTP para generar la especificación OpenAPI."

### Step 2 — Creation vs. Update Logic (Strict Rules)

Check whether `swagger/openapi.yaml` already exists.

#### 2a — File does NOT exist → Create from scratch

1. Create the `swagger/` directory if it does not exist.
2. Generate `swagger/openapi.yaml` using the Reference Template (see Step 4) populated with ALL extracted endpoint data.
3. Set `info.version` to `"0.0.1"`.

#### 2b — File DOES exist → Diff-based update

Perform a comparison between the endpoints found in code and the endpoints already documented in the existing YAML:

- **New endpoints** (in code but NOT in YAML): Add them automatically — no confirmation needed.
- **Existing endpoints with changes**: **STOP.** Do NOT modify automatically. For each changed endpoint, pause and ask the user using this exact format:

  > ⚠️ He detectado cambios en el endpoint `[METHOD] /path` porque `[clear explanation of the change, e.g.: the controller now requires a new header X-Custom-Auth]`. ¿Deseas que actualice esta modificación en el archivo swagger/openapi.yaml? (Sí/No)

  Wait for user confirmation before applying each change. If the user says No, skip that specific endpoint update.

- **Removed endpoints** (in YAML but NOT in code): Flag them to the user:

  > ⚠️ El endpoint `[METHOD] /path` existe en swagger/openapi.yaml pero ya no se encuentra en el código fuente. ¿Deseas eliminarlo del archivo? (Sí/No)

- **Version increment**: If ANY change is made (additions or updates), you MUST increment `info.version` by `+0.0.1` (e.g. `0.0.1` → `0.0.2`).

### Step 3 — Mandatory Examples and Structure Quality

You are responsible for producing rich, clear documentation:

- Include `example:` fields for ALL response schemas, parameters, and request bodies. Invent realistic sample values.
- Use exclusively the **OpenAPI 3.0.0** specification.
- Use `$ref: '#/components/schemas/...'` references to avoid duplicated structures.
- Every schema MUST have a `description` on each property.
- Group endpoints by controller/module using `tags`.
- Include `operationId` for every operation (use camelCase, e.g. `getUserById`).

### Step 4 — Reference Template

Use exactly this structure and format when creating or updating the document. Replace placeholders with real extracted data:

```yaml
openapi: 3.0.0
info:
  title: "Service Name"
  description: "Detailed description of what this API does and what business problem it solves."
  version: "0.0.1"

servers:
  - url: "https://dev.api.com"
    description: Development
  - url: "https://staging.api.com"
    description: Staging
  - url: "https://api.com"
    description: Production

paths:
  /v1/resource:
    get:
      tags:
        - ModuleName
      summary: "Short description of what this GET does"
      operationId: "getResource"
      parameters:
        - in: header
          name: X-Auth-Token
          required: true
          schema:
            type: string
          description: "Authentication token"
          example: "abc123xyz"
      responses:
        '200':
          description: "Successful operation"
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ResourceResponse'
        '401':
          description: "Unauthorized — invalid or missing token"
        '500':
          description: "Internal server error"

    post:
      tags:
        - ModuleName
      summary: "Create a new resource"
      operationId: "createResource"
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/ResourceRequest'
      responses:
        '201':
          description: "Resource created"
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ResourceResponse'
        '400':
          description: "Bad request — validation error"
        '401':
          description: "Unauthorized"

  /v1/resource/{id}:
    get:
      tags:
        - ModuleName
      summary: "Get resource by ID"
      operationId: "getResourceById"
      parameters:
        - in: path
          name: id
          required: true
          schema:
            type: string
          description: "Resource unique identifier"
          example: "res-abc-123"
      responses:
        '200':
          description: "Successful operation"
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ResourceResponse'
        '404':
          description: "Resource not found"

    put:
      tags:
        - ModuleName
      summary: "Full update of a resource"
      operationId: "updateResource"
      parameters:
        - in: path
          name: id
          required: true
          schema:
            type: string
          example: "res-abc-123"
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/ResourceRequest'
      responses:
        '200':
          description: "Resource updated"
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ResourceResponse'

    patch:
      tags:
        - ModuleName
      summary: "Partial update of a resource"
      operationId: "patchResource"
      parameters:
        - in: path
          name: id
          required: true
          schema:
            type: string
          example: "res-abc-123"
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/ResourcePatchRequest'
      responses:
        '200':
          description: "Resource partially updated"
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ResourceResponse'

    delete:
      tags:
        - ModuleName
      summary: "Delete a resource"
      operationId: "deleteResource"
      parameters:
        - in: path
          name: id
          required: true
          schema:
            type: string
          example: "res-abc-123"
      responses:
        '204':
          description: "Successfully deleted"
        '404':
          description: "Resource not found"

components:
  schemas:
    ResourceRequest:
      type: object
      required:
        - required_field
      properties:
        required_field:
          type: string
          description: "Description of the required field"
      example:
        required_field: "sample value"

    ResourcePatchRequest:
      type: object
      properties:
        optional_field:
          type: string
          description: "Field to partially update"
      example:
        optional_field: "updated value"

    ResourceResponse:
      type: object
      properties:
        id:
          type: string
          description: "Unique identifier"
        status:
          type: boolean
          description: "Whether the resource is active"
      example:
        id: "res-abc-123"
        status: true

  securitySchemes:
    BearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT
    ApiKeyAuth:
      type: apiKey
      in: header
      name: X-Auth-Token
```

### Step 5 — Final Report

After completing the generation or update, output a summary:

- **Action performed**: Created from scratch / Updated existing
- **Version**: Previous → New (or `N/A → 0.0.1` for new files)
- **Endpoints documented**: Total count, broken down by HTTP method
- **Schemas created**: List of component schemas
- **Changes applied**: List of additions and confirmed updates
- **Changes skipped**: List of updates the user declined
- **File path**: `swagger/openapi.yaml`
- **Suggested next step**: Recommend validating the spec with a tool like Swagger Editor or `swagger-cli validate swagger/openapi.yaml`

## Behavior Rules

- If no HTTP endpoints are found in the repository, do NOT create an empty or placeholder YAML. Report the absence and stop.
- Never guess endpoint behavior — only document what is explicitly defined in the code.
- If a controller imports middleware but you cannot determine its exact effect, document it as a comment in the YAML and flag it in the report.
- Respect existing YAML formatting and ordering when performing updates.
- Always validate that the produced YAML is syntactically valid OpenAPI 3.0.0 before writing.
- The `servers` block should use placeholder URLs unless real server URLs are found in configuration files (e.g. `.env`, `config.yaml`, `application.properties`).
