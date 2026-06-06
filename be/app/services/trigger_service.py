import math
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import User, get_compatible_blood_groups, get_compatible_patients_for_donor
from app.models.request import BloodRequest

def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great circle distance between two points on the earth (specified in decimal degrees)"""
    # Convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])

    # Haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    r = 6371 # Radius of earth in kilometers
    return c * r

class TriggerService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def find_eligible_donors_for_request(self, request: BloodRequest, max_distance_km: float = 30.0) -> list[User]:
        """
        Trigger A: A patient needs blood. Find all eligible donors.
        Criteria:
        1. Blood group match (exact match for now, could be expanded to universal donor logic)
        2. is_available is True
        3. last_donation_date is NULL or > 90 days ago
        4. Spatial: Within max_distance_km
        """
        now = datetime.now(timezone.utc)
        ninety_days_ago = now - timedelta(days=90)
        
        # We query all donors with matching blood type and availability
        # For a real scale application, we would use PostGIS for spatial queries,
        # but for this hackathon we filter spatially in memory.
        query = select(User).where(
            User.blood_group.in_(get_compatible_blood_groups(request.blood_group)),
            User.is_available == True
        )
        
        result = await self.db.execute(query)
        potential_donors = result.scalars().all()
        
        eligible_donors = []
        for donor in potential_donors:
            # Check temporal rule (90 days)
            if donor.last_donation_date and donor.last_donation_date > ninety_days_ago:
                continue
                
            # Check spatial rule (distance)
            dist = haversine(request.latitude, request.longitude, donor.latitude, donor.longitude)
            if dist <= max_distance_km:
                eligible_donors.append(donor)
                
        return eligible_donors

    async def find_eligible_requests_for_donor(self, donor: User, max_distance_km: float = 30.0) -> list[BloodRequest]:
        """
        Trigger C: A donor becomes available. Find all open requests they can fulfill.
        Criteria:
        1. last_donation_date is NULL or > 90 days ago (pre-validated usually)
        2. request status is OPEN
        3. Blood group match
        4. Spatial: Within max_distance_km
        """
        now = datetime.now(timezone.utc)
        ninety_days_ago = now - timedelta(days=90)
        
        if donor.last_donation_date and donor.last_donation_date > ninety_days_ago:
            return [] # Donor is not temporally eligible
            
        if not donor.is_available:
            return []
            
        query = select(BloodRequest).where(
            BloodRequest.blood_group.in_(get_compatible_patients_for_donor(donor.blood_group)),
            BloodRequest.status == "OPEN"
        )
        
        result = await self.db.execute(query)
        open_requests = result.scalars().all()
        
        eligible_requests = []
        for req in open_requests:
            dist = haversine(donor.latitude, donor.longitude, req.latitude, req.longitude)
            if dist <= max_distance_km:
                eligible_requests.append(req)
                
        return eligible_requests
