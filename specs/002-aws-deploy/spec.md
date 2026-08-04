# Feature Specification: Despliegue en AWS del Registro de Cajas

**Feature Branch**: `002-aws-deploy`  
**Created**: 2026-08-04  
**Status**: Draft  
**Input**: User description: "quiero implementar esto en AWS, lo importante es que la base de datos con la que se levante este vacia y que el lugar de acceso sea una url (no importa comprar un dominio por ahora)"

## Dependencies

- **Feature previa**: `001-registro-cajas` — la aplicación funcional (login, registro y consulta de cajas) debe existir y estar validada en entorno local antes de desplegar.
- **Proveedor cloud**: AWS, según solicitud explícita del usuario.

## Clarifications

### Session 2026-08-04

- Q: ¿Aplicar TDD y/o Unit Tests estrictos para esta feature de despliegue? → A: **Hybrid** — Unit Tests para lógica crítica (scripts, validaciones); smoke/integración post-despliegue; sin TDD estricto.
- Q: ¿Cómo se provisiona el usuario administrador inicial en producción? → A: **Variables de entorno / secretos en despliegue** — bootstrap al primer arranque con credenciales inyectadas de forma segura (p. ej. AWS Secrets Manager o parámetros de entorno).
- Q: ¿Qué nivel de backups de base de datos se requiere en producción? → A: **Backups automáticos mínimos** — retención por defecto del proveedor (p. ej. 7 días en RDS); sin procedimiento documentado de restauración.
- Q: ¿Qué nivel de disponibilidad requiere la base de datos de producción? → A: **Single-AZ** — una sola zona de disponibilidad; menor costo; recuperación manual si falla la instancia.
- Q: ¿En qué región AWS desplegar? → A: **us-east-1** (N. Virginia) — mayor oferta de servicios y menor costo; mayor latencia aceptada.

### Session 2026-08-04 (amend — costo mínimo)

- Q: ¿Rediseñar arquitectura para minimizar costo? → A: **Sí** — eliminar ALB, ECS Fargate, ECR y NAT Gateway; usar **EC2 t4g.micro** (Docker) + **CloudFront/S3** + **RDS micro** + **SSM Parameter Store** (SecureString) para secretos.

## Assumptions

- "Base de datos vacía" significa que el **primer despliegue en producción** no incluye datos de desarrollo ni de prueba: sin movimientos históricos, sin usuarios de prueba precargados y sin datos ficticios. El esquema de tablas y el catálogo maestro de cajas (las 15 cajas del negocio) sí se aplican mediante migraciones, ya que son requisito estructural del sistema.
- No se adquiere dominio propio en esta fase; el acceso se realiza mediante una **URL pública generada por el proveedor cloud** (por ejemplo, un hostname de balanceador o de distribución de contenido).
- El usuario administrador inicial se provisiona de forma segura en el primer despliegue
  mediante **variables de entorno o secretos del proveedor cloud** (no mediante el
  script de seed de desarrollo). Un proceso de bootstrap al primer arranque crea la
  cuenta admin con las credenciales inyectadas; dichas credenciales no residen en el
  código fuente ni en imágenes publicadas.
- El tráfico de acceso debe ser **HTTPS**; no se expone la aplicación solo por HTTP en producción.
- El alcance de esta feature es el **primer entorno productivo accesible por URL**; no incluye dominio personalizado, entornos múltiples (staging/prod) ni pipelines de CI/CD avanzados, salvo lo mínimo necesario para desplegar de forma repetible.
- La base de datos de producción DEBE tener **backups automáticos con retención mínima por defecto del proveedor** (p. ej. 7 días en RDS). No se requiere documentar ni probar procedimientos de restauración en esta fase.
- La base de datos de producción se despliega en **Single-AZ** (una sola zona de disponibilidad) para optimizar costos en esta fase; no se requiere failover automático Multi-AZ.
- El entorno de producción se despliega en la región AWS **us-east-1** (N. Virginia), priorizando costo y disponibilidad de servicios sobre latencia mínima.
- La arquitectura de producción prioriza **costo operativo mínimo** (~USD 20–32/mes
  estimado): una instancia **EC2 t4g.micro** ejecuta el backend en Docker; el frontend
  se sirve desde **S3 + CloudFront**; la API se expone vía behavior `/api/*` de
  CloudFront hacia el origen EC2; **no** se usan ALB, ECS Fargate, ECR ni NAT Gateway.
- Los secretos de producción se almacenan en **SSM Parameter Store** (SecureString),
  no en Secrets Manager, salvo requisito futuro de rotación automática.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Acceder a la aplicación por URL pública (Priority: P1)

Como usuario de la escribanía (secretaria o escribano), necesito abrir la aplicación
desde un navegador web usando una URL pública para poder registrar y consultar cajas
sin depender de una máquina local ni de Docker en mi equipo.

**Why this priority**: Sin una URL accesible desde internet, el despliegue no cumple
el objetivo principal del usuario. Es el resultado visible del proyecto en producción.

**Independent Test**: Puede probarse abriendo la URL publicada desde un navegador
externo (fuera de la red de desarrollo), iniciando sesión y navegando a registro o
consulta según el rol.

**Acceptance Scenarios**:

1. **Given** el sistema desplegado en AWS,
   **When** un usuario abre la URL pública en un navegador estándar,
   **Then** ve la pantalla de inicio de sesión de la aplicación.
2. **Given** un usuario con credenciales válidas provisionadas en producción,
   **When** accede a la URL pública e inicia sesión,
   **Then** puede usar las funcionalidades de su rol (registro para secretaria,
   consulta para ambos roles) sin errores de conectividad.
3. **Given** la URL pública del sistema,
   **When** un usuario intenta acceder por HTTP sin cifrado,
   **Then** es redirigido o bloqueado hacia una conexión segura (HTTPS).
4. **Given** un visitante no autenticado,
   **When** intenta acceder directamente a rutas internas de la aplicación,
   **Then** es redirigido al login, igual que en el entorno local.

---

### User Story 2 - Arrancar con base de datos vacía de datos operativos (Priority: P2)

Como responsable del despliegue, necesito que la base de datos de producción
arranque sin datos de desarrollo ni transacciones previas, para comenzar el
uso real del sistema desde cero.

**Why this priority**: Es un requisito explícito del usuario. Garantiza que el
entorno productivo no hereda basura de pruebas y refleja el estado inicial real
del negocio.

**Independent Test**: Puede probarse tras el primer despliegue verificando que
no existen movimientos registrados, que no hay usuarios de desarrollo precargados
(por ejemplo `admin`/`admin` del seed local) y que las cajas del catálogo maestro
sí están disponibles para operar.

**Acceptance Scenarios**:

1. **Given** un despliegue inicial en AWS,
   **When** se consulta el historial de movimientos de cualquier caja,
   **Then** no hay movimientos registrados.
2. **Given** un despliegue inicial en AWS,
   **When** se intenta iniciar sesión con credenciales del entorno de desarrollo
   (`admin`/`admin` del seed local),
   **Then** el acceso es rechazado.
3. **Given** un despliegue inicial en AWS,
   **When** una secretaria autenticada selecciona una caja,
   **Then** el catálogo de las 15 cajas está disponible y el saldo inicial es cero
   (o el valor definido por ausencia de movimientos).
4. **Given** un despliegue inicial completado,
   **When** el administrador registra el primer movimiento,
   **Then** el movimiento se persiste correctamente y el subtotal se calcula desde
   el estado inicial vacío.

---

### User Story 3 - Desplegar y mantener el entorno de forma repetible (Priority: P3)

Como responsable técnico del proyecto, necesito poder desplegar y actualizar la
aplicación en AWS de forma documentada y repetible, para que el entorno sea
recuperable y actualizable sin depender de pasos manuales no registrados.

**Why this priority**: Asegura que el despliegue no sea un evento único frágil y
que futuras correcciones puedan publicarse en el mismo entorno accesible por URL.

**Independent Test**: Puede probarse siguiendo la documentación de despliegue desde
cero en una cuenta AWS de prueba y verificando que la URL queda operativa; luego
aplicar una actualización menor y confirmar que la aplicación sigue accesible.

**Acceptance Scenarios**:

1. **Given** la documentación de despliegue del proyecto,
   **When** un operador sigue los pasos descritos,
   **Then** obtiene una URL pública funcional en un tiempo razonable (ver SC-003).
2. **Given** un entorno ya desplegado con datos operativos,
   **When** se publica una actualización de la aplicación,
   **Then** los datos existentes en la base de datos se conservan (no se reinicia
   la base a vacía salvo acción explícita de destrucción del entorno).
3. **Given** credenciales y secretos necesarios para el despliegue,
   **When** se revisa el repositorio y la configuración publicada,
   **Then** no contienen contraseñas, tokens ni claves en texto plano.

---

### Edge Cases

- ¿Qué ocurre si el despliegue falla a mitad de camino (base de datos creada pero
  aplicación no levantada)? El operador debe poder identificar el fallo, corregirlo
  y reintentar sin dejar el sistema en un estado inconsistente difícil de diagnosticar.
- ¿Qué ocurre si un usuario intenta acceder mientras se aplica una actualización?
  La aplicación debe degradarse de forma controlada (mensaje de mantenimiento o
  breve indisponibilidad) sin corrupción de datos.
- ¿Qué ocurre si se destruye y recrea el entorno de base de datos? Solo en ese caso
  la base vuelve a estado vacío de datos operativos; debe quedar documentado como
  operación destructiva.
- ¿Qué ocurre si la URL pública cambia tras un redespliegue? Debe documentarse cómo
  obtener la nueva URL; no se requiere dominio fijo en esta fase.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE estar accesible desde internet mediante una URL pública
  proporcionada por el entorno de despliegue en AWS, sin requerir dominio propio.
- **FR-002**: El acceso a la aplicación en producción DEBE realizarse exclusivamente
  por conexión segura (HTTPS).
- **FR-003**: En el primer despliegue a producción, la base de datos DEBE iniciar sin
  movimientos registrados ni usuarios de desarrollo precargados.
- **FR-004**: En el primer despliegue, el catálogo maestro de las 15 cajas DEBE estar
  disponible para operar (aplicado como parte del esquema/migraciones, no como datos
  de prueba opcionales).
- **FR-005**: El sistema DEBE provisionar al menos un usuario administrador inicial en
  producción mediante bootstrap al primer arranque, usando credenciales inyectadas de
  forma segura (variables de entorno o secretos del proveedor cloud); el script de seed
  de desarrollo NO DEBE ejecutarse en producción.
- **FR-006**: Las funcionalidades de `001-registro-cajas` (login, registro de
  movimientos, consulta, roles Secretaria/Escribano, paginación, edición/eliminación
  en ventana de 24 h) DEBEN comportarse igual en el entorno desplegado que en local.
- **FR-007**: El despliegue DEBE documentarse con pasos reproducibles que permitan a
  un operador autorizado levantar el entorno desde cero.
- **FR-008**: Los secretos de producción (contraseñas de base de datos, claves de
  firma de sesión, credenciales de administrador) NO DEBEN almacenarse en el
  repositorio de código ni en imágenes publicadas.
- **FR-009**: Las actualizaciones posteriores al primer despliegue NO DEBEN borrar
  datos operativos existentes de forma accidental.
- **FR-010**: El entorno desplegado DEBE aplicar las migraciones de esquema necesarias
  para que la aplicación funcione contra la base de datos de producción.
- **FR-011**: El despliegue DEBE incluir verificaciones automatizadas post-despliegue
  (smoke/integración) que confirmen URL accesible, HTTPS, login y estado inicial de BD
  vacía de datos operativos.
- **FR-012**: La base de datos de producción DEBE tener backups automáticos habilitados
  con la retención mínima por defecto del proveedor cloud (p. ej. 7 días); no se exige
  documentación ni prueba de restauración en esta fase.
- **FR-013**: La base de datos de producción DEBE desplegarse en configuración Single-AZ
  (una sola zona de disponibilidad); Multi-AZ queda fuera de alcance en esta fase.
- **FR-014**: Todo el entorno de producción DEBE desplegarse en la región AWS **us-east-1**
  (N. Virginia).
- **FR-015**: La arquitectura de producción DEBE minimizar costo mensual evitando ALB,
  ECS Fargate, NAT Gateway y Secrets Manager cuando una instancia EC2 mínima con Docker
  sea suficiente para la carga esperada (≤ 10 usuarios concurrentes).

### Key Entities

- **Entorno de producción**: Instancia desplegada en AWS región **us-east-1** que expone
  la aplicación y su base de datos asociada, accesible por URL pública.
- **URL pública**: Dirección HTTPS compartible que permite el acceso al frontend y,
  de forma indirecta, a las operaciones del backend.
- **Base de datos de producción**: Almacén persistente del entorno cloud; en el
  primer despliegue contiene esquema y catálogo maestro, sin datos operativos ni
  usuarios de desarrollo.
- **Usuario administrador inicial**: Primera cuenta con privilegios para operar el
  sistema en producción, creada automáticamente en el primer arranque a partir de
  credenciales definidas en secretos o variables de entorno del despliegue.
- **Documentación de despliegue**: Guía paso a paso para crear, actualizar y
  diagnosticar el entorno en AWS.

## Testing Strategy

- **Enfoque elegido**: Hybrid (Unit Tests for core logic, no strict TDD)
- **Rationale**: La feature es principalmente infraestructura y operaciones; se exigen
  tests unitarios en scripts y validaciones críticas, más smoke/integración tras el
  despliegue, sin imponer TDD-first en todos los entregables.
- **Alcance de tests**:
  - **Unit Tests**: scripts de despliegue, validación de configuración y lógica
    reutilizable (p. ej. comprobaciones de secretos, health checks automatizados).
  - **Smoke / integración post-despliegue**: verificar URL pública accesible, HTTPS,
    login funcional, BD vacía de datos operativos y catálogo de cajas disponible.
  - **Fuera de alcance de tests obligatorios**: TDD estricto en definiciones de
    infraestructura declarativa (IaC) donde no aplique lógica testeable unitariamente.
- **Nota para downstream**: Esta decisión DEBE ser respetada por `/spec-kitti.plan`
  (contratos de test) y `/spec-kitti.tasks` (generar u omitir tareas TDD/unit-test
  según corresponda).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Un usuario con credenciales válidas puede completar el flujo de login
  y llegar a su pantalla principal (registro o consulta) usando únicamente la URL
  pública, desde un navegador fuera del entorno de desarrollo.
- **SC-002**: Tras el primer despliegue, el 100 % de las cajas del catálogo maestro
  están disponibles y el 0 % de las cajas tienen movimientos históricos.
- **SC-003**: Un operador con la documentación puede obtener una URL funcional en
  menos de 60 minutos en una cuenta AWS nueva (excluyendo tiempos de aprovisionamiento
  de infraestructura que dependan del proveedor).
- **SC-004**: El 100 % de los intentos de acceso por URL usan HTTPS en producción.
- **SC-005**: Tras una actualización de aplicación sin recreación de base de datos,
  los movimientos registrados antes de la actualización permanecen consultables.
- **SC-006**: Un auditor de configuración no encuentra secretos de producción en el
  repositorio ni en artefactos de despliegue inspeccionables públicamente.
- **SC-007**: El costo operativo mensual estimado del entorno base (sin tráfico
  extraordinario) es ≤ **USD 35** en us-east-1 con la arquitectura lean acordada.

## Out of Scope

- Compra y configuración de dominio propio (DNS personalizado).
- Entornos adicionales (staging, QA, disaster recovery).
- Alta disponibilidad multi-región o escalado automático avanzado.
- Monitoreo, alertas y procedimientos de restauración de backups (la retención automática
  mínima de BD sí está incluida; ver FR-012).
- Migración de datos desde un sistema legado o desde el entorno local de desarrollo.
- ALB, ECS Fargate, ECR y NAT Gateway (reemplazados por EC2 + CloudFront en arquitectura lean).
- Alta disponibilidad de compute (single EC2 aceptado en esta fase).
