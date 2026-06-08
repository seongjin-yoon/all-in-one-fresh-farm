import re

from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException

from app.db.chat_memory import (
    add_message,
    get_or_create_session,
    get_recent_turns,
    maybe_summarize_session,
)
from app.db.sales import list_products, register_listing_from_chat_request
from app.llm.ollama_client import generate_answer, summarize_conversation
from app.rag.prompt_builder import build_prompt
from app.rag.retriever import retrieve_context

router = APIRouter()


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1)
    session_id: int | None = None
    user_id: str = "local_user"


class SourceChunk(BaseModel):
    source_path: str
    chunk_index: int
    content: str
    distance: float


class ChatResponse(BaseModel):
    session_id: int
    answer: str
    sources: list[SourceChunk]


def is_inventory_question(question: str) -> bool:
    return any(keyword in question for keyword in ("재고", "남아", "남은", "몇 kg", "몇키로", "몇 킬로"))


def get_requested_grade(question: str) -> str | None:
    for grade in ("상", "중", "하"):
        if re.search(rf"{grade}\s*(?:등급|품질|상품성)", question):
            return grade

    quality_text = (
        question.replace("중과", "")
        .replace("대과", "")
        .replace("중 크기", "")
        .replace("대 크기", "")
        .replace("중 사이즈", "")
        .replace("대 사이즈", "")
    )
    for grade in ("상", "중", "하"):
        if grade in quality_text:
            return grade
    return None


def get_requested_size_class(question: str) -> str | None:
    if "중과" in question or "중 크기" in question or "중 사이즈" in question:
        return "중"
    if "대과" in question or "대 크기" in question or "대 사이즈" in question:
        return "대"
    return None


def build_live_inventory_context() -> dict:
    lines = ["현재 MariaDB 판매 재고 현황입니다."]
    for product in list_products():
        lines.append(
            (
                f"- {product['product_name']} {product['size_class']}과 {product['grade']} 등급: "
                f"기준 가용 재고 {int(product['base_available_kg']):,}kg, "
                f"예약 재고 {int(product['reserved_kg']):,}kg, "
                f"쇼핑몰 등록 재고 {int(product['listed_kg']):,}kg, "
                f"쇼핑몰 남은 판매수량 {int(product['remaining_listing_kg']):,}kg, "
                f"판매 완료 {int(product['sold_kg']):,}kg, "
                f"쇼핑몰 추가 등록 가능 재고 {int(product['available_kg']):,}kg"
            )
        )

    return {
        "source_path": "mariadb://sales/products",
        "chunk_index": 0,
        "content": "\n".join(lines),
        "distance": 0.0,
    }


def build_inventory_answer(question: str) -> str:
    requested_grade = get_requested_grade(question)
    requested_size_class = get_requested_size_class(question)
    products = [
        product
        for product in list_products()
        if (
            (requested_grade is None or product["grade"] == requested_grade)
            and (requested_size_class is None or product["size_class"] == requested_size_class)
        )
    ]

    lines = []
    for product in products:
        lines.append(
            (
                f"{product['size_class']}과 {product['grade']} 등급은 기준 가용 재고 {int(product['base_available_kg']):,}kg 중 "
                f"쇼핑몰 등록 재고가 {int(product['listed_kg']):,}kg이고, "
                f"현재 쇼핑몰 추가 등록 가능 재고는 {int(product['available_kg']):,}kg입니다. "
                f"쇼핑몰에 남아 판매 중인 수량은 {int(product['remaining_listing_kg']):,}kg, "
                f"판매 완료 수량은 {int(product['sold_kg']):,}kg입니다."
            )
        )

    if requested_grade or requested_size_class:
        return " ".join(lines)
    return "\n".join(f"- {line}" for line in lines)


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    try:
        session = get_or_create_session(request.session_id, request.user_id)
        session_id = int(session["id"])
        summary = session.get("summary")
        history = get_recent_turns(session_id)

        try:
            listing = register_listing_from_chat_request(
                request.question,
                history=history,
                summary=summary,
            )
        except ValueError as exc:
            answer = f"{exc} 재고보다 많은 수량은 쇼핑몰에 등록할 수 없습니다."
            add_message(session_id, "user", request.question)
            add_message(session_id, "assistant", answer)
            return ChatResponse(session_id=session_id, answer=answer, sources=[])

        if listing:
            answer = (
                f"{listing['product_name']} {listing['size_class']}과 {listing['grade']} 등급 {listing['quantity_kg']}kg을 "
                f"내부 쇼핑몰에 등록했습니다. kg당 판매가는 {listing['price_per_kg']:,}원이고, "
                f"판매 단위는 {listing['package_unit']}입니다. 등록상품과 알림 탭에서 확인할 수 있습니다."
            )
            add_message(session_id, "user", request.question)
            add_message(session_id, "assistant", answer)
            return ChatResponse(session_id=session_id, answer=answer, sources=[])

        if is_inventory_question(request.question):
            answer = build_inventory_answer(request.question)
            add_message(session_id, "user", request.question)
            add_message(session_id, "assistant", answer)
            return ChatResponse(
                session_id=session_id,
                answer=answer,
                sources=[SourceChunk(**build_live_inventory_context())],
            )

        chunks = retrieve_context(request.question)
        prompt = build_prompt(request.question, chunks)
        answer = generate_answer(prompt, history=history, summary=summary)

        add_message(session_id, "user", request.question)
        add_message(session_id, "assistant", answer)
        maybe_summarize_session(session_id, summary, summarize_conversation)

        return ChatResponse(
            session_id=session_id,
            answer=answer,
            sources=[SourceChunk(**chunk) for chunk in chunks],
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
