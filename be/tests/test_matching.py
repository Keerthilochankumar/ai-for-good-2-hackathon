import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.ilp_service import ILPMatchingService
from app.models.user import User
from app.models.request import BloodRequest, UrgencyLevel
import uuid

@pytest.mark.asyncio
@patch("httpx.AsyncClient.post")
async def test_ilp_matching_logic(mock_post):
    # Mock DB session
    mock_db = AsyncMock()
    
    # Initialize Service
    service = ILPMatchingService(mock_db)
    
    # Mock HTTP response so it always approves
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "content": [{"text": '{"is_valid": true, "reason": "Test match"}'}]
    }
    mock_post.return_value = mock_response

    # Create dummy request
    req1 = BloodRequest(
        id=uuid.uuid4(),
        blood_group="A Positive",
        latitude=40.7128,
        longitude=-74.0060,
        urgency=UrgencyLevel.CRITICAL,
        gender="Male",
        expected_next_transfusion_date=None
    )
    
    # Create matching donor (close, same blood type)
    donor1 = User(
        id=uuid.uuid4(),
        blood_group="A Positive",
        latitude=40.7130,
        longitude=-74.0065,
        donor_type="Regular",
        gender="Male",
        eligibility_status="Eligible",
        account_status="Active",
        donations_till_date=5,
        last_contacted_date=None
    )
    
    # Create non-matching donor (different blood type)
    donor2 = User(
        id=uuid.uuid4(),
        blood_group="B Positive",
        latitude=40.7128,
        longitude=-74.0060,
        donor_type="Regular",
        gender="Male",
        eligibility_status="Eligible",
        account_status="Active",
        donations_till_date=2,
        last_contacted_date=None
    )

    requests = [req1]
    donors = [donor1, donor2]

    matches = await service.optimize_batch(requests, donors)
    
    # We expect 1 match (req1 -> donor1)
    assert len(matches) == 1
    
    matched_req, matched_donor, dist, reason = matches[0]
    
    assert matched_req.id == req1.id
    assert matched_donor.id == donor1.id
    assert reason == "Test match"
    
@pytest.mark.asyncio
@patch("httpx.AsyncClient.post")
async def test_llm_validation_rejection(mock_post):
    # Mock DB session
    mock_db = AsyncMock()
    
    # Initialize Service
    service = ILPMatchingService(mock_db)
    
    # Mock HTTP response so it REJECTS
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "content": [{"text": '{"is_valid": false, "reason": "Donor recently contacted"}'}]
    }
    mock_post.return_value = mock_response

    req1 = BloodRequest(
        id=uuid.uuid4(),
        blood_group="O Positive",
        latitude=40.7128,
        longitude=-74.0060,
        urgency=UrgencyLevel.URGENT,
        gender="Female",
        expected_next_transfusion_date=None
    )
    
    donor1 = User(
        id=uuid.uuid4(),
        blood_group="O Positive",
        latitude=40.7130,
        longitude=-74.0065,
        donor_type="First Time",
        gender="Female",
        eligibility_status="Eligible",
        account_status="Active",
        donations_till_date=0,
        last_contacted_date=None
    )

    requests = [req1]
    donors = [donor1]

    matches = await service.optimize_batch(requests, donors)
    
    # We expect 0 matches because the LLM rejected it
    assert len(matches) == 0
