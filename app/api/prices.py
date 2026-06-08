from fastapi import APIRouter, HTTPException

from app.prices.refresh import refresh_price_forecast_rag

router = APIRouter(prefix="/prices", tags=["prices"])


@router.get("/refresh")
def refresh_prices_info() -> dict:
    return {
        "message": "이 주소는 가격 갱신 API입니다. 관리자 Streamlit 화면의 '최신 시세 가져와서 RAG 갱신' 버튼으로 실행하세요.",
        "method": "POST",
        "path": "/prices/refresh",
    }


@router.post("/refresh")
def refresh_prices() -> dict:
    try:
        return refresh_price_forecast_rag()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
