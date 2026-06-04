from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException

from app.db.chat_memory import (
    add_message,
    get_or_create_session,
    get_recent_turns,
    maybe_summarize_session,
)
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


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    try:
        session = get_or_create_session(request.session_id, request.user_id)
        session_id = int(session["id"])
        summary = session.get("summary")
        history = get_recent_turns(session_id)

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
