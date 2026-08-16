# Contracts — 007-responsive-mobile

## API HTTP

**Sin cambios.** Esta feature no agrega, modifica ni depreca endpoints. El contrato OpenAPI vigente del repositorio (`swagger/openapi.yaml` o el generado por `/spec-kitti.swagger`) permanece autoritativo.

El archivo [openapi.yaml](./openapi.yaml) de esta feature declara explícitamente `paths: {}` para que herramientas de plan no asuman superficie nueva.

## Contrato de presentación

El comportamiento móvil se especifica en [ui-presentation.yaml](./ui-presentation.yaml):

- Breakpoint y media type (`screen`)
- Orden de campos por listado
- Paridad de destinos de navegación por rol
- Prohibición de recorte de texto y de scroll horizontal de página
