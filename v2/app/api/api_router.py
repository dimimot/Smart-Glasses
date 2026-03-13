from fastapi import APIRouter
from v2.app.api.routers import core, mobile

api_router = APIRouter()

api_router.include_router(core.router, tags=["core"])
api_router.include_router(mobile.router, prefix="/mobile", tags=["mobile"])
