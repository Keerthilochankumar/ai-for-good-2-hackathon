import enum
import uuid
from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.core.database import Base

class BloodGroup(str, enum.Enum):
    A_POS = "A+"
    A_NEG = "A-"
    B_POS = "B+"
    B_NEG = "B-"
    AB_POS = "AB+"
    AB_NEG = "AB-"
    O_POS = "O+"
    O_NEG = "O-"

def get_compatible_blood_groups(patient_bg: BloodGroup) -> list[BloodGroup]:
    return {
        BloodGroup.O_POS: [BloodGroup.O_POS, BloodGroup.O_NEG],
        BloodGroup.O_NEG: [BloodGroup.O_NEG],
        BloodGroup.A_POS: [BloodGroup.O_POS, BloodGroup.O_NEG, BloodGroup.A_POS, BloodGroup.A_NEG],
        BloodGroup.A_NEG: [BloodGroup.O_NEG, BloodGroup.A_NEG],
        BloodGroup.B_POS: [BloodGroup.O_POS, BloodGroup.O_NEG, BloodGroup.B_POS, BloodGroup.B_NEG],
        BloodGroup.B_NEG: [BloodGroup.O_NEG, BloodGroup.B_NEG],
        BloodGroup.AB_POS: [BloodGroup.O_POS, BloodGroup.O_NEG, BloodGroup.A_POS, BloodGroup.A_NEG, BloodGroup.B_POS, BloodGroup.B_NEG, BloodGroup.AB_POS, BloodGroup.AB_NEG],
        BloodGroup.AB_NEG: [BloodGroup.O_NEG, BloodGroup.A_NEG, BloodGroup.B_NEG, BloodGroup.AB_NEG]
    }.get(patient_bg, [patient_bg])

def get_compatible_patients_for_donor(donor_bg: BloodGroup) -> list[BloodGroup]:
    reverse_map = {bg: [] for bg in BloodGroup}
    for patient_bg in BloodGroup:
        for comp_donor_bg in get_compatible_blood_groups(patient_bg):
            if patient_bg not in reverse_map[comp_donor_bg]:
                reverse_map[comp_donor_bg].append(patient_bg)
    return reverse_map.get(donor_bg, [donor_bg])

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    clerk_id = Column(String, unique=True, index=True, nullable=True) # Open for now
    
    # Core demographic
    name = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    
    # Medical profile
    blood_group = Column(Enum(BloodGroup), index=True, nullable=False)
    
    # Location (Spatial)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    
    # Status (Temporal/Availability)
    last_donation_date = Column(DateTime(timezone=True), nullable=True)
    is_available = Column(Boolean, default=True) # Can manually toggle off
    
    # Extended CSV Fields
    external_id = Column(String, unique=True, index=True, nullable=True) # Maps to user_id in CSV
    gender = Column(String, nullable=True)
    registration_date = Column(DateTime(timezone=True), nullable=True)
    donor_type = Column(String, nullable=True)
    last_contacted_date = Column(DateTime(timezone=True), nullable=True)
    next_eligible_date = Column(DateTime(timezone=True), nullable=True)
    donations_till_date = Column(Integer, nullable=True)
    eligibility_status = Column(String, nullable=True)
    cycle_of_donations = Column(Integer, nullable=True)
    total_calls = Column(Integer, nullable=True)
    frequency_in_days = Column(Integer, nullable=True)
    account_status = Column(String, nullable=True) # maps to "status" in CSV
    donated_earlier = Column(Boolean, nullable=True)
    calls_to_donations_ratio = Column(Float, nullable=True)
    user_donation_active_status = Column(String, nullable=True)
    inactive_trigger_comment = Column(String, nullable=True)

    # Audit
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
