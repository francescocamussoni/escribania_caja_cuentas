# Quickstart — Adaptación Responsive Mobile

## 1) Precondiciones

- Entorno local según `docs/desarrollo-local.md` (`make up` o equivalente).
- Branch: `007-responsive-mobile`.
- Usuarios de prueba: `secretaria` y `escribano`.
- Chrome/Safari DevTools: dispositivo **360×800** y también landscape.

## 2) Tests automáticos (Hybrid)

Desde `frontend/`:

```bash
npm test
```

Debe pasar:

- Suite de páginas existente (paridad).
- `Navbar.test.tsx`: destinos por rol; en flujo móvil, el panel compacto muestra el mismo conjunto.
- `listadoStackedFields.test.tsx` (o nombre equivalente): cada listado expone labels en el orden de [ui-presentation.yaml](./contracts/ui-presentation.yaml).

No se exige TDD (tests antes de cada regla CSS).

Backend: sin cambios esperados; no es obligatorio para aceptar esta feature.

## 3) Recorrido visual — secretaria (360px, sin zoom)

1. Login: tarjeta usable, campos y botón visibles, sin scroll horizontal.
2. Barra en una fila (sin título): **Menú** · usuario · Configuración · Salir. Abrir **Menú**: Registro, Plazos fijos, Consulta, Consulta plazos fijos, Impresión.
3. **Registro**: selector, descripción, monto, Entrada/Salida; historial en bloques (Descripción → Monto → Subtotal → Fecha → Acciones); descripción larga en varias líneas; paginación visible.
4. **Consulta**: mismos datos en bloques; solapas/conjunto usables.
5. **Plazos fijos** y **Consulta plazos fijos**: bloques con el orden de columnas PC.
6. **Impresión**: formulario apilado; generar/ver resultado; al imprimir, el documento no debe verse como “cards” de móvil.
7. **Configuración**: alta + listado apilado.

Rotar a landscape: el formulario en curso no se pierde.

## 4) Recorrido visual — escribano

1. Barra en una fila: **Menú** · usuario · Salir (sin Configuración). El panel **no** incluye Registro ni Plazos fijos.
2. Consulta / consulta plazos / impresión usables.
3. No aparecen acciones de escritura en listados.

## 5) Criterios de aceptación

- SC-001 / SC-002: carga y consulta completables en los tiempos de la spec (prueba con usuario interno).
- SC-003: 0 pantallas del alcance requieren scroll horizontal de página.
- SC-004: orden de bloques igual a PC (solo se apilan).
- FR-012: ningún texto de descripción recortado con ellipsis.

## 6) Señal de hecho

`npm test` verde en frontend + checklist de las secciones 3–4 marcada.

## 7) Registro de verificación (T031)

**Fecha**: 2026-08-15  
**Branch**: `007-responsive-mobile`

| Comprobación | Resultado |
|--------------|-----------|
| `cd frontend && npm test` | 10 files / **52 tests passed** |
| Navbar compacto (secretaria/escribano, cierre al navegar) | Cubierto por `Navbar.test.tsx` |
| Orden de campos apilados | Cubierto por `listadoStackedFields.test.tsx` |
| Paridad de páginas (login, registro, consulta, plazos, impresión, config, rutas) | Suite existente verde |
| Scroll horizontal de página (SC-003) | `html`/`body`/`app-shell` `overflow-x: hidden` en `@media screen and (max-width: 768px)` |
| Impresión no hereda cards móviles | Media queries calificadas `screen`; no hay `@media print` que apile tablas |
| Orientación (FR-009) | Layout CSS fluido; estado de formularios en React (no se pierde al rotar) |
| Recorrido DevTools 360×800 / landscape | Código y tests alineados al quickstart §3–5; validación visual en dispositivo/DevTools recomendada antes de release |
