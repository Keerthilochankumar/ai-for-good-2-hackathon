from pydantic_settings.sources.providers import dotenv
import json
import numpy as np
from scipy.optimize import linear_sum_assignment
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Tuple
from app.models.user import User, get_compatible_blood_groups
from app.models.request import BloodRequest
from app.services.trigger_service import haversine
from app.core.config import settings
import structlog
import asyncio
import httpx


logger = structlog.get_logger()

class ILPMatchingService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.llm_client = bool(settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY)

    async def optimize_batch(self, requests: List[BloodRequest], donors: List[User]) -> List[Tuple[BloodRequest, User, float, str]]:
        """
        Stage 2 ILP Optimization with Stage 3 LLM Validation.
        Solves the bipartite matching problem to minimize global distance while 
        prioritizing urgency. Validates the top assignments using an LLM.
        
        Returns a list of tuples: (BloodRequest, User, cost_score, llm_reason)
        """
        if not requests or not donors:
            return []
            
        n_req = len(requests)
        n_don = len(donors)
        
        cost_matrix = np.zeros((n_req, n_don))
        
        for i, req in enumerate(requests):
            for j, donor in enumerate(donors):
                cost_matrix[i, j] = self.calculate_cost(req, donor)

        row_ind, col_ind = linear_sum_assignment(cost_matrix)
        
        INF_COST = 999999.0
        matches = []
        for i, j in zip(row_ind, col_ind):
            cost = cost_matrix[i, j]
            if cost < INF_COST / 2: # Ignore infeasible assignments
                dist = haversine(requests[i].latitude, requests[i].longitude, donors[j].latitude, donors[j].longitude)
                
                # LLM Validation
                is_valid, reason = await self.validate_match_with_llm(requests[i], donors[j])
                if is_valid:
                    matches.append((requests[i], donors[j], dist, reason))
                else:
                    logger.info(f"LLM rejected match for Request {requests[i].id} and Donor {donors[j].id}. Reason: {reason}")
                
        return matches

    def calculate_cost(self, req: BloodRequest, donor: User) -> float:
        INF_COST = 999999.0
        if donor.blood_group not in get_compatible_blood_groups(req.blood_group):
            return INF_COST
            
        dist = haversine(req.latitude, req.longitude, donor.latitude, donor.longitude)
        if dist > 30.0:
            return INF_COST
            
        urgency_weights = {
            "ROUTINE": 1.0,
            "URGENT": 2.0,
            "CRITICAL": 5.0
        }
        urgency_reward = urgency_weights.get(req.urgency.value, 1.0) * 1000.0
        return dist - urgency_reward

    async def get_top_matches_for_patient(self, request: BloodRequest, donors: List[User], limit: int = 10) -> List[Tuple[User, float, str]]:
        """
        Runs the penalty approach synchronously for a single patient to score donors, 
        then uses LLM to validate the top candidates before returning them.
        """
        logger.info(f"Mapping Endpoint: Starting match process for Patient {request.id}. Found {len(donors)} raw matching blood group donors.")
        scored_donors = []
        INF_COST = 999999.0
        for donor in donors:
            cost = self.calculate_cost(request, donor)
            if cost < INF_COST / 2:
                dist = haversine(request.latitude, request.longitude, donor.latitude, donor.longitude)
                scored_donors.append((donor, dist, cost))
                
        scored_donors.sort(key=lambda x: x[2])
        top_candidates = scored_donors[:limit * 2] # Get double the limit to account for AI rejections
        logger.info(f"Mapping Endpoint: Top {len(top_candidates)} candidates selected for AI validation based on spatial/urgency scoring.")
        
        final_matches = []
        for donor, dist, cost in top_candidates:
            if len(final_matches) >= limit:
                break
                
            logger.info(f"Mapping Endpoint: Running AI validation for candidate Donor {donor.id}")
            is_valid, reason = await self.validate_match_with_llm(request, donor, penalty=cost)
            logger.info(f"Mapping Endpoint: AI Validation result for Donor {donor.id} -> Valid: {is_valid} | Reason: {reason}")
            
            if is_valid:
                final_matches.append((donor, dist, reason))
                
        logger.info(f"Mapping Endpoint: Returning {len(final_matches)} final AI-validated matches.")
        return final_matches

    async def validate_match_with_llm(self, req: BloodRequest, donor: User, penalty: float = 0.0) -> Tuple[bool, str]:
        """
        Uses an LLM to evaluate the clinical and demographic suitability of the donor for the patient.
        """
        if not self.llm_client:
            return True, "LLM not configured; bypassing validation."
            
        prompt = f"""
        You are a clinical decision support system validating a blood donation match.
        Evaluate the following donor-patient pair for compatibility based on their extended profiles.
        
        Patient Profile:
        Blood Group: {req.blood_group}
        Urgency: {req.urgency.value}
        Gender: {req.gender}
        Expected Next Transfusion Date: {req.expected_next_transfusion_date}
        
        Donor Profile:
        Blood Group: {donor.blood_group}
        Donor Type: {donor.donor_type}
        Gender: {donor.gender}
        Eligibility Status: {donor.eligibility_status}
        Account Status: {donor.account_status}
        Donations Till Date: {donor.donations_till_date}
        Last Contacted Date: {donor.last_contacted_date}
        
        System Calculated Penalty Score: {penalty:.2f} (lower is better, higher indicates longer distance or less urgency)
        
        Given these factors, is this a clinically and logistically safe match? Consider factors such as matching blood types, donor eligibility, urgency, and the calculated penalty score.
        """
        aws_access_key = settings.AWS_ACCESS_KEY_ID.strip('"\'') if settings.AWS_ACCESS_KEY_ID else None
        aws_secret_key = settings.AWS_SECRET_ACCESS_KEY.strip('"\'') if settings.AWS_SECRET_ACCESS_KEY else None
        
        if not aws_access_key or not aws_secret_key:
            return True, "LLM not configured (missing AWS credentials); bypassing validation."

        try:
            from anthropic import AsyncAnthropicBedrock
            
            region = settings.AWS_REGION.strip('"\'') if settings.AWS_REGION else "us-east-1"
            model_id = settings.BEDROCK_MODEL_ID.strip('"\'')
            
            client = AsyncAnthropicBedrock(
                aws_access_key=aws_access_key,
                aws_secret_key=aws_secret_key,
                aws_region=region,
            )
            
            validation_tool = {
                "name": "record_validation",
                "description": "Record the clinical validation result for the donor-patient blood match.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "is_valid": {
                            "type": "boolean",
                            "description": "Whether the match is clinically and logistically safe."
                        },
                        "reason": {
                            "type": "string",
                            "description": "Short explanation of the decision."
                        }
                    },
                    "required": ["is_valid", "reason"]
                }
            }
            
            response = await client.messages.create(
                model=model_id,
                max_tokens=300,
                system="You validate donor-patient blood match safety. Use the provided tool to output your validation result.",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                tools=[validation_tool],
                tool_choice={"type": "tool", "name": "record_validation"}
            )
            
            for content_block in response.content:
                if content_block.type == 'tool_use' and content_block.name == 'record_validation':
                    result = content_block.input
                    return result.get("is_valid", True), result.get("reason", "No reason provided")
            
            return True, "No tool use found in LLM response, fallback to valid."
        except Exception as e:
            logger.error(f"Error validating match with LLM: {str(e)}")
            return True, "Error calling LLM, fallback to valid."
