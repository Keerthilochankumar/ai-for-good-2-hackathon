import json
from pydantic import BaseModel, Field
from typing import Literal, Optional
from app.core.config import settings
import structlog
import httpx

logger = structlog.get_logger()

class DonorIntent(BaseModel):
    """Structured output schema for donor reply parsing."""
    intent: Literal["accept", "decline", "reschedule", "unclear"]
    reason: Optional[str] = Field(None, description="illness, travel, busy, personal, other")
    suggested_reschedule_days: Optional[int] = Field(None, description="Days to reschedule")
    confidence: float = Field(description="0.0 to 1.0 confidence score")

class NLUService:
    """
    Anthropic Bedrock Proxy for structured NLU extraction.
    Called when a donor sends a free-text response.
    """
    def __init__(self):
        pass
    
    async def parse_donor_reply(self, raw_text: str) -> DonorIntent:
        """
        Input:  "I'm sick this week, can't make it"
        Output: DonorIntent(
            intent="decline",
            reason="illness",
            suggested_reschedule_days=7,
            confidence=0.95
        )
        """
        aws_access_key = settings.AWS_ACCESS_KEY_ID.strip('"\'') if settings.AWS_ACCESS_KEY_ID else None
        aws_secret_key = settings.AWS_SECRET_ACCESS_KEY.strip('"\'') if settings.AWS_SECRET_ACCESS_KEY else None
        
        if not aws_access_key or not aws_secret_key:
            logger.warning("AWS credentials not configured, returning 'unclear' intent.")
            return DonorIntent(intent="unclear", confidence=0.0)

        try:
            from anthropic import AsyncAnthropicBedrock
            
            region = settings.AWS_REGION.strip('"\'') if settings.AWS_REGION else "us-east-1"
            model_id = settings.BEDROCK_MODEL_ID.strip('"\'')
            
            system_prompt = (
                "You are a blood donation intent classifier. "
                "Extract the donor's intent from their reply. "
                "Use the provided tool to output your parsed result."
            )
            
            client = AsyncAnthropicBedrock(
                aws_access_key=aws_access_key,
                aws_secret_key=aws_secret_key,
                aws_region=region,
            )
            
            intent_tool = {
                "name": "record_donor_intent",
                "description": "Record the donor's intent extracted from their reply.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "intent": {
                            "type": "string",
                            "enum": ["accept", "decline", "reschedule", "unclear"],
                            "description": "The donor's main intent."
                        },
                        "reason": {
                            "type": "string",
                            "description": "Reason given, e.g. illness, travel, busy, personal, other. Leave null if not provided."
                        },
                        "suggested_reschedule_days": {
                            "type": "integer",
                            "description": "Number of days the donor suggests rescheduling by, if applicable."
                        },
                        "confidence": {
                            "type": "number",
                            "description": "Confidence score from 0.0 to 1.0 of this interpretation."
                        }
                    },
                    "required": ["intent", "confidence"]
                }
            }
            
            response = await client.messages.create(
                model=model_id,
                max_tokens=1024,
                system=system_prompt,
                messages=[{"role": "user", "content": raw_text}],
                temperature=0.0,
                tools=[intent_tool],
                tool_choice={"type": "tool", "name": "record_donor_intent"}
            )
            
            parsed_json = None
            for content_block in response.content:
                if content_block.type == 'tool_use' and content_block.name == 'record_donor_intent':
                    parsed_json = content_block.input
                    break
                    
            if not parsed_json:
                return DonorIntent(intent="unclear", confidence=0.0)
                
            result = DonorIntent(**parsed_json)
            
            # Fallback for low confidence
            if result.confidence < 0.7:
                result.intent = "unclear"
                
            return result
        except Exception as e:
            logger.error(f"Error parsing donor reply: {str(e)}")
            return DonorIntent(intent="unclear", confidence=0.0)
