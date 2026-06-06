import asyncio
import structlog
from app.core.celery_app import celery_app
from app.core.database import AsyncSessionLocal
from app.services.ilp_service import ILPMatchingService
from app.models.request import BloodRequest
from app.models.user import User, get_compatible_blood_groups
from app.models.match import MatchRequest
from sqlalchemy import select

logger = structlog.get_logger()

async def run_ilp_batch_async():
    """Async implementation of the ILP batch optimization"""
    logger.info("Starting ILP batch optimization")
    
    async with AsyncSessionLocal() as session:
        ilp_service = ILPMatchingService(session)
        
        # 1. Fetch all OPEN requests
        req_query = select(BloodRequest).where(BloodRequest.status == "OPEN")
        req_result = await session.execute(req_query)
        open_requests = list(req_result.scalars().all())
        
        if not open_requests:
            logger.info("No open requests to process.")
            return "No open requests."
            
        # 2. Fetch all eligible donors (available, no recent donation)
        # Assuming we just fetch all available for simplicity in the batch, 
        # or we could filter by the blood types of the open requests.
        compatible_blood_groups = set()
        for req in open_requests:
            compatible_blood_groups.update(get_compatible_blood_groups(req.blood_group))
        blood_groups = list(compatible_blood_groups)
        
        donor_query = select(User).where(
            User.is_available == True,
            User.blood_group.in_(blood_groups)
        )
        donor_result = await session.execute(donor_query)
        available_donors = list(donor_result.scalars().all())
        
        if not available_donors:
            logger.info("No available donors for the open requests.")
            return "No available donors."
            
        # 3. Run the optimization
        matches = await ilp_service.optimize_batch(open_requests, available_donors)
        
        if not matches:
            logger.info("ILP solver found no feasible matches.")
            return "No matches found."
            
        # 4. Save MatchRequests to DB
        new_match_requests = []
        from datetime import datetime, timezone, timedelta
        now = datetime.now(timezone.utc)
        
        from app.api.v1.ws import manager
        
        for req, donor, dist, reason in matches:
            delta = timedelta(days=4)
            if req.urgency.value == "CRITICAL":
                delta = timedelta(days=2)
            elif req.urgency.value == "URGENT":
                delta = timedelta(days=3)
                
            match = MatchRequest(
                request_id=req.id,
                donor_id=donor.id,
                status="PENDING",
                distance_km=dist,
                ilp_cost_score=dist, # Basic mapping for now
                expires_at=now + delta
            )
            # We could store the LLM reason here if we added a column, 
            # but for now we'll just log it.
            logger.info(f"Match LLM Reason: {reason}")
            
            new_match_requests.append(match)
            # Update request status so it's not matched twice
            req.status = "MATCHING"
            
            # Emit WebSocket event
            await manager.broadcast("MATCH_FOUND", {
                "request_id": str(req.id),
                "donor_id": str(donor.id),
                "distance_km": dist,
                "reason": reason
            })
            
        session.add_all(new_match_requests)
        await session.commit()
        
        logger.info(f"Successfully created {len(new_match_requests)} matches.")
        return f"Created {len(new_match_requests)} matches."


@celery_app.task(name="app.tasks.optimization_tasks.run_ilp_batch_optimization")
def run_ilp_batch_optimization():
    """
    Celery task wrapper to run the async ILP batch.
    Triggered periodically by Celery Beat or manually via CSV import webhook.
    """
    # Create a new event loop for this Celery worker thread
    loop = asyncio.get_event_loop()
    if loop.is_closed():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    result = loop.run_until_complete(run_ilp_batch_async())
    return result
