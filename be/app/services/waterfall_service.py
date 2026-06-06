import uuid
import structlog
from app.core.database import AsyncSessionLocal
from sqlalchemy import select, and_, or_
from app.models.match import MatchRequest
from app.models.request import BloodRequest
from app.models.user import User

logger = structlog.get_logger()

async def trigger_next_donor(request_id: uuid.UUID):
    """
    Finds the next PENDING match for a given request, based on ILP rank,
    and triggers a Telegram notification to that donor.
    """
    async with AsyncSessionLocal() as session:
        # Find all matches for this request
        query = select(MatchRequest, User, BloodRequest).join(
            User, MatchRequest.donor_id == User.id
        ).join(
            BloodRequest, MatchRequest.request_id == BloodRequest.id
        ).where(
            MatchRequest.request_id == request_id,
            MatchRequest.status == "PENDING"
        ).order_by(MatchRequest.ilp_cost_score.asc())
        
        result = await session.execute(query)
        matches = result.all()
        
        if not matches:
            logger.info(f"No more PENDING donors available for request {request_id}.")
            return False
            
        next_match, donor, blood_req = matches[0]
        
        # Notify this donor
        from app.services.donor_bot import notify_donor_via_telegram
        
        logger.info(f"Triggering next donor in waterfall for request {request_id}: Donor {donor.name}")
        await notify_donor_via_telegram(
            match_id=str(next_match.id),
            donor_name=donor.name,
            patient_name=blood_req.patient_name,
            hospital_name=blood_req.hospital_name,
            distance_km=next_match.distance_km,
            reason="You are the next best match in our system."
        )
        return True
