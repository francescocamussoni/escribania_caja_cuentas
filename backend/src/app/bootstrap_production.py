"""Production bootstrap: initial catalog cajas + admin user from secure env/secrets.

Inserts the 15 seed cajas if missing by slug. Does not freeze the live list;
secretaria altas after bootstrap do not require editing CAJAS_CATALOG.

Does NOT seed development users (escribano) or sample movimientos.
"""

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.seed import seed_admin_user, seed_cajas


def bootstrap_production(db: Session | None = None, *, commit: bool = True) -> None:
    own_session = db is None
    session = db if db is not None else SessionLocal()
    try:
        seed_cajas(session)
        seed_admin_user(session)
        if commit:
            session.commit()
        else:
            session.flush()
    except Exception:
        session.rollback()
        raise
    finally:
        if own_session:
            session.close()


def run_bootstrap_production() -> None:
    bootstrap_production()


if __name__ == "__main__":
    run_bootstrap_production()
