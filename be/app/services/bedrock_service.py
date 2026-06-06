import os
import json
import boto3
from botocore.exceptions import ClientError
from typing import Dict, Any

class BedrockService:
    def __init__(self):
        self.model_id = os.getenv("BEDROCK_MODEL_ID", "us.anthropic.claude-haiku-4-5-20251001-v1:0")
        # boto3 will automatically pick up AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY from env
        self.client = boto3.client(
            service_name="bedrock-runtime",
            region_name=os.getenv("AWS_REGION", "us-east-1")
        )

    def parse_blood_request(self, text: str) -> Dict[str, Any]:
        """
        Uses Claude Haiku on Bedrock to extract patient details from conversational text.
        Expected return format: JSON with name, blood_group, latitude, longitude.
        """
        system_prompt = """
        You are a medical assistant parsing blood requests from text messages.
        Extract the patient's name, blood group, and location (latitude/longitude) if possible.
        If a city or place is mentioned without exact coordinates, estimate its generic latitude/longitude or provide null.
        Respond ONLY with a valid JSON object containing:
        {
          "name": "extracted or Unknown",
          "blood_group": "extracted (e.g. A+, O-) or null",
          "latitude": float or null,
          "longitude": float or null
        }
        """

        messages = [
            {"role": "user", "content": [{"text": text}]}
        ]

        # Use the Converse API for Claude 3/3.5/Haiku
        try:
            response = self.client.converse(
                modelId=self.model_id,
                messages=messages,
                system=[{"text": system_prompt}],
                inferenceConfig={
                    "maxTokens": 500,
                    "temperature": 0.0
                }
            )
            
            output_text = response['output']['message']['content'][0]['text']
            
            # Clean up the output if it has markdown code blocks
            output_text = output_text.strip()
            if output_text.startswith("```json"):
                output_text = output_text[7:]
            if output_text.startswith("```"):
                output_text = output_text[3:]
            if output_text.endswith("```"):
                output_text = output_text[:-3]
                
            return json.loads(output_text.strip())
            
        except ClientError as err:
            print(f"Bedrock Error: {err}")
            return {"error": str(err)}
        except json.JSONDecodeError as err:
            print(f"JSON Parse Error: {err} on string: {output_text}")
            return {"error": "Failed to parse JSON"}

    def extract_medical_record(self, image_bytes: bytes, image_format: str = "jpeg") -> Dict[str, Any]:
        """
        Uses Claude on Bedrock (Vision) to extract medical details from an uploaded image.
        """
        system_prompt = """
        You are an expert medical data extractor.
        Analyze the provided medical record/report image and extract the following details if present:
        - Patient Name
        - Blood Group
        - Key Diagnosis or Findings
        - Urgency (e.g., HIGH, LOW, UNKNOWN based on context like 'immediate transfusion needed')
        - Hospital or Clinic Name
        
        Respond ONLY with a valid JSON object matching this structure:
        {
          "name": "string or null",
          "blood_group": "string or null",
          "diagnosis": "string or null",
          "urgency": "string or null",
          "hospital": "string or null"
        }
        """
        
        if image_format.lower() == "jpg":
            image_format = "jpeg"

        messages = [
            {
                "role": "user", 
                "content": [
                    {
                        "image": {
                            "format": image_format.lower(),
                            "source": {"bytes": image_bytes}
                        }
                    },
                    {"text": system_prompt}
                ]
            }
        ]

        try:
            response = self.client.converse(
                modelId=self.model_id,
                messages=messages,
                inferenceConfig={
                    "maxTokens": 500,
                    "temperature": 0.0
                }
            )
            
            output_text = response['output']['message']['content'][0]['text']
            
            output_text = output_text.strip()
            if output_text.startswith("```json"):
                output_text = output_text[7:]
            if output_text.startswith("```"):
                output_text = output_text[3:]
            if output_text.endswith("```"):
                output_text = output_text[:-3]
                
            return json.loads(output_text.strip())
            
        except ClientError as err:
            print(f"Bedrock Error: {err}")
            return {"error": str(err)}
        except json.JSONDecodeError as err:
            print(f"JSON Parse Error: {err} on string: {output_text}")
            return {"error": "Failed to parse JSON"}

bedrock_service = BedrockService()
