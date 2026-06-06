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
            
        from app.api.v1.ws import manager
        
        # Emit MATCH_EVALUATING for each open request so frontend shows 'Pipeline Running'
        for req in open_requests:
            await manager.broadcast("MATCH_EVALUATING", {
                "request_id": str(req.id),
                "status": "Running ILP for donor matching"
            })
            
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
        
        # Sort matches by distance (assuming dist is ILP cost)
        matches.sort(key=lambda x: x[2]) # x[2] is dist
        
        # Keep track of which requests we have already notified
        notified_requests = set()
        
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
        await session.flush() # flush to get match IDs
        
        # Now trigger notification for top donor per request
        for match in new_match_requests:
            if match.request_id not in notified_requests:
                notified_requests.add(match.request_id)
                
                # We need the donor and request objects. They are already in session/memory.
                # Find corresponding original tuple for notification details
                top_tuple = next(m for m in matches if m[0].id == match.request_id and m[1].id == match.donor_id)
                top_req, top_donor, top_dist, top_reason = top_tuple
                
                from app.services.donor_bot import notify_donor_via_telegram
                await notify_donor_via_telegram(
                    match_id=str(match.id),
                    donor_name=top_donor.name,
                    patient_name=top_req.patient_name,
                    hospital_name=top_req.hospital_name,
                    distance_km=top_dist,
                    reason=top_reason
                )
        
        await session.commit()
        
        logger.info(f"Successfully created {len(new_match_requests)} matches.")
        return f"Created {len(new_match_requests)} matches."

import uuid
async def run_ilp_single_async(request_id: uuid.UUID):
    """Async implementation of ILP matching for a specific request"""
    logger.info(f"Starting ILP matching for request {request_id}")
    
    async with AsyncSessionLocal() as session:
        ilp_service = ILPMatchingService(session)
        
        req_result = await session.execute(select(BloodRequest).where(BloodRequest.id == request_id, BloodRequest.status == "OPEN"))
        req = req_result.scalars().first()
        
        if not req:
            logger.info("Request not found or not OPEN.")
            return "Request not open."
            
        compatible_groups = get_compatible_blood_groups(req.blood_group)
        donor_result = await session.execute(
            select(User).where(User.is_available == True, User.blood_group.in_(compatible_groups))
        )
        available_donors = list(donor_result.scalars().all())
        
        if not available_donors:
            logger.info("No available donors for the request.")
            return "No available donors."
            
        from app.api.v1.ws import manager
        await manager.broadcast("MATCH_EVALUATING", {
            "request_id": str(req.id),
            "status": "Running ILP for donor matching"
        })
        
        matches = await ilp_service.get_top_matches_for_patient(req, available_donors, limit=5)
        
        if not matches:
            logger.info("ILP solver found no feasible matches.")
            return "No matches found."
            
        new_match_requests = []
        from datetime import datetime, timezone, timedelta
        now = datetime.now(timezone.utc)
        
        # Sort matches by distance (assuming dist is ILP cost)
        matches.sort(key=lambda x: x[1])
        
        for idx, (donor, dist, reason) in enumerate(matches):
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
                ilp_cost_score=dist,
                expires_at=now + delta
            )
            new_match_requests.append(match)
            req.status = "MATCHING"
            
            await manager.broadcast("MATCH_FOUND", {
                "request_id": str(req.id),
                "donor_id": str(donor.id),
                "distance_km": dist,
                "reason": reason
            })
            
        session.add_all(new_match_requests)
        await session.commit()
        
        # Only notify the top 1 donor initially to start the waterfall loop
        if new_match_requests:
            top_match = new_match_requests[0]
            top_donor = matches[0][0]
            top_reason = matches[0][2]
            
            from app.services.donor_bot import notify_donor_via_telegram
            await notify_donor_via_telegram(
                match_id=str(top_match.id),
                donor_name=top_donor.name,
                patient_name=req.patient_name,
                hospital_name=req.hospital_name,
                distance_km=top_match.distance_km,
                reason=top_reason
            )
        
        logger.info(f"Successfully created {len(new_match_requests)} matches for request {request_id}.")
        return f"Created matches for {request_id}."

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
