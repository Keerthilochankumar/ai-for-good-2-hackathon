import uuid
from sqlalchemy import Column, String, Float, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.core.database import Base

class HospitalBridge(Base):
    __tablename__ = "hospital_bridges"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Details
    name = Column(String, nullable=False)
    contact_phone = Column(String, nullable=False)
    
    # Location
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    
    # Audit
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
