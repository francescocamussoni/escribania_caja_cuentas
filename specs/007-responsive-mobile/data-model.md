# Data Model — Adaptación Responsive Mobile

Esta feature **no introduce entidades persistidas**. El modelo es de presentación (cómo se muestra lo que ya existe).

## Entity: Vista de Pantalla

**Description**: Una ruta de la aplicación renderizada según viewport y orientación.

**Fields**:
- `ruta` (enum de rutas actuales): `/login`, `/registro`, `/consulta`, `/plazos-fijos`, `/consulta-plazos-fijos`, `/impresion`, `/configuracion`
- `modo_viewport` (enum): `desktop` (>= 768px) | `mobile` (< 768px)
- `orientacion` (enum): `vertical` | `horizontal` — no persiste; el CSS reacomoda

**Validation Rules**:
- Toda vista autenticada conserva las mismas acciones que en PC para el rol.
- El cambio de orientación no borra estado de formularios en memoria (React state).

**State Transitions**:
- `desktop <-> mobile` al cruzar 768px (p. ej. rotación en tablet o DevTools).
- No hay transición de negocio.

## Entity: Bloque Funcional de Interfaz

**Description**: Grupo de controles que debe conservar orden lógico PC → móvil (arriba hacia abajo).

**Campos / bloques canónicos por pantalla**:

| Pantalla | Orden de bloques (móvil = mismo orden, apilados) |
|----------|--------------------------------------------------|
| Login | título → campos → acciones → enlace auxiliar |
| Registro | selector caja → formulario movimiento → historial → paginación |
| Consulta | controles (caja/consulta) → saldo/solapas → historial → paginación |
| Plazos fijos | selector → resumen → formulario → listado → paginación |
| Consulta plazos | controles → listado → paginación |
| Impresión | filtros/fechas → acciones generar → resultado |
| Configuración | formulario alta → listado cajas |
| Navbar | marca → menú (compacto) → usuario / configuración / salir |

**Validation Rules**:
- No se reordenan bloques entre dispositivos.
- Mensajes de error van junto al bloque que los origina, sin cubrir acciones primarias.

## Entity: Fila de Listado

**Description**: Un registro de tabla. En desktop es una fila; en móvil es un bloque apilado.

**Fields** (presentación):
- `campos[]` — pares `{ etiqueta, valor }` en el **mismo orden que las columnas PC**
- `acciones[]` — Editar / Eliminar si aplican; van **después** de los campos
- `estado_visual` — p. ej. vencido (plazos), entrada/salida (color de monto)

**Validation Rules**:
- Ningún campo de la fila PC puede omitirse en móvil (salvo columna Acciones si no hay callbacks).
- `etiqueta` = texto del `<th>` correspondiente.
- Textos largos (`descripcion` y equivalentes) se muestran completos (wrap); no truncar.

**State Transitions**:
- Ninguna. Es la misma entidad de negocio (`Movimiento`, `PlazoFijo`, `Caja`) ya definida en features previas.

## Entity: Elemento de Dato Financiero Visible

**Description**: Dato crítico de caja/plazo que debe permanecer legible sin zoom.

**Campos típicos**:
- Movimiento: Descripción, Monto, Subtotal, Fecha
- Plazo fijo: Monto ingresado, Fecha de vencimiento, Monto a vencimiento
- Caja (configuración): los encabezados actuales de esa tabla

**Validation Rules**:
- Montos con cifra completa visible.
- Color semántico de ingreso/egreso se conserva en el valor de monto.

## Relaciones

```text
Vista de Pantalla 1..n Bloque Funcional
Bloque historial/listado 1..n Fila de Listado
Fila de Listado 1..n Elemento de Dato Financiero Visible
```

## Out of scope (persistencia)

- No hay migraciones.
- No hay nuevos campos en `Movimiento`, `PlazoFijo`, `Caja` ni `Usuario`.
