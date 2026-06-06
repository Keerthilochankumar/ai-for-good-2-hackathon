from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from pydantic import BaseModel
import uuid
from datetime import datetime

from app.core.database import get_db
from app.models.user import User, BloodGroup

router = APIRouter(prefix="/donors", tags=["Donors"])

class DonorCreate(BaseModel):
    name: str
    phone: str
    blood_group: str
    latitude: float
    longitude: float
    
    # Extended CSV Fields
    external_id: Optional[str] = None
    gender: Optional[str] = None
    registration_date: Optional[datetime] = None
    donor_type: Optional[str] = None
    last_contacted_date: Optional[datetime] = None
    next_eligible_date: Optional[datetime] = None
    donations_till_date: Optional[int] = None
    eligibility_status: Optional[str] = None
    cycle_of_donations: Optional[int] = None
    total_calls: Optional[int] = None
    frequency_in_days: Optional[int] = None
    account_status: Optional[str] = None
    donated_earlier: Optional[bool] = None
    calls_to_donations_ratio: Optional[float] = None
    user_donation_active_status: Optional[str] = None
    inactive_trigger_comment: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Alice Smith",
                "phone": "555-0101",
                "blood_group": "A+",
                "latitude": 40.7128,
                "longitude": -74.0060
            }
        }

class DonorUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    blood_group: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    is_available: Optional[bool] = None

    # Extended CSV Fields
    external_id: Optional[str] = None
    gender: Optional[str] = None
    registration_date: Optional[datetime] = None
    donor_type: Optional[str] = None
    last_contacted_date: Optional[datetime] = None
    next_eligible_date: Optional[datetime] = None
    donations_till_date: Optional[int] = None
    eligibility_status: Optional[str] = None
    cycle_of_donations: Optional[int] = None
    total_calls: Optional[int] = None
    frequency_in_days: Optional[int] = None
    account_status: Optional[str] = None
    donated_earlier: Optional[bool] = None
    calls_to_donations_ratio: Optional[float] = None
    user_donation_active_status: Optional[str] = None
    inactive_trigger_comment: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "is_available": False,
                "phone": "555-0202"
            }
        }

class DonorResponse(BaseModel):
    id: uuid.UUID
    name: str
    phone: str
    blood_group: str
    latitude: float
    longitude: float
    is_available: bool

    # Extended CSV Fields
    external_id: Optional[str]
    gender: Optional[str]
    registration_date: Optional[datetime]
    donor_type: Optional[str]
    last_contacted_date: Optional[datetime]
    next_eligible_date: Optional[datetime]
    donations_till_date: Optional[int]
    eligibility_status: Optional[str]
    cycle_of_donations: Optional[int]
    total_calls: Optional[int]
    frequency_in_days: Optional[int]
    account_status: Optional[str]
    donated_earlier: Optional[bool]
    calls_to_donations_ratio: Optional[float]
    user_donation_active_status: Optional[str]
    inactive_trigger_comment: Optional[str]

    class Config:
        from_attributes = True

@router.get("/", response_model=List[DonorResponse])
async def get_donors(
    skip: int = 0,
    limit: int = 100,
    q: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve users/donors for the dashboard with pagination and optional search.
    """
    query = select(User)
    if q:
        search = f"%{q}%"
        query = query.where((User.name.ilike(search)) | (User.phone.ilike(search)))
        
    result = await db.execute(query.offset(skip).limit(limit))
    return result.scalars().all()

@router.post("/", response_model=DonorResponse, status_code=status.HTTP_201_CREATED)
async def create_donor(donor_in: DonorCreate, db: AsyncSession = Depends(get_db)):
    bg_map = {
        "A+": BloodGroup.A_POS, "A-": BloodGroup.A_NEG,
        "B+": BloodGroup.B_POS, "B-": BloodGroup.B_NEG,
        "AB+": BloodGroup.AB_POS, "AB-": BloodGroup.AB_NEG,
        "O+": BloodGroup.O_POS, "O-": BloodGroup.O_NEG,
    }
    bg = bg_map.get(donor_in.blood_group.replace(" ", "").upper())
    if not bg:
        raise HTTPException(status_code=400, detail="Invalid blood group")

    donor = User(
        name=donor_in.name,
        phone=donor_in.phone,
        blood_group=bg,
        latitude=donor_in.latitude,
        longitude=donor_in.longitude,
        is_available=True
    )
    db.add(donor)
    await db.commit()
    await db.refresh(donor)
    return donor

@router.put("/{donor_id}", response_model=DonorResponse)
async def update_donor(donor_id: uuid.UUID, donor_in: DonorUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == donor_id))
    donor = result.scalars().first()
    if not donor:
        raise HTTPException(status_code=404, detail="Donor not found")

    if donor_in.name is not None:
        donor.name = donor_in.name
    if donor_in.phone is not None:
        donor.phone = donor_in.phone
    if donor_in.blood_group is not None:
        bg_map = {
            "A+": BloodGroup.A_POS, "A-": BloodGroup.A_NEG,
            "B+": BloodGroup.B_POS, "B-": BloodGroup.B_NEG,
            "AB+": BloodGroup.AB_POS, "AB-": BloodGroup.AB_NEG,
            "O+": BloodGroup.O_POS, "O-": BloodGroup.O_NEG,
        }
        bg = bg_map.get(donor_in.blood_group.replace(" ", "").upper())
        if not bg:
            raise HTTPException(status_code=400, detail="Invalid blood group")
        donor.blood_group = bg
    if donor_in.latitude is not None:
        donor.latitude = donor_in.latitude
    if donor_in.longitude is not None:
        donor.longitude = donor_in.longitude
    if donor_in.is_available is not None:
        donor.is_available = donor_in.is_available

    await db.commit()
    await db.refresh(donor)
    return donor
