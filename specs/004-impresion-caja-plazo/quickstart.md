# Quickstart: Impresión de Caja y Plazos Fijos

**Feature**: `004-impresion-caja-plazo`  
**Branch**: `004-impresion-caja-plazo`  
**Depends on**: `001-registro-cajas`, `003-plazos-fijos` (consulta operativa)

> Documentación operativa: [docs/README.md](../../docs/README.md) · [frontend](../../docs/frontend.md)

## Prerequisites

- Stack local levantado (`make up`, migraciones aplicadas)
- Datos de prueba: movimientos en al menos una caja y plazos fijos opcionales
- Branch `004-impresion-caja-plazo` checked out

## 1. Levantar entorno

```bash
git checkout 004-impresion-caja-plazo
make up
make migrate
```

Usuarios de prueba:

| Usuario | Rol | Uso |
|---------|-----|-----|
| `admin` | secretaria | Generar informes |
| `escribano` | escribano | Generar informes (solo lectura) |

## 2. Verificar API (tras implementación)

Login:

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin"}' | jq -r .access_token)
```

Informe de caja — mes y año, solo ese mes (guardar PDF):

```bash
curl -s -X POST "http://localhost:8000/api/v1/informes/pdf" \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "tipo": "CAJA",
    "caja_id": 2,
    "modo": "MES_ANIO",
    "mes": 3,
    "anio": 2026
  }' \
  -D - -o /tmp/CAJA-Ebel-2026-03.pdf
```

Informe de caja — abril 2026 **hasta hoy** (ej. hoy 17/jul/2026 → abr+may+jun+jul 1–17):

```bash
curl -s -X POST "http://localhost:8000/api/v1/informes/pdf" \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "tipo": "CAJA",
    "caja_id": 2,
    "modo": "MES_ANIO",
    "mes": 4,
    "anio": 2026,
    "hasta_hoy": true
  }' \
  -D - -o /tmp/CAJA-Ebel-2026-04-01_2026-07-17.pdf
```

Verificar cabecera PDF:

```bash
head -c 5 /tmp/CAJA-Ebel-2026-03.pdf
# Esperado: %PDF-
```

Informe plazos fijos — período específico:

```bash
curl -s -X POST "http://localhost:8000/api/v1/informes/pdf" \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "tipo": "PLAZO_FIJO",
    "caja_id": 5,
    "modo": "PERIODO",
    "fecha_inicio": "2026-01-01",
    "fecha_fin": "2026-12-31"
  }' -o /tmp/plazos.pdf
```

Período específico **hasta hoy** (solo fecha inicio):

```bash
curl -s -X POST "http://localhost:8000/api/v1/informes/pdf" \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "tipo": "CAJA",
    "caja_id": 2,
    "modo": "PERIODO",
    "fecha_inicio": "2026-04-01",
    "hasta_hoy": true
  }' -o /tmp/CAJA-Ebel-2026-04-01_2026-07-17.pdf
```

Validación rechazada (fecha inicio > fin):

```bash
curl -s -o /dev/null -w "%{http_code}" -X POST "http://localhost:8000/api/v1/informes/pdf" \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "tipo": "CAJA",
    "caja_id": 1,
    "modo": "PERIODO",
    "fecha_inicio": "2026-06-01",
    "fecha_fin": "2026-01-01"
  }'
# Esperado: 400
```

RBAC — escribano puede generar (200):

```bash
ESC_TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"escribano","password":"escribano"}' | jq -r .access_token)

curl -s -o /dev/null -w "%{http_code}" -X POST "http://localhost:8000/api/v1/informes/pdf" \
  -H "Authorization: Bearer $ESC_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"tipo":"CAJA","caja_id":1,"modo":"MES_ANIO","mes":1,"anio":2026}'
# Esperado: 200
```

Sin autenticación (401):

```bash
curl -s -o /dev/null -w "%{http_code}" -X POST "http://localhost:8000/api/v1/informes/pdf" \
  -H 'Content-Type: application/json' \
  -d '{"tipo":"CAJA","caja_id":1,"modo":"MES_ANIO","mes":1,"anio":2026}'
# Esperado: 401
```

## 3. Frontend (tras implementación)

| Ruta | Roles | Descripción |
|------|-------|-------------|
| `/impresion` | secretaria, escribano | Formulario + botón Generar informe |

```text
http://localhost:5173/impresion
```

Flujo manual:

1. Seleccionar tipo **Caja** o **Plazo fijo**
2. Elegir caja del catálogo
3. Definir **Mes y año** o **Período específico**; opcionalmente marcar **Hasta hoy**
4. Clic **Generar informe** → descarga PDF con nombre `TIPO-Caja-Periodo.pdf`
5. Abrir PDF: verificar encabezado operativo, tablas y (caja) saldos dual + signos Entrada/Salida

## 4. Tests (TDD)

```bash
# Backend
cd backend && pytest tests/unit/test_informe_service.py tests/integration/test_informes_api.py -q

# Frontend
cd frontend && npm test -- ImpresionPage
```

## 5. Criterios de aceptación rápidos

- [x] PDF caja: columnas Descripción, Monto (+/− o Entrada/Salida), Subtotal, Fecha
- [x] PDF caja: saldo al cierre del período + saldo actual
- [x] PDF plazos: resumen solo activos del período filtrado
- [x] Período sin registros: PDF válido con mensaje explícito
- [x] Filename: `CAJA-Ebel-2026-03.pdf` / `CAJA-Ebel-2026-04-01_2026-07-17.pdf` (hasta hoy)
- [ ] Hasta hoy: abril + hoy 17/jul incluye abr, may, jun completos y 1–17 jul *(validación manual con datos reales)*

> Items marcados [x] están cubiertos por tests automatizados (`test_pdf_informe_renderer.py`,
> `test_informes_api.py`, `ImpresionPage.test.tsx`). El ítem de rango acumulado hasta hoy
> requiere verificación manual con fecha de referencia en el entorno local.
