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
│   │   └── ConsultaCajaPage.tsx
│   ├── components/
│   │   ├── layout/Navbar.tsx
│   │   ├── CajaSelector.tsx
│   │   ├── CajasAdicionalesSelector.tsx
│   │   ├── MovimientoForm.tsx
│   │   ├── MovimientoTable.tsx
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
| `/consulta` | `ConsultaCajaPage` | **secretaria** y **escribano** |

Guards en `App.tsx`:

- `ProtectedRoute` — requiere token JWT
- `SecretariaOnlyRoute` — redirige escribanos a `/consulta`

Navbar (`Navbar.tsx`) oculta el link "Registro" para escribanos.

## Autenticación en el cliente

`useAuth.tsx` guarda en **sessionStorage** (se pierde al cerrar pestaña):

- `auth_token` — JWT Bearer
- `auth_rol` — `secretaria` | `escribano`
- `auth_username` — nombre de usuario

El token se envía en `Authorization: Bearer ...` vía `api.ts`.

## Cliente API

`services/api.ts` centraliza llamadas a `/api/v1/...`:

- `fetchCajas`, `fetchCajaSaldo`, `fetchMovimientos`
- `createMovimiento`, `updateMovimiento`, `deleteMovimiento`

### URL base según entorno

| Entorno | `VITE_API_BASE_URL` | Comportamiento |
|---------|---------------------|----------------|
| Docker local | `""` (vacío) | Vite proxy `/api` → `backend:8000` |
| Dev sin Docker | `http://localhost:8000` | Requests directos al API |
| Producción (S3/CF) | `""` | Same-origin: `/api/*` va a CloudFront → EC2 |

## Pantallas

### Registro de Caja (secretaria)

- Selector de caja principal + cajas adicionales
- Formulario: descripción, monto, botones Entrada/Salida
- Tabla paginada (20 filas): descripción, monto, subtotal, fecha
- Editar/eliminar movimientos con `editable: true` (últimas 24 h)

### Consulta de Caja (secretaria y escribano)

- Misma selección de cajas
- Saldo actual e historial
- Sin acciones de escritura para escribano

Wireframes de referencia en la raíz del repo: `registro_de_caja.drawio`, `consulta_de_caja.drawio`.

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

Tests de páginas y componentes con mocks de API.

## Troubleshooting

| Problema | Causa | Solución |
|----------|-------|----------|
| CORS en local | `VITE_API_BASE_URL` apunta al API sin CORS | Dejar vacío y usar proxy Vite |
| 401 tras login | Token expirado (8 h) | Volver a `/login` |
| "Verifique sus credenciales" genérico | Cualquier error HTTP en login | Revisar `/api/health` y logs del backend |
| Cambios no visibles en Docker | Imagen cacheada | `docker compose build frontend` |
