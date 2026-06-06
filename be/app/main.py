from fastapi import FastAPI
import asyncio
from contextlib import asynccontextmanager
from app.core.config import settings
from app.api.v1.router import api_router
from app.core.database import engine, Base
from app.api.v1 import donors, patients
from app.services.patient_bot import start_patient_bot
from app.services.donor_bot import start_donor_bot

from app.models import user, request, match, bridge

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Setup actions (if any) could go here
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    # Start Telegram conversational bots
    patient_bot_task = asyncio.create_task(start_patient_bot())
    donor_bot_task = asyncio.create_task(start_donor_bot())
    
    yield
    # Cleanup
    await engine.dispose()
    patient_bot_task.cancel()
    donor_bot_task.cancel()

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API v1 routers
app.include_router(api_router, prefix="/api/v1")
app.include_router(donors.router, prefix="/api/v1")
app.include_router(patients.router, prefix="/api/v1")

@app.get("/health")
async def health_check():
    return {"status": "ok", "project": settings.PROJECT_NAME}
