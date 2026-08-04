from fastapi import APIRouter

from app.api.routes import auth, cajas, movimientos

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(cajas.router, prefix="/cajas", tags=["cajas"])
api_router.include_router(movimientos.router, prefix="/cajas", tags=["movimientos"])
