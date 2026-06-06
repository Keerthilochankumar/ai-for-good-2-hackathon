from fastapi import APIRouter, Depends, Body, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from app.api.deps import get_db
from app.services.nlu_service import NLUService
from app.models.match import MatchRequest

router = APIRouter()
nlu_service = NLUService()

class TextReplyPayload(BaseModel):
    match_id: str
    reply_text: str

@router.post("/text-reply")
async def process_text_reply(
    payload: TextReplyPayload,
    db: AsyncSession = Depends(get_db)
):
    """
    Process a free-text response from a donor regarding a match request.
    Uses Bedrock NLU to extract intent and updates the DB.
    """
    # 1. Fetch match
    query = select(MatchRequest).where(MatchRequest.id == payload.match_id)
    result = await db.execute(query)
    match = result.scalars().first()
    
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
        
    # 2. Extract intent
    intent_result = await nlu_service.parse_donor_reply(payload.reply_text)
    
    # 3. Handle state transitions
    if intent_result.intent == "accept":
        match.status = "ACCEPTED"
    elif intent_result.intent == "decline":
        match.status = "DECLINED"
    elif intent_result.intent == "reschedule":
        match.status = "RESCHEDULED"
        # In a real app we would update the donor's availability here based on suggested_reschedule_days
    else:
        # UNCLEAR — flag for manual review
        match.status = "NEEDS_REVIEW"
        
    await db.commit()
    
    return {
        "status": "success",
        "parsed_intent": intent_result.dict(),
        "new_match_status": match.status
    }
