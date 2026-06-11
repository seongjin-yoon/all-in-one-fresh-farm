from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.db.sales import record_harvest_event

router = APIRouter(prefix="/robot", tags=["robot"])


class HarvestRequest(BaseModel):
    size_class: str = Field(..., min_length=1)
    quality_grade: str = Field(..., min_length=1)
    product_name: str = "사과"
    harvested_at: datetime | None = None


class HarvestResponse(BaseModel):
    id: int
    product_name: str
    size_class: str
    quality_grade: str
    estimated_weight_kg: float
    harvested_at: datetime
    current_base_available_kg: float
    current_available_kg: float


@router.post("/harvest", response_model=HarvestResponse)
def create_harvest_event(request: HarvestRequest) -> HarvestResponse:
    try:
        event = record_harvest_event(
            size_class=request.size_class,
            quality_grade=request.quality_grade,
            product_name=request.product_name,
            harvested_at=request.harvested_at,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return HarvestResponse(**event)
