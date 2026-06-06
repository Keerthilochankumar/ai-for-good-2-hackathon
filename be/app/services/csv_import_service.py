import pandas as pd
import io
import structlog
import numpy as np
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone
from app.models.user import User, BloodGroup
from app.models.request import BloodRequest, UrgencyLevel
from app.tasks.optimization_tasks import run_ilp_batch_optimization
import random

logger = structlog.get_logger()

class CSVImportService:
    async def import_and_run_pipeline(
        self, file: UploadFile, db: AsyncSession
    ) -> dict:
        """
        STEP 1 — IMPORT:
        Reads the CSV (7K dataset). Upserts Donors and creates BloodRequests.
        
        STEP 2 — TRIGGER:
        Kicks off the Celery optimization task (Stage 2 ILP) automatically.
        """
        content = await file.read()
        
        # Read CSV with pandas
        try:
            df = pd.read_csv(io.StringIO(content.decode("utf-8")))
            df.columns = df.columns.str.strip().str.lower()
            df = df.replace({np.nan: None})
        except Exception as e:
            return {"status": "error", "message": f"Failed to parse CSV: {e}"}
            
        # Load existing IDs to prevent duplicates
        existing_donors_res = await db.execute(select(User.external_id).where(User.external_id.isnot(None)))
        seen_donors = set(existing_donors_res.scalars().all())
        
        existing_req_res = await db.execute(select(BloodRequest.external_id).where(BloodRequest.external_id.isnot(None)))
        seen_requests = set(existing_req_res.scalars().all())

        donors_added = 0
        requests_added = 0
        
        for _, row in df.iterrows():
            role = str(row.get("role", "")).strip().lower()
            raw_id = str(row.get("user_id", "Unknown"))
            
            if pd.isna(raw_id) or not raw_id:
                continue
            
            if "donor" in role:
                if raw_id in seen_donors:
                    continue
                seen_donors.add(raw_id)
                record_type = "donor"
            elif "patient" in role or "receiver" in role or row.get("quantity_required") is not None:
                if raw_id in seen_requests:
                    continue
                seen_requests.add(raw_id)
                record_type = "patient"
            else:
                continue # Skip rows we can't identify
                
            # Name and phone don't exist in dataset, generate dummies
            name = f"User_{raw_id[:6]}" if len(raw_id) > 6 else f"User_{raw_id}"
            phone = "555-0000"
            
            # Map blood group from 'A Positive' to enum
            bg_raw = str(row.get("blood_group", "")).strip().lower()
            bg_map = {
                "a positive": BloodGroup.A_POS, "a+": BloodGroup.A_POS,
                "a negative": BloodGroup.A_NEG, "a-": BloodGroup.A_NEG,
                "b positive": BloodGroup.B_POS, "b+": BloodGroup.B_POS,
                "b negative": BloodGroup.B_NEG, "b-": BloodGroup.B_NEG,
                "ab positive": BloodGroup.AB_POS, "ab+": BloodGroup.AB_POS,
                "ab negative": BloodGroup.AB_NEG, "ab-": BloodGroup.AB_NEG,
                "o positive": BloodGroup.O_POS, "o+": BloodGroup.O_POS,
                "o negative": BloodGroup.O_NEG, "o-": BloodGroup.O_NEG,
            }
            bg = bg_map.get(bg_raw)
            if not bg:
                continue # Skip invalid blood groups
                
            raw_lat = float(row.get("latitude", 0.0) or 0.0)
            raw_lon = float(row.get("longitude", 0.0) or 0.0)
            
            # If coordinates are missing or zero, default to a central location (e.g., Hyderabad)
            if raw_lat == 0.0:
                raw_lat = 17.3922792
            if raw_lon == 0.0:
                raw_lon = 78.4602749
                
            # Add up to ~15km jitter (0.15 degrees) for realistic distance simulation
            lat = raw_lat + random.uniform(-0.15, 0.15)
            lon = raw_lon + random.uniform(-0.15, 0.15)

            # Helper for datetime parsing
            def parse_date(val):
                if val is None or not str(val).strip():
                    return None
                try:
                    return pd.to_datetime(val).replace(tzinfo=timezone.utc)
                except Exception:
                    return None

            # Helper for bool parsing
            def parse_bool(val):
                if val is None:
                    return None
                v = str(val).lower().strip()
                return v in ['true', '1', 'yes', 'y', 't']

            if record_type == "donor":
                # Create donor
                donor = User(
                    external_id=raw_id,
                    name=name,
                    phone=phone,
                    blood_group=bg,
                    latitude=lat,
                    longitude=lon,
                    is_available=True,
                    gender=str(row.get("gender", "")) if row.get("gender") is not None else None,
                    registration_date=parse_date(row.get("registration_date")),
                    donor_type=str(row.get("donor_type", "")) if row.get("donor_type") is not None else None,
                    last_contacted_date=parse_date(row.get("last_contacted_date")),
                    next_eligible_date=parse_date(row.get("next_eligible_date")),
                    donations_till_date=int(float(row.get("donations_till_date", 0))) if row.get("donations_till_date") is not None else None,
                    eligibility_status=str(row.get("eligibility_status", "")) if row.get("eligibility_status") is not None else None,
                    cycle_of_donations=int(float(row.get("cycle_of_donations", 0))) if row.get("cycle_of_donations") is not None else None,
                    total_calls=int(float(row.get("total_calls", 0))) if row.get("total_calls") is not None else None,
                    frequency_in_days=int(float(row.get("frequency_in_days", 0))) if row.get("frequency_in_days") is not None else None,
                    account_status=str(row.get("status", "")) if row.get("status") is not None else None,
                    donated_earlier=parse_bool(row.get("donated_earlier")),
                    calls_to_donations_ratio=float(row.get("calls_to_donations_ratio", 0)) if row.get("calls_to_donations_ratio") is not None else None,
                    user_donation_active_status=str(row.get("user_donation_active_status", "")) if row.get("user_donation_active_status") is not None else None,
                    inactive_trigger_comment=str(row.get("inactive_trigger_comment", "")) if row.get("inactive_trigger_comment") is not None else None
                )
                db.add(donor)
                donors_added += 1
                
            elif record_type == "patient":
                # Dataset has no urgency, default to URGENT for testing
                urgency = UrgencyLevel.URGENT
                    
                # Parse units from quantity_required
                qty = row.get("quantity_required")
                if qty is None:
                    units = 1
                else:
                    try:
                        units = int(float(qty))
                    except (ValueError, TypeError):
                        units = 1
                
                hospital = "Central Hospital" # Dummy hospital
                
                # Deadline logic
                now = datetime.now(timezone.utc)
                deadline = now + pd.Timedelta(days=3)
                    
                req = BloodRequest(
                    external_id=raw_id,
                    patient_name=name,
                    blood_group=bg,
                    units_required=units,
                    hospital_name=hospital,
                    latitude=lat,
                    longitude=lon,
                    urgency=urgency,
                    deadline=deadline,
                    status="OPEN",
                    gender=str(row.get("gender", "")) if not pd.isna(row.get("gender")) else None,
                    bridge_id=str(row.get("bridge_id", "")) if not pd.isna(row.get("bridge_id")) else None,
                    role_status=parse_bool(row.get("role_status")),
                    bridge_status=parse_bool(row.get("bridge_status")),
                    bridge_gender=str(row.get("bridge_gender", "")) if not pd.isna(row.get("bridge_gender")) else None,
                    bridge_blood_group=str(row.get("bridge_blood_group", "")) if not pd.isna(row.get("bridge_blood_group")) else None,
                    last_transfusion_date=parse_date(row.get("last_transfusion_date")),
                    expected_next_transfusion_date=parse_date(row.get("expected_next_transfusion_date")),
                    status_of_bridge=parse_bool(row.get("status_of_bridge")),
                    last_bridge_donation_date=parse_date(row.get("last_bridge_donation_date"))
                )
                db.add(req)
                requests_added += 1
                
        # Commit to DB
        await db.commit()
        
        return {
            "status": "success", 
            "message": f"Imported {donors_added} donors and {requests_added} requests. Did not trigger optimization pipeline."
        }
