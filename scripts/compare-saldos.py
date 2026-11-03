#!/usr/bin/env python3
"""Read-only: compare the old balance (subtotal of the latest row) with the new one (signed SUM).

Run it against a COPY of production BEFORE migrating (it works on the pre-010 schema) and again
after the deploy. Any row printed with DIFF means the "Valor de caja" shown to users changes.

Usage (from backend/, with the venv active; the URL is read from the environment, never printed):
    DATABASE_URL=postgresql://... python ../scripts/compare-saldos.py
"""

import os
import sys

from sqlalchemy import create_engine, text

QUERY = """
WITH old AS (
    SELECT DISTINCT ON (caja_id, moneda) caja_id, moneda, subtotal AS saldo_viejo
    FROM movimiento
    WHERE subtotal IS NOT NULL
    ORDER BY caja_id, moneda, COALESCE(fecha_override, created_at) DESC, id DESC
),
new AS (
    SELECT caja_id, moneda,
           SUM(CASE WHEN tipo = 'entrada' THEN monto ELSE -monto END) AS saldo_nuevo
    FROM movimiento
    GROUP BY caja_id, moneda
)
SELECT c.nombre, old.moneda, old.saldo_viejo, new.saldo_nuevo
FROM old JOIN new USING (caja_id, moneda) JOIN caja c ON c.id = old.caja_id
ORDER BY c.nombre, old.moneda
"""


def main() -> int:
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("Set DATABASE_URL", file=sys.stderr)
        return 2
    engine = create_engine(url)
    diffs = 0
    with engine.connect() as conn:
        conn.execute(text("SET TRANSACTION READ ONLY"))
        for nombre, moneda, viejo, nuevo in conn.execute(text(QUERY)):
            flag = "OK  " if viejo == nuevo else "DIFF"
            diffs += flag == "DIFF"
            print(f"{flag} {nombre:<20} {moneda} viejo={viejo} nuevo={nuevo}")
    print(f"\n{diffs} diferencia(s)")
    return 1 if diffs else 0


if __name__ == "__main__":
    sys.exit(main())
