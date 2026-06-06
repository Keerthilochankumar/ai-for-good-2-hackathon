from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import get_db
from app.models.user import User
from app.models.request import BloodRequest

router = APIRouter()

from typing import Optional

@router.get("/stats")
async def get_dashboard_stats(blood_group: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    # Total donors
    donor_query = select(func.count(User.id))
    if blood_group and blood_group != 'ALL':
        donor_query = donor_query.where(User.blood_group == blood_group)
    donors_result = await db.execute(donor_query)
    total_donors = donors_result.scalar() or 0

    # Total requests
    req_query = select(func.count(BloodRequest.id))
    if blood_group and blood_group != 'ALL':
        req_query = req_query.where(BloodRequest.blood_group == blood_group)
    requests_result = await db.execute(req_query)
    total_requests = requests_result.scalar() or 0

    # Fulfilled requests
    ful_query = select(func.count(BloodRequest.id)).where(BloodRequest.status == "FULFILLED")
    if blood_group and blood_group != 'ALL':
        ful_query = ful_query.where(BloodRequest.blood_group == blood_group)
    fulfilled_result = await db.execute(ful_query)
    fulfilled_requests = fulfilled_result.scalar() or 0

    # Blood group counts (for donors) - ALWAYS GLOBAL so buttons don't disappear
    bg_result = await db.execute(select(User.blood_group, func.count(User.id)).group_by(User.blood_group))
    bg_counts = {row[0]: row[1] for row in bg_result.all()}

    success_rate = round((fulfilled_requests / total_requests) * 100) if total_requests > 0 else 0
    ratio = round((total_donors / total_requests), 1) if total_requests > 0 else 0

    return {
        "totalDonors": total_donors,
        "totalPatients": total_requests,
        "successRate": success_rate,
        "ratio": ratio,
        "bgCounts": bg_counts
    }
