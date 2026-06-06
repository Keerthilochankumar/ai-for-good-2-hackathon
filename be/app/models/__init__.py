from app.models.user import User, BloodGroup
from app.models.request import BloodRequest, UrgencyLevel
from app.models.match import MatchRequest
from app.models.bridge import HospitalBridge

# This is so Alembic can discover the models when we import them in env.py
__all__ = [
    "User",
    "BloodGroup",
    "BloodRequest",
    "UrgencyLevel",
    "MatchRequest",
    "HospitalBridge"
]
