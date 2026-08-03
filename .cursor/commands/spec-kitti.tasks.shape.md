---
description: Genera Work Units estructuradas a partir del Plan Jerárquico, reduciendo 120+ tareas a 5-10 unidades de trabajo funcionales.
scripts:
  sh: .spec-kitti/scripts/bash/itti-tasks-shape.sh --json
  ps: scripts/powershell/itti-tasks-shape.ps1 -Json
---

## User Input

```text
$ARGUMENTS
```

## ⚠️ Restricción de Alcance

**Este comando SOLO produce el archivo `work-units.json`. NO debe generar, crear ni modificar ningún archivo de código fuente de la aplicación (ej. `.ts`, `.py`, `.js`, `.java`, etc.). La generación de código fuente es responsabilidad exclusiva de `/spec-kitti.implement`.**

## Outline

Este comando transforma el Plan Jerárquico en **Work Units** (Unidades de Trabajo) autocontenidas y ejecutables de forma autónoma.

### ¿Qué es una Work Unit?

Una Work Unit es **UN ARCHIVO** (a crear o modificar) con todas sus tareas asociadas:
- - **1 Work Unit = 1 Archivo** (src/users/user.controller.ts, src/models/user.py, etc.)
- - Incluye 3-15 subtareas específicas para ese archivo
- - Especifica acción: CREATE, MODIFY, o DELETE
- - Lista dependencias (otros archivos que deben existir primero)
- - Tiene pruebas de paridad legacy asociadas
- - Se puede execute de forma autónoma

### Workflow

1. **Cargar contexto**: Lee `plan.md` del feature actual
   ```bash
   {SCRIPT}
   ```

2. **Analizar Plan Jerárquico**: Busca la sección "## Plan Jerárquico" o "## Implementation Phases"
   - Si no existe, ERROR: "Plan debe contener sección jerárquica. Ejecuta /plan primero."

3. **Identificar Work Units (Archivos)**: Extrae cada archivo a crear/modificar del plan
   - **Heurísticas de identificación**:
     - Buscar menciones explícitas de archivos (*.ts, *.py, *.java, etc.)
     - Inferir archivos desde estructura arquitectónica (Controller → Service → Repository)
     - Agrupar por feature module (users/, orders/, payments/)
   - **Límites de tamaño**:
     - Mínimo 3 subtareas por archivo
     - Máximo 15 subtareas por archivo
     - Target: 10-30 archivos (Work Units) totales
   - **Orden jerárquico**:
     - Primero archivos base (entities, DTOs, models)
     - Luego archivos de lógica (services, managers)
     - Finalmente archivos de presentación (controllers, routes)

4. **Identificar Pruebas Legacy**: Para cada WU, determina qué pruebas legacy debe pasar
   - Lee `spec.md` sección "## Legacy Tests" (si existe)
   - Infiere del nombre de la WU (ej: "Autenticación" → busca `test_*auth*.py`)
   - Si no hay pruebas legacy, marca como `"legacy_tests": []` pero agrega warning

5. **Detectar Dependencias**: Analiza si una WU depende de otra
   ```json
   "dependencies": ["WU-001", "WU-003"]
   ```
   - Si WU-002 usa modelos de WU-001 → dependencia
   - Si WU-004 requiere API de WU-002 → dependencia

6. **Generate `work-units.json`**: 
   ```json
   {
     "metadata": {
       "feature": "001-user-management",
       "generated_at": "2025-11-07T16:00:00Z",
       "total_work_units": 12,
       "estimated_hours": 18,
       "parity_contract_reference": ".spec-kitti/discovery/endpoint_mapping_schema.json"
     },
     "work_units": [
       {
         "id": "WU-001",
         "file_path": "src/users/entities/user.entity.ts",
         "action": "CREATE",
         "description": "Entidad User con TypeORM, todos los campos del Parity Contract, constraints y timestamps",
         "priority": 1,
         "estimated_hours": 1,
         "parity_anchors": ["EP001", "EP002", "EP003"],
         "affected_endpoints": [
           "GET /api/users",
           "GET /api/users/:id",
           "POST /api/users"
         ],
         "legacy_tests": [
           "tests/legacy/test_user_entity.py"
         ],
         "subtasks": [
           "1. Crear clase User con decorador @Entity()",
           "2. Definir campos: id (UUID), username (unique), email (unique), password_hash, created_at, updated_at",
           "3. Agregar constraints: @Column({unique: true, nullable: false}) para username y email",
           "4. Agregar decoradores de timestamp: @CreateDateColumn(), @UpdateDateColumn()",
           "5. Agregar índices: @Index(['username']), @Index(['email'])",
           "6. Implementar método toJSON() para excluir password_hash",
           "7. Validar que campos coincidan exactamente con Parity Contract EP001-EP003"
         ],
         "success_criteria": "Entity compilada sin errores, campos coinciden 100% con Parity Contract",
         "dependencies": [],
         "parallel_safe": true
       },
       {
         "id": "WU-002",
         "file_path": "src/users/dto/create-user.dto.ts",
         "action": "CREATE",
         "description": "DTO para creación de usuarios con validaciones según business rules del Parity Contract",
         "priority": 1,
         "estimated_hours": 0.5,
         "parity_anchors": ["EP003"],
         "business_rules": ["BR001", "BR002"],
         "legacy_tests": [],
         "subtasks": [
           "1. Crear clase CreateUserDto",
           "2. Agregar campo username con @IsString(), @IsNotEmpty(), @MinLength(3), @MaxLength(20)",
           "3. Agregar campo email con @IsEmail(), @IsNotEmpty()",
           "4. Agregar campo password con @IsString(), @MinLength(8), @Matches() para complejidad",
           "5. Aplicar business rule BR001: username debe ser alfanumérico + underscore",
           "6. Aplicar business rule BR002: email debe ser corporativo (@company.com)",
           "7. Agregar comentarios JSDoc con ejemplos del Parity Contract"
         ],
         "success_criteria": "DTO valida correctamente según reglas de negocio documentadas",
         "dependencies": [],
         "parallel_safe": true
       },
       {
         "id": "WU-003",
         "file_path": "src/users/dto/update-user.dto.ts",
         "action": "CREATE",
         "description": "DTO para actualización parcial de usuarios, extiende CreateUserDto",
         "priority": 1,
         "estimated_hours": 0.3,
         "parity_anchors": ["EP004"],
         "legacy_tests": [],
         "subtasks": [
           "1. Importar CreateUserDto y PartialType desde @nestjs/mapped-types",
           "2. Crear clase UpdateUserDto extends PartialType(CreateUserDto)",
           "3. Agregar campo opcional isActive: @IsBoolean(), @IsOptional()",
           "4. Documentar que username y email siguen siendo únicos si se actualizan"
         ],
         "success_criteria": "DTO permite actualizaciones parciales correctamente",
         "dependencies": ["WU-002"],
         "parallel_safe": false
       },
       {
         "id": "WU-004",
         "file_path": "src/users/users.repository.ts",
         "action": "CREATE",
         "description": "Repositorio TypeORM para User con métodos de consulta y persistencia",
         "priority": 2,
         "estimated_hours": 1.5,
         "parity_anchors": ["EP001", "EP002", "EP003", "EP004", "EP005"],
         "legacy_tests": [
           "tests/legacy/test_user_repository.py"
         ],
         "subtasks": [
           "1. Crear clase UserRepository extends Repository<User>",
           "2. Implementar findAll(page, size): Promise<[User[], number]> con paginación",
           "3. Implementar findById(id): Promise<User | null>",
           "4. Implementar findByUsername(username): Promise<User | null>",
           "5. Implementar findByEmail(email): Promise<User | null>",
           "6. Implementar create(createUserDto): Promise<User> con hash de password",
           "7. Implementar update(id, updateUserDto): Promise<User>",
           "8. Implementar softDelete(id): Promise<boolean> (no hard delete)",
           "9. Agregar transacciones con @Transaction() donde sea necesario"
         ],
         "success_criteria": "Todos los métodos pasan legacy tests, transacciones correctas",
         "dependencies": ["WU-001"],
         "parallel_safe": false
       },
       {
         "id": "WU-005",
         "file_path": "src/users/users.service.ts",
         "action": "CREATE",
         "description": "Servicio con lógica de negocio para gestión de usuarios, implementa business rules",
         "priority": 3,
         "estimated_hours": 2.5,
         "parity_anchors": ["EP001", "EP002", "EP003", "EP004", "EP005"],
         "business_rules": ["BR001", "BR002", "BR003", "BR004"],
         "legacy_tests": [
           "tests/legacy/test_user_service.py",
           "tests/legacy/test_user_business_rules.py"
         ],
         "subtasks": [
           "1. Crear clase UserService con @Injectable()",
           "2. Inyectar UserRepository en constructor",
           "3. Implementar listUsers(page, size) con paginación (BR003: default 20, max 100)",
           "4. Implementar getUser(id) con validación de existencia",
           "5. Implementar createUser(dto) con hash de password usando bcrypt",
           "6. Aplicar BR001: validar username único antes de crear",
           "7. Aplicar BR002: validar email corporativo y único",
           "8. Aplicar BR004: no permitir crear usuarios con rol ADMIN directamente",
           "9. Implementar updateUser(id, dto) respetando campos inmutables",
           "10. Implementar deleteUser(id) como soft-delete",
           "11. Agregar logging de todas las operaciones",
           "12. Implementar manejo de errores con excepciones custom"
         ],
         "success_criteria": "Todos los business rules aplicados correctamente, legacy tests pasan 100%",
         "dependencies": ["WU-004"],
         "parallel_safe": false
       },
       {
         "id": "WU-006",
         "file_path": "src/users/users.controller.ts",
         "action": "CREATE",
         "description": "Controller REST para gestión de usuarios, expone endpoints del Parity Contract",
         "priority": 4,
         "estimated_hours": 2,
         "parity_anchors": ["EP001", "EP002", "EP003", "EP004", "EP005"],
         "affected_endpoints": [
           "GET /api/users",
           "GET /api/users/:id",
           "POST /api/users",
           "PUT /api/users/:id",
           "DELETE /api/users/:id"
         ],
         "legacy_tests": [
           "tests/legacy/test_user_api.py"
         ],
         "subtasks": [
           "1. Crear clase UserController con @Controller('users')",
           "2. Inyectar UserService en constructor",
           "3. Implementar GET /users con @Get() y paginación (@Query page, size)",
           "4. Implementar GET /users/:id con @Get(':id') y @Param('id')",
           "5. Implementar POST /users con @Post() y @Body(CreateUserDto)",
           "6. Implementar PUT /users/:id con @Put(':id') y @Body(UpdateUserDto)",
           "7. Implementar DELETE /users/:id con @Delete(':id')",
           "8. Agregar decoradores @ApiTags(), @ApiResponse() para Swagger",
           "9. Implementar manejo de excepciones con @UseFilters()",
           "10. Validar que response format coincida EXACTAMENTE con Parity Contract"
         ],
         "success_criteria": "API REST funciona con mismo comportamiento que legacy, legacy tests pasan",
         "dependencies": ["WU-005"],
         "parallel_safe": false
       },
       {
         "id": "WU-007",
         "file_path": "src/users/users.module.ts",
         "action": "CREATE",
         "description": "Módulo NestJS para users, registra controllers, services y repositories",
         "priority": 5,
         "estimated_hours": 0.5,
         "parity_anchors": [],
         "legacy_tests": [],
         "subtasks": [
           "1. Crear clase UsersModule con @Module()",
           "2. Importar TypeOrmModule.forFeature([User])",
           "3. Agregar UserService a providers",
           "4. Agregar UserController a controllers",
           "5. Exportar UserService para uso en otros módulos"
         ],
         "success_criteria": "Módulo se importa correctamente en AppModule sin errores",
         "dependencies": ["WU-001", "WU-004", "WU-005", "WU-006"],
         "parallel_safe": false
       },
       {
         "id": "WU-008",
         "file_path": "src/users/tests/user.controller.spec.ts",
         "action": "CREATE",
         "description": "Tests unitarios para UserController, mockeando UserService",
         "priority": 6,
         "estimated_hours": 1.5,
         "parity_anchors": ["EP001", "EP002", "EP003"],
         "legacy_tests": [],
         "subtasks": [
           "1. Crear suite de tests con describe('UserController')",
           "2. Configurar TestingModule con mocks de UserService",
           "3. Test: GET /users retorna lista paginada correctamente",
           "4. Test: GET /users/:id retorna usuario o 404",
           "5. Test: POST /users crea usuario y retorna 201",
           "6. Test: PUT /users/:id actualiza y retorna usuario modificado",
           "7. Test: DELETE /users/:id soft-deletes y retorna 204",
           "8. Test: validaciones de DTO fallan correctamente (400)",
           "9. Verificar que mocks de service son llamados con parámetros correctos"
         ],
         "success_criteria": "Coverage >= 90% del controller, todos los tests pasan",
         "dependencies": ["WU-006"],
         "parallel_safe": true
       },
       {
         "id": "WU-009",
         "file_path": "src/users/tests/user.service.spec.ts",
         "action": "CREATE",
         "description": "Tests unitarios para UserService, mockeando UserRepository",
         "priority": 6,
         "estimated_hours": 2,
         "business_rules": ["BR001", "BR002", "BR003", "BR004"],
         "legacy_tests": [],
         "subtasks": [
           "1. Configurar suite con mocks de UserRepository",
           "2. Test: listUsers aplica paginación correctamente (BR003)",
           "3. Test: getUser lanza NotFoundException si no existe",
           "4. Test: createUser hashea password con bcrypt",
           "5. Test: createUser valida username único (BR001)",
           "6. Test: createUser valida email corporativo (BR002)",
           "7. Test: createUser rechaza rol ADMIN (BR004)",
           "8. Test: updateUser no modifica campos inmutables",
           "9. Test: deleteUser hace soft-delete (no elimina físicamente)",
           "10. Verificar logging en todas las operaciones"
         ],
         "success_criteria": "Coverage >= 95% del service, business rules validadas",
         "dependencies": ["WU-005"],
         "parallel_safe": true
       },
       {
         "id": "WU-010",
         "file_path": "src/users/tests/user.e2e.spec.ts",
         "action": "CREATE",
         "description": "Tests end-to-end del módulo users contra base de datos real",
         "priority": 7,
         "estimated_hours": 2.5,
         "parity_anchors": ["EP001", "EP002", "EP003", "EP004", "EP005"],
         "legacy_tests": [
           "tests/legacy/test_user_integration.py",
           "tests/legacy/test_user_e2e.py"
         ],
         "subtasks": [
           "1. Configurar TestingModule con base de datos de test (SQLite in-memory)",
           "2. Test: flujo completo CREATE → GET → UPDATE → DELETE",
           "3. Test: paginación con múltiples páginas",
           "4. Test: búsqueda por username y email",
           "5. Test: validaciones de negocio en flujo real",
           "6. Test: manejo de errores (404, 400, 409 conflict)",
           "7. Test: transacciones y rollback en caso de error",
           "8. Comparar resultados con legacy tests (deben ser idénticos)"
         ],
         "success_criteria": "Todos los legacy tests e2e pasan sin modificación",
         "dependencies": ["WU-007"],
         "parallel_safe": false
       },
       {
         "id": "WU-011",
         "file_path": "migrations/001_create_users_table.ts",
         "action": "CREATE",
         "description": "Migración TypeORM para crear tabla users con índices y constraints",
         "priority": 1,
         "estimated_hours": 0.5,
         "parity_anchors": [],
         "legacy_tests": [],
         "subtasks": [
           "1. Crear clase CreateUsersTable implements MigrationInterface",
           "2. Implementar up(): crear tabla users con todos los campos",
           "3. Agregar constraints UNIQUE en username y email",
           "4. Agregar índices en username, email, created_at",
           "5. Implementar down(): drop table users",
           "6. Probar migración up y down múltiples veces"
         ],
         "success_criteria": "Migración se ejecuta sin errores, rollback funciona",
         "dependencies": [],
         "parallel_safe": true
       },
       {
         "id": "WU-012",
         "file_path": "docs/api/users.md",
         "action": "CREATE",
         "description": "Documentación completa de API de usuarios con ejemplos del Parity Contract",
         "priority": 8,
         "estimated_hours": 1,
         "parity_anchors": ["EP001", "EP002", "EP003", "EP004", "EP005"],
         "legacy_tests": [],
         "subtasks": [
           "1. Documentar cada endpoint con formato OpenAPI",
           "2. Incluir ejemplos de request/response del Parity Contract",
           "3. Documentar business rules (BR001-BR004)",
           "4. Documentar codes de error posibles",
           "5. Agregar diagrama de flujo de operaciones",
           "6. Incluir ejemplos de uso con curl",
           "7. Documentar diferencias con API legacy (si las hay)"
         ],
         "success_criteria": "Documentación completa, ejemplos probados y funcionales",
         "dependencies": ["WU-006"],
         "parallel_safe": true
       }
     ]
   }
   ```

7. **Validar y Reportar**:
   - - Total de archivos (WUs) generados
   - - Archivos base vs archivos dependientes
   - - Archivos que pueden crearse en paralelo
   - - Orden de ejecución recomendado (basado en dependencias entre archivos)
   - WARNING:  Archivos sin pruebas legacy (requieren atención manual)
   - Estadísticas: CREATE vs MODIFY vs DELETE

## Output

Después de execute este comando, el usuario verá:

```
- Work Units generadas exitosamente (Agrupadas por Archivo)

Resumen:
   • Total de archivos (Work Units): 12
   • Archivos a CREAR: 11
   • Archivos a MODIFICAR: 1
   • Archivos sin dependencias (base): 4 
   • Archivos que pueden crearse en paralelo: 6
   • Archivos con legacy tests: 8
   • Tiempo estimado total: 18 horas
   
Archivo generado:
   .spec-kitti/work-units.json
   
**Estructura de Archivos:
   Módulo: src/users/
   ├── entities/
   │   └── WU-001: user.entity.ts [CREATE] (1h)
   ├── dto/
   │   ├── WU-002: create-user.dto.ts [CREATE] (0.5h)
   │   └── WU-003: update-user.dto.ts [CREATE] (0.3h)
   ├── WU-004: users.repository.ts [CREATE] (1.5h)
   ├── WU-005: users.service.ts [CREATE] (2.5h)
   ├── WU-006: users.controller.ts [CREATE] (2h)
   ├── WU-007: users.module.ts [CREATE] (0.5h)
   └── tests/
       ├── WU-008: user.controller.spec.ts [CREATE] (1.5h)
       ├── WU-009: user.service.spec.ts [CREATE] (2h)
       └── WU-010: user.e2e.spec.ts [CREATE] (2.5h)
   
   migrations/
   └── WU-011: 001_create_users_table.ts [CREATE] (0.5h)
   
   docs/api/
   └── WU-012: users.md [CREATE] (1h)

Orden de ejecución recomendado:
   FASE 1 (Paralelo - Base):
   • WU-001 (entity) 
   • WU-002 (DTO create)
   • WU-011 (migration)
   
   FASE 2 (Secuencial):
   • WU-003 (DTO update) → depende de WU-002
   • WU-004 (repository) → depende de WU-001
   
   FASE 3:
   • WU-005 (service) → depende de WU-004
   
   FASE 4:
   • WU-006 (controller) → depende de WU-005
   
   FASE 5:
   • WU-007 (module) → depende de WU-001, WU-004, WU-005, WU-006
   
   FASE 6 (Paralelo - Tests):
   • WU-008 (controller tests) → depende de WU-006
   • WU-009 (service tests) → depende de WU-005
   • WU-010 (e2e tests) → depende de WU-007
   • WU-012 (docs) → depende de WU-006

**Siguiente paso:
   Ejecuta: /spec-kitti.implement.unit WU-001
   
   Para execute varios archivos en paralelo:
   /spec-kitti.implement.unit WU-001 WU-002 WU-011
```

## Reglas de Generación

### 1. Granularidad Adecuada (1 Work Unit = 1 Archivo)
- - **Correcto**: WU-001 = `src/users/user.entity.ts` con 7 subtareas
- - **Correcto**: WU-002 = `src/users/user.service.ts` con 12 subtareas
- - **Incorrecto**: "Implementar todo el módulo de usuarios" → Dividir en archivos individuales
- - **Incorrecto**: Agrupar múltiples archivos en una WU (entity + service + controller)

### 2. Pruebas de Paridad Obligatorias
- Cada WU que toque lógica de negocio DEBE tener `legacy_tests` asociados
- Si no existen pruebas legacy, la WU debe incluir subtarea: "Crear tests de paridad basados en comportamiento legacy documentado"

### 3. Dependencias Explícitas entre Archivos
- Si un archivo IMPORTA code de otro archivo, declarar en `dependencies`
- Ejemplo: `user.service.ts` importa de `user.repository.ts` → WU-005 depende de WU-004
- Ejemplo: `user.controller.ts` importa de `user.service.ts` → WU-006 depende de WU-005
- El orquestador usará esto para prevenir creación de archivos antes de sus dependencias
- **Orden típico**: entity → dto → repository → service → controller → module → tests

### 4. Estimaciones Realistas por Archivo
- `estimated_hours` basado en tipo y complejidad del archivo:
  - **Entity/DTO simple**: 0.3-0.5 horas
  - **Repository básico**: 1-1.5 horas
  - **Service con business logic**: 2-3 horas
  - **Controller REST**: 1.5-2 horas
  - **Module (wiring)**: 0.5 horas
  - **Tests unitarios**: 1.5-2 horas
  - **Tests e2e**: 2-3 horas
  - **Migration**: 0.5-1 hora
  - **Documentation**: 1 hora

### 5. Paralelización Segura entre Archivos
- `parallel_safe: true` solo si:
  - El archivo no tiene dependencias (`dependencies: []`)
  - Archivos como entity, DTO, migration pueden crearse en paralelo
  - Tests pueden executese en paralelo SI no comparten base de datos
  - **Ejemplo**: WU-001 (entity) + WU-002 (DTO) + WU-011 (migration) pueden executese simultáneamente

## Algoritmo de Agrupación por Archivos

```python
def group_tasks_into_work_units_by_file(plan_hierarchical, parity_contract):
    """
    Algoritmo para transformar plan jerárquico en Work Units (1 WU = 1 Archivo).
    """
    work_units = []
    
    # 1. Extraer estructura de módulos del plan
    modules = extract_modules_from_plan(plan_hierarchical)
    # Ejemplo: modules = [{"name": "users", "path": "src/users"}, {...}]
    
    for module in modules:
        # 2. Inferir archivos necesarios según arquitectura
        files = infer_required_files(module, architecture_pattern="NestJS")
        # Ejemplo: entity, dto, repository, service, controller, module, tests
        
        for file_info in files:
            # 3. Generate subtareas específicas para ese archivo
            subtasks = generate_subtasks_for_file(
                file_type=file_info['type'],  # "entity", "service", etc.
                file_path=file_info['path'],
                parity_anchors=find_parity_anchors(file_info, parity_contract),
                business_rules=find_business_rules(file_info, parity_contract)
            )
            
            # 4. Crear Work Unit (1 archivo = 1 WU)
            wu = {
                "id": generate_id(),
                "file_path": file_info['path'],
                "action": file_info.get('action', 'CREATE'),  # CREATE, MODIFY, DELETE
                "description": file_info['description'],
                "subtasks": subtasks,
                "estimated_hours": estimate_hours(file_info['type'], len(subtasks)),
                "parity_anchors": file_info.get('parity_anchors', []),
                "business_rules": file_info.get('business_rules', []),
                "legacy_tests": find_legacy_tests(file_info),
                "dependencies": [],  # Se calcula después
                "parallel_safe": False  # Se calcula después
            }
            
            work_units.append(wu)
    
    # 5. Calcular dependencias entre archivos (imports)
    for wu in work_units:
        wu['dependencies'] = calculate_file_dependencies(wu, work_units)
        # Si user.service.ts importa user.repository.ts, agregar dependencia
    
    # 6. Determinar paralelización segura
    for wu in work_units:
        wu['parallel_safe'] = len(wu['dependencies']) == 0
    
    # 7. Asignar prioridades con topological sort
    work_units = topological_sort(work_units)
    
    return work_units

def infer_required_files(module, architecture_pattern):
    """
    Infiere qué archivos se necesitan según el patrón de arquitectura.
    """
    if architecture_pattern == "NestJS":
        return [
            {"type": "entity", "path": f"{module['path']}/entities/{module['name']}.entity.ts"},
            {"type": "dto", "path": f"{module['path']}/dto/create-{module['name']}.dto.ts"},
            {"type": "dto", "path": f"{module['path']}/dto/update-{module['name']}.dto.ts"},
            {"type": "repository", "path": f"{module['path']}/{module['name']}.repository.ts"},
            {"type": "service", "path": f"{module['path']}/{module['name']}.service.ts"},
            {"type": "controller", "path": f"{module['path']}/{module['name']}.controller.ts"},
            {"type": "module", "path": f"{module['path']}/{module['name']}.module.ts"},
            {"type": "test", "path": f"{module['path']}/tests/{module['name']}.controller.spec.ts"},
            {"type": "test", "path": f"{module['path']}/tests/{module['name']}.service.spec.ts"},
            {"type": "test", "path": f"{module['path']}/tests/{module['name']}.e2e.spec.ts"},
        ]
    # Más patrones: Django, Spring Boot, etc.
    
def calculate_file_dependencies(wu, all_wus):
    """
    Calcula dependencias basándose en imports típicos entre archivos.
    """
    deps = []
    file_type = get_file_type(wu['file_path'])
    
    # Reglas de dependencia según tipo de archivo
    dependency_rules = {
        "dto-update": ["dto-create"],  # UpdateDto extiende CreateDto
        "repository": ["entity"],      # Repository usa Entity
        "service": ["repository", "dto"],  # Service usa Repository y DTOs
        "controller": ["service", "dto"],  # Controller usa Service y DTOs
        "module": ["entity", "service", "controller"],  # Module registra todo
        "controller.spec": ["controller"],  # Tests dependen del archivo testeado
        "service.spec": ["service"],
        "e2e.spec": ["module"]
    }
    
    required_types = dependency_rules.get(file_type, [])
    for other_wu in all_wus:
        other_type = get_file_type(other_wu['file_path'])
        if other_type in required_types and in_same_module(wu, other_wu):
            deps.append(other_wu['id'])
    
    return deps
```

## Errores Comunes a Prevenir

1. **Work Units sin criterio de éxito**: Cada WU DEBE tener `success_criteria` medible
2. **Ciclos de dependencias**: WU-001 depende de WU-002 que depende de WU-001 → ERROR
3. **WUs huérfanas**: WU que no aparece en dependencias de ninguna otra (posible duplicación)
4. **Estimaciones irreales**: Total de horas > 100 para un feature → Replantear alcance

## Integración con Motor de Orquestación

El `work-units.json` generado es consumido por `/implement.unit <ID>`:

```bash
# Usuario ejecuta
/implement.unit WU-001

# Sistema internamente hace
itti-orchestrator.sh WU-001

# Orquestador lee work-units.json, extrae WU-001 y ejecuta:
# 1. Agente Executor (genera code basándose en subtasks)
# 2. Agente de Pruebas (ejecuta legacy_tests)
# 3. Bucle de corrección (si FAIL, vuelve a 1 con reporte)
# 4. Crea PR (si PASS)
```

## Ejemplo de Uso Completo

```bash
# 1. Usuario crea especificación
/specify Modernizar sistema de facturación de PHP a Python

# 2. Usuario crea plan técnico
/plan Usar FastAPI, PostgreSQL, mantener compatibilidad total con API legacy

# 3. Sistema genera Work Units automáticamente
/tasks.shape

# Output:
# - 8 Work Units generadas
#    WU-001: Migrar modelos de factura
#    WU-002: API de creación de facturas
#    WU-003: API de consulta de facturas
#    WU-004: Sistema de cálculo de impuestos
#    WU-005: Integración con pasarela de pago
#    WU-006: Migración de datos históricos
#    WU-007: Tests end-to-end
#    WU-008: Documentación y deploy

# 4. Usuario ejecuta WUs autónomamente
/implement.unit WU-001
# [Sistema auto-corrige hasta que tests legacy pasan]
# - PR creado: "WU-001: Migración de modelos (18 tests legacy passed)"

/implement.unit WU-002
# [Ciclo autónomo]
# - PR creado: "WU-002: API creación facturas (12 tests legacy passed)"
```

## Variables de Entorno

```bash
# Configuración de generación de WUs
export ITTI_MAX_WUS=10              # Máximo de WUs a generate
export ITTI_MIN_SUBTASKS_PER_WU=3   # Mínimo de subtareas por WU
export ITTI_MAX_SUBTASKS_PER_WU=15  # Máximo de subtareas por WU
export ITTI_REQUIRE_LEGACY_TESTS=1  # Si 1, error si WU no tiene legacy tests
```

---

**Estado**: Comando Core de Itti-Kit  
**Dependencias**: Plan Jerárquico en `plan.md`  
**Output**: `work-units.json`  
**Siguiente**: `/implement.unit <ID>`

