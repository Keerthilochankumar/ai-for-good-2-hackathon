import pytest
from unittest.mock import MagicMock, patch
from app.services.nlu_service import NLUService

@pytest.mark.asyncio
@patch("httpx.AsyncClient.post")
async def test_nlu_service_parsing(mock_post):
    service = NLUService()
    
    # Mock HTTP response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "content": [{"text": '{"intent": "decline", "reason": "illness", "suggested_reschedule_days": 7, "confidence": 0.95}'}]
    }
    mock_post.return_value = mock_response

    result = await service.parse_donor_reply("I'm sick this week, can't make it")
    
    assert result.intent == "decline"
    assert result.reason == "illness"
    assert result.suggested_reschedule_days == 7
    assert result.confidence == 0.95
