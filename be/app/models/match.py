import uuid
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.core.database import Base
from app.models.user import User
from app.models.request import BloodRequest

class MatchRequest(Base):
    __tablename__ = "match_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Relationships
    request_id = Column(UUID(as_uuid=True), ForeignKey("blood_requests.id"), index=True, nullable=False)
    donor_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), index=True, nullable=False)
    
    # State Machine
    # PENDING -> ACCEPTED / DECLINED / EXPIRED
    status = Column(String, default="PENDING", index=True)
    
    # Expiration for response loops
    expires_at = Column(DateTime(timezone=True), index=True)
    
    # ILP Output / Metrics
    distance_km = Column(Float, nullable=False)
    ilp_cost_score = Column(Float, nullable=False)
    
    # Audit
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
