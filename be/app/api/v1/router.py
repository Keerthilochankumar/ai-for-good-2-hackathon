from fastapi import APIRouter
from app.api.v1 import admin, webhooks, ws, matches

api_router = APIRouter()
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
api_router.include_router(ws.router)
api_router.include_router(matches.router)
