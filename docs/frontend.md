# Frontend

SPA en **React 18** + **TypeScript** + **Vite**. Código en `frontend/src/`.

## Stack

| Componente | Tecnología |
|------------|------------|
| UI | React 18 |
| Routing | react-router-dom v6 |
| Build | Vite 5 |
| Tests | Vitest + Testing Library |
| Estilos | CSS en `index.css` (sin UI framework) |

## Estructura de carpetas

```text
frontend/
├── src/
│   ├── main.tsx           # Entry + AuthProvider
│   ├── App.tsx            # Rutas y guards por rol
│   ├── index.css          # Estilos globales
│   ├── pages/
│   │   ├── LoginPage.tsx
│   │   ├── RegistroCajaPage.tsx
│   │   ├── ConsultaCajaPage.tsx
│   │   ├── PlazosFijosPage.tsx
│   │   ├── ConsultaPlazosFijosPage.tsx
│   │   ├── ImpresionPage.tsx
│   │   └── ConfiguracionCajasPage.tsx
│   ├── components/
│   │   ├── layout/Navbar.tsx
│   │   ├── CajaSelector.tsx
│   │   ├── CajasAdicionalesSelector.tsx
│   │   ├── CajaConsultaSolapa.tsx
│   │   ├── MovimientoForm.tsx
│   │   ├── MovimientoTable.tsx
│   │   ├── PlazoFijoForm.tsx
│   │   ├── PlazoFijoTable.tsx
│   │   ├── PlazosFijosResumenPanel.tsx
│   │   └── Pagination.tsx
│   ├── hooks/
│   │   └── useAuth.tsx    # JWT en sessionStorage
│   └── services/
│       └── api.ts         # Cliente HTTP + tipos
├── tests/                 # Vitest
└── vite.config.ts         # Proxy /api → backend
```

## Rutas y permisos

| Ruta | Componente | Acceso |
|------|------------|--------|
| `/login` | `LoginPage` | Público |
| `/` | Redirige según rol | Autenticado |
| `/registro` | `RegistroCajaPage` | Solo **secretaria** |
| `/plazos-fijos` | `PlazosFijosPage` | Solo **secretaria** |
| `/consulta` | `ConsultaCajaPage` | **secretaria** y **escribano** |
| `/consulta-plazos-fijos` | `ConsultaPlazosFijosPage` | **secretaria** y **escribano** |
| `/impresion` | `ImpresionPage` | **secretaria** y **escribano** |
| `/configuracion` | `ConfiguracionCajasPage` | Solo **secretaria** |

Guards en `App.tsx`:

- `ProtectedRoute` — requiere token JWT
- `SecretariaOnlyRoute` — redirige escribanos a `/consulta` (aplica a `/registro`, `/plazos-fijos` y `/configuracion`)

Navbar (`Navbar.tsx`) muestra links operativos según rol. A la derecha, en este orden: **nombre de usuario** (abre el panel de cambio de clave), **Configuración** (solo secretaria) y **Salir**.

En **viewport &lt; 768px** se oculta el título «Escribanía Barat» y la barra queda en una sola fila: **Menú** · usuario · Configuración (secretaria) · Salir. El botón **Menú** compacta los links operativos en un panel (`aria-expanded`). Al tocar el usuario, el cambio de contraseña se abre a ancho de pantalla (etiquetas completas); un fondo oscurece el contenido. Al elegir un destino el panel de navegación se cierra. En escritorio el título y los links en fila se mantienen.

| Link | Roles |
|------|-------|
| Registro | secretaria |
| Plazos fijos | secretaria |
| Consulta | secretaria, escribano |
| Consulta plazos fijos | secretaria, escribano |
| Impresión | secretaria, escribano |
| Configuración (junto a Salir) | secretaria |

## Layout responsive (móvil)

Breakpoint canónico: `@media screen and (max-width: 768px)` en `index.css` (no aplica a impresión).

- Shell sin scroll horizontal de página; textos largos con wrap (sin recorte).
- Formularios y chrome (headers, consulta, paginación, impresión, configuración) en columna; controles táctiles ~44px.
- Listados (`.movimiento-table`): cada fila es un bloque apilado; etiquetas vía `data-label` en el mismo orden que las columnas de PC (Descripción → Monto → Subtotal → Fecha → Acciones cuando hay edición). El estado vacío no se parte en campos.
- El orden de bloques de cada pantalla coincide con escritorio (`data-block` / `page-stack`).
- Impresión: el formulario de pantalla se apila; el PDF generado no usa el layout de cards móviles.

Contrato: `specs/007-responsive-mobile/contracts/ui-presentation.yaml`. Recorrido: `specs/007-responsive-mobile/quickstart.md`.

## Autenticación en el cliente

`useAuth.tsx` guarda en **sessionStorage** (se pierde al cerrar pestaña):

- `auth_token` — JWT Bearer
- `auth_rol` — `secretaria` | `escribano`
- `auth_username` — nombre de usuario

El token se envía en `Authorization: Bearer ...` vía `api.ts`.

Tras un cambio de clave **autenticado** (`changePassword` → `POST /api/v1/auth/me/password`), el cliente hace **logout** y redirige a `/login`. Los JWT anteriores son rechazados por el backend.

## Cliente API

`services/api.ts` centraliza llamadas a `/api/v1/...`:

- `postChangePasswordPublic` — `POST /api/v1/auth/change-password` (login, sin JWT)
- `postChangePasswordMe` — `POST /api/v1/auth/me/password` (sesión activa)
- `fetchCajas` / `getCajas` — `GET /cajas` (solo activas)
- `listCajasConfig`, `createCaja`, `archiveCaja`, `unarchiveCaja` — configuración (secretaria)
- `fetchCajaSaldo`, `fetchSaldoGeneral`, `fetchMovimientos`
- `createMovimiento`, `updateMovimiento`, `deleteMovimiento`
- `fetchPlazosFijosResumen`, `fetchPlazosFijos`
- `createPlazoFijo`, `updatePlazoFijo`, `deletePlazoFijo`
- `postInformePdf` — genera y descarga PDF de informes (caja o plazo fijo)

### URL base según entorno

| Entorno | `VITE_API_BASE_URL` | Comportamiento |
|---------|---------------------|----------------|
| Docker local | `""` (vacío) | Vite proxy `/api` → `backend:8000` |
| Dev sin Docker | `http://localhost:8000` | Requests directos al API |
| Producción (S3/CF) | `""` | Same-origin: `/api/*` va a CloudFront → EC2 |

## Pantallas

### Login

- Formulario de ingreso (usuario + contraseña)
- Enlace **Cambiar contraseña**: sustituye el formulario de login (no es un overlay). Incluye usuario, contraseña actual, nueva y confirmación; **Cancelar** vuelve al ingreso
- Tras un cambio público exitoso se muestra confirmación y se vuelve al formulario de login (hay que ingresar con la nueva clave)

### Registro de Caja (secretaria)

- Selector de caja principal + cajas adicionales
- Formulario: descripción, monto, botones Entrada/Salida
- Tabla paginada (20 filas): descripción, monto, subtotal, fecha
- Editar/eliminar movimientos con `editable: true` (solo secretaria)

### Consulta de Caja (secretaria y escribano)

- Desplegable de **una** caja + botón **Consulta** (igual que el wireframe `consulta_de_caja.drawio`)
- **secretaria**: botón **Subtotal general** (junto a Consulta) llama `GET /cajas/saldo-general`, muestra la suma y debajo un resumen (nombre + subtotal) de cada caja **activa**. Escribano no ve el botón; el backend responde **403**. Consulta de caja(s) y subtotal general son mutuamente excluyentes en pantalla.
- Debajo: sección **Ver en conjunto con otras cajas** (`CajasAdicionalesSelector` con `summary` distinto; Registro sigue diciendo «Registrar también en otras cajas»)
- **Sin casillas**: valor de caja + historial paginado (20), mismas llamadas `GET .../saldo` y `GET .../movimientos`
- **Con casillas**: `Promise.all` de saldos (principal + marcadas). Si **cualquiera** falla, se descarta el intento (error, sin paneles). Arriba de las solapas se muestra **Valor en conjunto** (suma de los `saldo_actual` de ese intento). Solapas `CajaConsultaSolapa` **cerradas**; primera = caja del desplegable; resto en orden de catálogo. Historial lazy al expandir; paginación independiente
- Sin acciones de escritura para escribano

### Plazos Fijos (secretaria)

- Selector de caja (una caja por plazo; sin cajas adicionales)
- Panel de resumen: dinero ingresado y dinero a cobrar al vencer (solo plazos activos)
- Formulario: monto ingresado, fecha de vencimiento, monto a vencimiento
- Tabla paginada (20 filas) con editar/eliminar sin límite de 24 h

### Consulta Plazos Fijos (secretaria y escribano)

- Selector de caja + botón **Consulta** (carga bajo demanda)
- Mismo panel de resumen dual y tabla que gestión, sin formulario ni acciones de escritura

### Impresión (secretaria y escribano)

- Paridad visual con Consulta de Caja (`consulta_de_caja.drawio`)
- Tipo de informe: **Caja** o **Plazo fijo**
- Selector de caja, temporalidad (**Mes y año** | **Período específico**) y checkbox **Hasta hoy**
- Botón **Generar informe** descarga PDF vía `postInformePdf` (nombre desde `Content-Disposition`)
- Mismos roles que consulta; sin capacidades de escritura adicionales para escribano

### Configuración de cajas (secretaria)

- Alta por nombre (1–120 caracteres); **Agregar** en la misma línea que el campo, a la derecha
- Archivo y desarchivo de cajas; listado de activas y archivadas; las archivadas no aparecen en selectores operativos
- Escribano no ve el link **Configuración**; acceso directo a `/configuracion` redirige a `/consulta`

Wireframes de referencia en la raíz del repo: `registro_de_caja.drawio`, `consulta_de_caja.drawio`.
La solapa Configuración sigue el wireframe descrito en `specs/006-config-archivo-cajas/spec.md`.

## Desarrollo local

### Con Docker (recomendado)

```bash
make up
# Frontend en http://localhost:5173 con hot-reload (volúmenes en docker-compose)
```

### Sin Docker

```bash
cd frontend
npm ci
npm run dev
# Requiere backend en :8000 o ajustar VITE_PROXY_TARGET
```

## Build de producción

```bash
cd frontend
npm ci
VITE_API_BASE_URL="" npm run build
# Salida: frontend/dist/ → sync a S3 en deploy AWS
```

## Tests

```bash
make test-frontend
# o
cd frontend && npm test
```

Tests de páginas y componentes con mocks de API. Incluye `Navbar.test.tsx` (menú compacto y destinos por rol) y `listadoStackedFields.test.tsx` (orden de `data-label` en listados).

## Troubleshooting

| Problema | Causa | Solución |
|----------|-------|----------|
| CORS en local | `VITE_API_BASE_URL` apunta al API sin CORS | Dejar vacío y usar proxy Vite |
| 401 tras login | Token expirado (8 h) o clave cambiada | Volver a `/login` |
| "Verifique sus credenciales" genérico | Cualquier error HTTP en login | Revisar `/api/health` y logs del backend |
| Cambios no visibles en Docker | Imagen cacheada | `docker compose build frontend` |
