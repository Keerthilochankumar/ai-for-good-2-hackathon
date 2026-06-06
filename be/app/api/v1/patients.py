from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from pydantic import BaseModel
import uuid
import httpx
import asyncio
from datetime import datetime, timezone, timedelta

from app.core.database import get_db
from app.models.request import BloodRequest, UrgencyLevel
from app.models.user import User, BloodGroup, get_compatible_blood_groups
from app.services.ilp_service import ILPMatchingService

router = APIRouter(prefix="/patients", tags=["Patients"])

class PatientCreate(BaseModel):
    name: str
    blood_group: str
    latitude: float
    longitude: float
    urgency: str
    units: int = 1
    hospital: str

    # Extended CSV Fields
    external_id: Optional[str] = None
    gender: Optional[str] = None
    bridge_id: Optional[str] = None
    role_status: Optional[bool] = None
    bridge_status: Optional[bool] = None
    bridge_gender: Optional[str] = None
    bridge_blood_group: Optional[str] = None
    last_transfusion_date: Optional[datetime] = None
    expected_next_transfusion_date: Optional[datetime] = None
    status_of_bridge: Optional[bool] = None
    last_bridge_donation_date: Optional[datetime] = None

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Bob Jones",
                "blood_group": "A+",
                "latitude": 40.7138,
                "longitude": -74.0070,
                "urgency": "CRITICAL",
                "units": 2,
                "hospital": "Central Hospital"
            }
        }

class PatientUpdate(BaseModel):
    name: Optional[str] = None
    blood_group: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    urgency: Optional[str] = None
    units: Optional[int] = None
    hospital: Optional[str] = None
    status: Optional[str] = None

    # Extended CSV Fields
    external_id: Optional[str] = None
    gender: Optional[str] = None
    bridge_id: Optional[str] = None
    role_status: Optional[bool] = None
    bridge_status: Optional[bool] = None
    bridge_gender: Optional[str] = None
    bridge_blood_group: Optional[str] = None
    last_transfusion_date: Optional[datetime] = None
    expected_next_transfusion_date: Optional[datetime] = None
    status_of_bridge: Optional[bool] = None
    last_bridge_donation_date: Optional[datetime] = None

    class Config:
        json_schema_extra = {
            "example": {
                "status": "FULFILLED",
                "units": 3
            }
        }

class PatientResponse(BaseModel):
    id: uuid.UUID
    patient_name: str
    blood_group: str
    latitude: float
    longitude: float
    urgency: str
    units_required: int
    hospital_name: str
    status: str

    # Extended CSV Fields
    external_id: Optional[str]
    gender: Optional[str]
    bridge_id: Optional[str]
    role_status: Optional[bool]
    bridge_status: Optional[bool]
    bridge_gender: Optional[str]
    bridge_blood_group: Optional[str]
    last_transfusion_date: Optional[datetime]
    expected_next_transfusion_date: Optional[datetime]
    status_of_bridge: Optional[bool]
    last_bridge_donation_date: Optional[datetime]

    class Config:
        from_attributes = True

class MatchResponse(BaseModel):
    donor_id: uuid.UUID
    donor_name: str
    donor_phone: str
    blood_group: str
    distance_km: float
    llm_reasoning: Optional[str] = None

@router.post("/", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
async def create_patient(patient_in: PatientCreate, db: AsyncSession = Depends(get_db)):
    bg_map = {
        "A+": BloodGroup.A_POS, "A-": BloodGroup.A_NEG,
        "B+": BloodGroup.B_POS, "B-": BloodGroup.B_NEG,
        "AB+": BloodGroup.AB_POS, "AB-": BloodGroup.AB_NEG,
        "O+": BloodGroup.O_POS, "O-": BloodGroup.O_NEG,
    }
    bg = bg_map.get(patient_in.blood_group.replace(" ", "").upper())
    if not bg:
        raise HTTPException(status_code=400, detail="Invalid blood group")

    urgency_raw = patient_in.urgency.strip().upper()
    urgency = UrgencyLevel.ROUTINE
    if urgency_raw in ["URGENT", "CRITICAL"]:
        urgency = UrgencyLevel(urgency_raw)

    now = datetime.now(timezone.utc)
    deadline = now + timedelta(days=7) # default ROUTINE
    if urgency == UrgencyLevel.CRITICAL:
        deadline = now + timedelta(hours=24)
    elif urgency == UrgencyLevel.URGENT:
        deadline = now + timedelta(days=3)

    req = BloodRequest(
        patient_name=patient_in.name,
        blood_group=bg,
        units_required=patient_in.units,
        hospital_name=patient_in.hospital,
        latitude=patient_in.latitude,
        longitude=patient_in.longitude,
        urgency=urgency,
        deadline=deadline,
        status="OPEN"
    )
    db.add(req)
    await db.commit()
    await db.refresh(req)
    return req

@router.put("/{patient_id}", response_model=PatientResponse)
async def update_patient(patient_id: uuid.UUID, patient_in: PatientUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BloodRequest).where(BloodRequest.id == patient_id))
    req = result.scalars().first()
    if not req:
        raise HTTPException(status_code=404, detail="Patient/Request not found")

    if patient_in.name is not None:
        req.patient_name = patient_in.name
    if patient_in.blood_group is not None:
        bg_map = {
            "A+": BloodGroup.A_POS, "A-": BloodGroup.A_NEG,
            "B+": BloodGroup.B_POS, "B-": BloodGroup.B_NEG,
            "AB+": BloodGroup.AB_POS, "AB-": BloodGroup.AB_NEG,
            "O+": BloodGroup.O_POS, "O-": BloodGroup.O_NEG,
        }
        bg = bg_map.get(patient_in.blood_group.replace(" ", "").upper())
        if not bg:
            raise HTTPException(status_code=400, detail="Invalid blood group")
        req.blood_group = bg
    if patient_in.latitude is not None:
        req.latitude = patient_in.latitude
    if patient_in.longitude is not None:
        req.longitude = patient_in.longitude
    if patient_in.units is not None:
        req.units_required = patient_in.units
    if patient_in.hospital is not None:
        req.hospital_name = patient_in.hospital
    if patient_in.status is not None:
        req.status = patient_in.status
    if patient_in.urgency is not None:
        urgency_raw = patient_in.urgency.strip().upper()
        if urgency_raw in ["ROUTINE", "URGENT", "CRITICAL"]:
            req.urgency = UrgencyLevel(urgency_raw)

    await db.commit()
    await db.refresh(req)
    return req

@router.get("/{patient_id}/matches", response_model=List[MatchResponse])
async def get_patient_matches(patient_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    # Fetch patient request
    result = await db.execute(select(BloodRequest).where(BloodRequest.id == patient_id))
    req = result.scalars().first()
    if not req:
        raise HTTPException(status_code=404, detail="Patient/Request not found")
        
    # Fetch eligible donors
    donor_result = await db.execute(
        select(User).where(
            User.blood_group.in_(get_compatible_blood_groups(req.blood_group)) & 
            (User.is_available == True)
        )
    )
    donors = donor_result.scalars().all()
    
    # Use the ILP Service scoring logic
    ilp_service = ILPMatchingService(db)
    top_matches = await ilp_service.get_top_matches_for_patient(req, list(donors), limit=10)
    
    async def fetch_driving_distance(donor, fallback_dist):
        url = f"http://router.project-osrm.org/route/v1/driving/{req.longitude},{req.latitude};{donor.longitude},{donor.latitude}?overview=false"
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(url, timeout=2.0)
                data = resp.json()
                if data.get("code") == "Ok":
                    return data["routes"][0]["distance"] / 1000.0
            except Exception:
                pass
        return fallback_dist

    # Fetch driving distances concurrently to avoid slow response times
    tasks = [fetch_driving_distance(donor, dist) for donor, dist, _ in top_matches]
    driving_distances = await asyncio.gather(*tasks)
    
    response = []
    for (donor, _, reason), driving_dist in zip(top_matches, driving_distances):
        response.append(MatchResponse(
            donor_id=donor.id,
            donor_name=donor.name,
            donor_phone=donor.phone,
            blood_group=donor.blood_group.value,
            distance_km=round(driving_dist, 2),
            llm_reasoning=reason
        ))
        
    return response
