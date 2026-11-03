from fastapi import APIRouter

from app.api.routes import auth, cajas, cheques, informes, movimientos, plazos_fijos

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(cajas.router, prefix="/cajas", tags=["cajas"])
api_router.include_router(movimientos.router, prefix="/cajas", tags=["movimientos"])
api_router.include_router(plazos_fijos.router, prefix="/cajas", tags=["plazos-fijos"])
api_router.include_router(cheques.router, prefix="/cheques", tags=["cheques"])
api_router.include_router(informes.router, prefix="/informes", tags=["informes"])
