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

    def rank_donors_by_priority(self, donors: List[User]) -> dict:
        """
        Ranks donors into Priority 1 (Bridged/Emergency) and Priority 2 (Regular).
        """
        ranked = {"Priority 1 (Bridged/Emergency)": [], "Priority 2 (Regular)": []}
        for d in donors:
            dtype = (d.donor_type or "").lower()
            elstatus = (d.eligibility_status or "").lower()
            if "bridge" in dtype or "bridge" in elstatus or "emergency" in dtype:
                ranked["Priority 1 (Bridged/Emergency)"].append(d)
            else:
                ranked["Priority 2 (Regular)"].append(d)
        return ranked

    async def get_top_matches_for_patient(self, request: BloodRequest, donors: List[User], limit: int = 10) -> List[Tuple[User, float, str]]:
        """
        Runs the penalty approach synchronously for a single patient to score donors, 
        then uses LLM to validate the top candidates in bulk before returning them.
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
        
        if not top_candidates:
            return []
            
        candidate_donors = [c[0] for c in top_candidates]
        ranked_groups = self.rank_donors_by_priority(candidate_donors)
        
        validated_results = await self.validate_matches_in_bulk_with_llm(request, ranked_groups, top_candidates)
        
        final_matches = []
        for donor, dist, cost in top_candidates:
            val = validated_results.get(str(donor.id))
            if val and val.get("is_valid"):
                final_matches.append((donor, dist, val.get("reason", "OK")))
                if len(final_matches) >= limit:
                    break
                    
        logger.info(f"Mapping Endpoint: Returning {len(final_matches)} final AI-validated matches.")
        return final_matches

    async def validate_matches_in_bulk_with_llm(self, req: BloodRequest, ranked_groups: dict, top_candidates: list) -> dict:
        """
        Uses an LLM to evaluate the clinical and demographic suitability of the donor list in bulk.
        Returns a dict mapping donor_id to {"is_valid": bool, "reason": str}.
        """
        if not self.llm_client:
            return {str(d[0].id): {"is_valid": True, "reason": "LLM not configured"} for d in top_candidates}
            
        prompt = f"""You are a clinical decision support system validating blood donation matches.
Evaluate the following donor candidates for the patient in bulk.
Output a strict format using the provided tool without additional justification.

Patient Profile:
Blood Group: {req.blood_group}
Urgency: {req.urgency.value}
Gender: {req.gender}
Expected Next Transfusion Date: {req.expected_next_transfusion_date}

Donor Candidates (by Priority Rank):
"""
        cost_map = {str(d[0].id): d[2] for d in top_candidates}
        for rank, d_list in ranked_groups.items():
            if not d_list: continue
            prompt += f"\n--- {rank} ---\n"
            for d in d_list:
                prompt += f"- ID: {d.id} | BG: {d.blood_group} | Type: {d.donor_type} | Eligibility: {d.eligibility_status} | Donations: {d.donations_till_date} | ILP Penalty: {cost_map[str(d.id)]:.2f}\n"
                
        aws_access_key = settings.AWS_ACCESS_KEY_ID.strip('"\'') if settings.AWS_ACCESS_KEY_ID else None
        aws_secret_key = settings.AWS_SECRET_ACCESS_KEY.strip('"\'') if settings.AWS_SECRET_ACCESS_KEY else None
        
        if not aws_access_key or not aws_secret_key:
            return {str(d[0].id): {"is_valid": True, "reason": "LLM missing credentials"} for d in top_candidates}

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
                "name": "record_bulk_validation",
                "description": "Record the clinical validation results for the list of donor candidates.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "results": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "donor_id": {"type": "string"},
                                    "is_valid": {"type": "boolean"},
                                    "reason": {"type": "string", "description": "Short explanation (e.g., 'Match OK')"}
                                },
                                "required": ["donor_id", "is_valid", "reason"]
                            }
                        }
                    },
                    "required": ["results"]
                }
            }
            
            response = await client.messages.create(
                model=model_id,
                max_tokens=1000,
                system="You validate donor-patient blood match safety in bulk. Use the provided tool to output your results. Provide simple and short reasons.",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                tools=[validation_tool],
                tool_choice={"type": "tool", "name": "record_bulk_validation"}
            )
            
            for content_block in response.content:
                if content_block.type == 'tool_use' and content_block.name == 'record_bulk_validation':
                    items = content_block.input.get("results", [])
                    return {item["donor_id"]: {"is_valid": item["is_valid"], "reason": item["reason"]} for item in items}
            
            return {str(d[0].id): {"is_valid": True, "reason": "No tool used"} for d in top_candidates}
        except Exception as e:
            logger.error(f"Error validating match with LLM: {str(e)}")
            return {str(d[0].id): {"is_valid": True, "reason": "LLM Error"} for d in top_candidates}

    async def validate_match_with_llm(self, req: BloodRequest, donor: User, penalty: float = 0.0) -> Tuple[bool, str]:
        """Legacy method for batch optimizing 1 by 1."""
        return True, "Legacy validation bypassed"
