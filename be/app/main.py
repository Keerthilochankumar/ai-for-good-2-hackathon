from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.core.config import settings
from app.api.v1.router import api_router
from app.core.database import engine, Base
from app.api.v1 import donors, patients

from app.models import user, request

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Setup actions (if any) could go here
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Cleanup
    await engine.dispose()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan
)

# Include API v1 routers
app.include_router(api_router, prefix="/api/v1")
app.include_router(donors.router, prefix="/api/v1")
app.include_router(patients.router, prefix="/api/v1")

@app.get("/health")
async def health_check():
    return {"status": "ok", "project": settings.PROJECT_NAME}
