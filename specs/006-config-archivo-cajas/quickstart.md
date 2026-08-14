# Quickstart — Configuración y Archivo de Cajas

## 1) Precondiciones

- Entorno local levantado (`make up`, migraciones y seed aplicados).
- Usuario `secretaria` y usuario no-secretaria disponibles para validación RBAC.
- Branch activo: `006-config-archivo-cajas`.

## 2) Validación TDD mínima esperada

1. Ejecutar tests unitarios de reglas de caja (alta, unicidad, archivo idempotente).
2. Ejecutar tests de integración de endpoints de configuración y permisos.
3. Ejecutar tests frontend de solapa de configuración y exclusión de archivadas.

## 3) Flujo funcional principal (manual)

1. Iniciar sesión como `secretaria`.
2. Abrir solapa de configuración de cajas.
3. Crear una caja nueva con nombre válido.
4. Confirmar que aparece como seleccionable en flujos operativos.
5. Archivar una caja activa.
6. Confirmar que deja de aparecer en todos los desplegables/boxes operativos.
7. Verificar que el historial de la caja archivada sigue consultable.

## 4) Flujo de seguridad/RBAC

1. Iniciar sesión con rol distinto de `secretaria`.
2. Intentar crear caja.
3. Intentar archivar caja.
4. Confirmar rechazo consistente de ambas operaciones.

## 5) Criterios de aceptación a comprobar

- SC-001: 100% de cajas archivadas fuera de selección operativa.
- SC-002: altas disponibles para selección operativa en <= 30 segundos.
- SC-003: 100% de intentos no autorizados rechazados.
- SC-004: tareas de agregar/archivar completables en < 1 minuto por secretaria.
