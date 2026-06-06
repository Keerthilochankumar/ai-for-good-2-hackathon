import asyncio
import structlog
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.core.celery_app import celery_app
from app.core.database import AsyncSessionLocal
from app.services.ilp_service import ILPMatchingService
from app.models.request import BloodRequest
from app.models.user import User, get_compatible_blood_groups
from app.models.match import MatchRequest
from app.api.v1.ws import manager

logger = structlog.get_logger()

async def process_match_timeouts_async():
    logger.info("Starting orchestration loop for expired match requests.")
    now = datetime.now(timezone.utc)
    
    async with AsyncSessionLocal() as session:
        # 1. Find expired PENDING matches
        query = select(MatchRequest).where(
            MatchRequest.status == "PENDING",
            MatchRequest.expires_at < now
        )
        result = await session.execute(query)
        expired_matches = list(result.scalars().all())
        
        if not expired_matches:
            logger.info("No expired matches found.")
            return "No expired matches."
            
        requests_to_reprocess = set()
        
        for match in expired_matches:
            match.status = "EXPIRED"
            requests_to_reprocess.add(match.request_id)
            logger.info(f"Match {match.id} EXPIRED. Donor {match.donor_id} failed to respond.")
            
            # Broadcast timeout event
            await manager.broadcast("MATCH_EXPIRED", {
                "match_id": str(match.id),
                "request_id": str(match.request_id),
                "donor_id": str(match.donor_id)
            })
            
        await session.commit()
        
        # 2. For each request that had an expiration, check if we still need more units
        ilp_service = ILPMatchingService(session)
        for req_id in requests_to_reprocess:
            req_result = await session.execute(select(BloodRequest).where(BloodRequest.id == req_id))
            blood_req = req_result.scalars().first()
            
            if not blood_req or blood_req.units_required <= 0 or blood_req.status == "FULFILLED":
                continue
                
            # Need more donors. Fetch available donors excluding ones already contacted for this request
            # Get already contacted
            contacted_query = select(MatchRequest.donor_id).where(MatchRequest.request_id == req_id)
            contacted_result = await session.execute(contacted_query)
            contacted_ids = [row[0] for row in contacted_result.all()]
            
            compatible_blood_groups = get_compatible_blood_groups(blood_req.blood_group)
            
            donor_query = select(User).where(
                User.is_available == True,
                User.blood_group.in_(list(compatible_blood_groups)),
                User.id.not_in(contacted_ids) if contacted_ids else True
            )
            donor_result = await session.execute(donor_query)
            available_donors = list(donor_result.scalars().all())
            
            if not available_donors:
                logger.warning(f"No more available donors for Request {req_id}!")
                continue
                
            # Batch size of 2 as requested by user
            logger.info(f"ILP fetching next best 2 donors for Request {req_id}")
            matches = await ilp_service.optimize_batch([blood_req], available_donors, limit=2)
            
            # Create new match requests
            for req, donor, dist, reason in matches:
                # Calculate expiration
                from datetime import timedelta
                delta = timedelta(days=4)
                if req.urgency.value == "CRITICAL":
                    delta = timedelta(days=1)
                elif req.urgency.value == "URGENT":
                    delta = timedelta(days=2)
                    
                match = MatchRequest(
                    request_id=req.id,
                    donor_id=donor.id,
                    status="PENDING",
                    distance_km=dist,
                    ilp_cost_score=dist,
                    expires_at=now + delta
                )
                session.add(match)
                
                await manager.broadcast("MATCH_FOUND", {
                    "request_id": str(req.id),
                    "donor_id": str(donor.id),
                    "distance_km": dist,
                    "reason": reason
                })
                
        await session.commit()
        return f"Processed {len(expired_matches)} expirations."


@celery_app.task(name="app.tasks.orchestration_tasks.process_match_timeouts")
def process_match_timeouts():
    loop = asyncio.get_event_loop()
    if loop.is_closed():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(process_match_timeouts_async())
