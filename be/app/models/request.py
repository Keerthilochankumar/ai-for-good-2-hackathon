import enum
import uuid
from sqlalchemy import Column, String, Float, Integer, DateTime, Enum, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.core.database import Base
from app.models.user import BloodGroup

class UrgencyLevel(str, enum.Enum):
    ROUTINE = "ROUTINE"
    URGENT = "URGENT"
    CRITICAL = "CRITICAL" # e.g. bleeding

class BloodRequest(Base):
    __tablename__ = "blood_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Patient Info
    patient_name = Column(String, nullable=False)
    blood_group = Column(Enum(BloodGroup), index=True, nullable=False)
    units_required = Column(Integer, nullable=False)
    
    # Location
    hospital_name = Column(String, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    
    # Temporal / Urgency
    urgency = Column(Enum(UrgencyLevel), nullable=False)
    deadline = Column(DateTime(timezone=True), nullable=False)
    
    # Status
    status = Column(String, default="OPEN", index=True) # OPEN, MATCHING, FULFILLED, EXPIRED
    
    # Extended CSV Fields
    external_id = Column(String, unique=True, index=True, nullable=True) # maps to user_id
    gender = Column(String, nullable=True)
    bridge_id = Column(String, nullable=True)
    role_status = Column(Boolean, nullable=True)
    bridge_status = Column(Boolean, nullable=True)
    bridge_gender = Column(String, nullable=True)
    bridge_blood_group = Column(String, nullable=True)
    last_transfusion_date = Column(DateTime(timezone=True), nullable=True)
    expected_next_transfusion_date = Column(DateTime(timezone=True), nullable=True)
    status_of_bridge = Column(Boolean, nullable=True)
    last_bridge_donation_date = Column(DateTime(timezone=True), nullable=True)

    # Audit
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
