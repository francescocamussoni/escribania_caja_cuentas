"""Initial caja seed only — not a closed operational list.

`seed_cajas` / `bootstrap_production` insert these 15 rows as `activa` if missing.
Later altas go through `caja_service.create_caja` (secretaria); do not add names here.
Archived cajas remain in the database and are excluded from operational selectors.
"""

CAJAS_CATALOG: list[dict[str, str]] = [
    {"nombre": "Bambina", "slug": "bambina"},
    {"nombre": "Ebel", "slug": "ebel"},
    {"nombre": "Martin", "slug": "martin"},
    {"nombre": "Gimnasio", "slug": "gimnasio"},
    {"nombre": "Gabriel", "slug": "gabriel"},
    {"nombre": "Costanza", "slug": "costanza"},
    {"nombre": "Guille", "slug": "guille"},
    {"nombre": "Intimayu", "slug": "intimayu"},
    {"nombre": "Amelia", "slug": "amelia"},
    {"nombre": "Entre Rios", "slug": "entre-rios"},
    {"nombre": "Chovet", "slug": "chovet"},
    {"nombre": "Maria Teresa", "slug": "maria-teresa"},
    {"nombre": "Barat Hermanos", "slug": "barat-hermanos"},
    {"nombre": "General Lagos", "slug": "general-lagos"},
    {"nombre": "Fideicomiso", "slug": "fideicomiso"},
]
