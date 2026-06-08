import os

from dotenv import load_dotenv

from app.db.vector_search import search_similar_chunks
from app.rag.embedder import embed_text

load_dotenv()

TOP_K = int(os.getenv("RAG_TOP_K", "4"))
DISTANCE_THRESHOLD = float(os.getenv("RAG_DISTANCE_THRESHOLD", "0.52"))

INVENTORY_KEYWORDS = ("재고", "가용", "예약", "보유", "물량")
FORECAST_KEYWORDS = (
    "예측",
    "전망",
    "시세",
    "가격",
    "판매시기",
    "판매 시기",
    "언제 팔",
    "언제",
    "팔기 좋은",
    "좋은 날",
    "타이밍",
)


def has_any(text: str, keywords: tuple[str, ...]) -> bool:
    return any(keyword in text for keyword in keywords)


def rank_by_question_intent(question: str, chunks: list[dict], top_k: int) -> list[dict]:
    if has_any(question, FORECAST_KEYWORDS):
        forecast_chunks = [
            chunk for chunk in chunks if "forecast" in chunk["source_path"]
        ]
        other_chunks = [
            chunk for chunk in chunks if "forecast" not in chunk["source_path"]
        ]
        ranked_chunks = forecast_chunks + other_chunks
        if ranked_chunks:
            return ranked_chunks[:top_k]

    if has_any(question, INVENTORY_KEYWORDS) and not has_any(question, FORECAST_KEYWORDS):
        inventory_chunks = [
            chunk
            for chunk in chunks
            if has_any(chunk["content"], INVENTORY_KEYWORDS)
            and "forecast" not in chunk["source_path"]
        ]
        if inventory_chunks:
            return inventory_chunks[:top_k]

    return chunks[:top_k]


def retrieve_context(
    question: str,
    top_k: int = TOP_K,
    distance_threshold: float | None = DISTANCE_THRESHOLD,
) -> list[dict]:
    question_embedding = embed_text(question)
    effective_threshold = None if has_any(question, FORECAST_KEYWORDS) else distance_threshold
    chunks = search_similar_chunks(question_embedding, top_k * 5, effective_threshold)
    return rank_by_question_intent(question, chunks, top_k)
