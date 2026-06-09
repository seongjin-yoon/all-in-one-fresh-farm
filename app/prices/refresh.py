from pathlib import Path

from app.prices.garak_crawler import crawl_and_save_latest_prices
from app.rag.ingest_docs import ingest_all


def refresh_price_forecast_rag() -> dict:
    from app.rag.generate_apple_forecast_doc import main as generate_forecast_doc

    price_path = crawl_and_save_latest_prices()
    generate_forecast_doc()
    ingest_all()

    forecast_path = Path("rag_docs") / "apple_price_forecast_chronos_mini.md"
    return {
        "status": "ok",
        "price_data_path": str(price_path),
        "forecast_doc_path": str(forecast_path),
    }
