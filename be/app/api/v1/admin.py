from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db
from app.services.csv_import_service import CSVImportService

router = APIRouter()

@router.post("/import")
async def import_dataset(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload a CSV dataset. This will automatically import users and requests,
    and trigger the batch ILP optimization pipeline in the background.
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed.")
        
    service = CSVImportService()
    result = await service.import_and_run_pipeline(file, db)
    
    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["message"])
        
    return result
