import uuid
import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.deps import get_db
from app.models.match import MatchRequest
from app.models.request import BloodRequest
from app.models.user import User
from app.api.v1.ws import manager

logger = structlog.get_logger()
router = APIRouter(prefix="/matches", tags=["Matches"])

class MatchResponseInput(BaseModel):
    status: str # "ACCEPTED" or "DECLINED"

@router.post("/{match_id}/response")
async def respond_to_match(
    match_id: uuid.UUID,
    payload: MatchResponseInput,
    db: AsyncSession = Depends(get_db)
):
    """
    Called when a donor responds to a request.
    Handles decrementing required units and locking the donor.
    """
    status = payload.status.upper()
    if status not in ["ACCEPTED", "DECLINED"]:
        raise HTTPException(status_code=400, detail="Invalid status. Must be ACCEPTED or DECLINED.")
        
    match_result = await db.execute(select(MatchRequest).where(MatchRequest.id == match_id))
    match = match_result.scalars().first()
    
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
        
    if match.status != "PENDING":
        raise HTTPException(status_code=400, detail=f"Match has already been processed (Current status: {match.status})")

    req_result = await db.execute(select(BloodRequest).where(BloodRequest.id == match.request_id))
    blood_req = req_result.scalars().first()

    donor_result = await db.execute(select(User).where(User.id == match.donor_id))
    donor = donor_result.scalars().first()
    
    match.status = status
    
    if status == "ACCEPTED":
        # Lock donor
        if donor:
            donor.is_available = False
            
        # Update Request needs
        if blood_req and blood_req.units_required > 0:
            blood_req.units_required -= 1
            if blood_req.units_required == 0:
                blood_req.status = "FULFILLED"
                
        # Emit WebSocket event
        await manager.broadcast("DONOR_ACCEPTED", {
            "match_id": str(match.id),
            "request_id": str(blood_req.id) if blood_req else None,
            "donor_name": donor.name if donor else "Unknown",
            "units_remaining": blood_req.units_required if blood_req else 0
        })
        logger.info(f"Donor {donor.id} ACCEPTED request {blood_req.id}")
        
    elif status == "DECLINED":
        await manager.broadcast("DONOR_DECLINED", {
            "match_id": str(match.id),
            "request_id": str(blood_req.id) if blood_req else None,
            "donor_name": donor.name if donor else "Unknown"
        })
        logger.info(f"Donor {donor.id} DECLINED request {blood_req.id}")
        
    await db.commit()
    return {"message": "Response recorded successfully", "match_status": status}
