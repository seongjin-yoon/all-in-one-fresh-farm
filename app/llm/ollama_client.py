import os
import re

import ollama
from dotenv import load_dotenv

load_dotenv()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
CHAT_MODEL = os.getenv("OLLAMA_CHAT_MODEL", "qwen2.5:7b")

client = ollama.Client(host=OLLAMA_BASE_URL)

HANJA_OR_CHINESE_PATTERN = re.compile(r"[\u4e00-\u9fff]")
ENGLISH_WORD_PATTERN = re.compile(r"[A-Za-z]{2,}")
HYPHENATED_ENGLISH_PATTERN = re.compile(r"[A-Za-z]+-[A-Za-z]+")
ALLOWED_SHORT_ENGLISH_WORDS = {
    "ai",
    "api",
    "db",
    "erp",
    "kg",
    "llm",
    "pos",
    "rag",
    "ui",
    "wms",
}


def contains_hanja_or_chinese(text: str) -> bool:
    return bool(HANJA_OR_CHINESE_PATTERN.search(text))


def contains_excessive_english(text: str) -> bool:
    english_words = [
        word
        for word in ENGLISH_WORD_PATTERN.findall(text)
        if word.lower() not in ALLOWED_SHORT_ENGLISH_WORDS
    ]
    if not english_words:
        return False

    latin_chars = sum(len(word) for word in english_words)
    non_space_chars = sum(1 for char in text if not char.isspace())
    latin_ratio = latin_chars / max(non_space_chars, 1)

    return (
        len(english_words) >= 5
        or (latin_chars >= 25 and latin_ratio >= 0.25)
        or bool(HYPHENATED_ENGLISH_PATTERN.search(text))
    )


def contains_disallowed_foreign_text(text: str) -> bool:
    return contains_hanja_or_chinese(text) or contains_excessive_english(text)


def build_messages(
    prompt: str,
    history: list[dict[str, str]] | None = None,
    summary: str | None = None,
) -> list[dict[str, str]]:
    messages = [
        {
            "role": "system",
            "content": (
                "당신은 과일 농장, 선별, 가격산정, 판매 업무를 돕는 친절한 한국어 업무 도우미입니다. "
                "항상 한국어로만 답변하세요. 중국어, 영어, 한자 중심 표현을 사용하지 마세요. "
                "사용자가 명시적으로 요청하지 않는 한 내부 검색, RAG, 출처, 문서를 언급하지 마세요. "
                "최근 대화는 사용자의 후속 질문 의도를 이해하는 데만 활용하고, 업무 기준은 현재 질문의 참고 정보를 우선하세요."
            ),
        }
    ]

    if summary:
        messages.append(
            {
                "role": "system",
                "content": f"이전 대화 요약입니다. 후속 질문의 맥락 이해에만 사용하세요.\n{summary}",
            }
        )

    for turn in (history or [])[-3:]:
        user_message = turn.get("user", "").strip()
        assistant_message = turn.get("assistant", "").strip()
        if user_message:
            messages.append({"role": "user", "content": user_message})
        if assistant_message:
            messages.append({"role": "assistant", "content": assistant_message})

    messages.append({"role": "user", "content": prompt})
    return messages


def generate_answer(
    prompt: str,
    history: list[dict[str, str]] | None = None,
    summary: str | None = None,
) -> str:
    response = client.chat(
        model=CHAT_MODEL,
        messages=build_messages(prompt, history, summary),
        options={"temperature": 0.2},
    )
    answer = response["message"]["content"]
    if not contains_disallowed_foreign_text(answer):
        return answer

    rewrite_prompt = f"""
다음 텍스트를 한국어로 번역하고 다듬어 주세요.
출력은 반드시 한글 중심의 자연스러운 한국어만 사용하세요.
중국어 원문과 한자는 출력하지 마세요.
AI, API, LLM, Streamlit 같은 짧고 자연스러운 기술 용어는 필요할 때만 허용하세요.
영어 문장이나 긴 영어 표현은 쉬운 한국어로 바꾸세요.
새로운 내용은 추가하지 말고, 원래 뜻만 유지하세요.

텍스트:
{answer}
""".strip()

    rewrite_response = client.chat(
        model=CHAT_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "당신은 중국어와 영어를 자연스러운 한국어로 번역하는 번역기입니다. "
                    "반드시 한글 중심의 한국어를 출력하세요. 한자와 중국어 문자는 절대 출력하지 마세요. "
                    "짧은 기술 용어를 제외한 영어 문장과 긴 영어 표현은 한국어로 바꾸세요."
                ),
            },
            {"role": "user", "content": rewrite_prompt},
        ],
        options={"temperature": 0.1},
    )
    rewritten_answer = rewrite_response["message"]["content"]
    if contains_disallowed_foreign_text(rewritten_answer):
        return "답변에 한국어가 아닌 표현이 섞여 다시 정리해야 합니다. 질문을 한 번만 더 보내주시면 한국어로만 답변드릴게요."
    return rewritten_answer


def summarize_conversation(existing_summary: str, rows: list[dict]) -> str:
    conversation = "\n".join(
        f"{'사용자' if row['role'] == 'user' else '도우미'}: {row['content']}"
        for row in rows
    )
    prompt = f"""
기존 요약과 새 대화를 합쳐 1,200자 이내의 한국어 요약으로 갱신하세요.
다음 질문을 이해하는 데 필요한 내용만 남기세요.
사용자의 관심 품목, 의사결정 목적, 선호 조건, 미해결 질문을 중심으로 정리하세요.
가격, 재고, 시세 숫자는 오래될 수 있으므로 꼭 필요한 경우만 짧게 포함하세요.
새로운 사실을 만들지 마세요.

# 기존 요약
{existing_summary or "없음"}

# 새 대화
{conversation}

# 갱신 요약
""".strip()

    response = client.chat(
        model=CHAT_MODEL,
        messages=[
            {
                "role": "system",
                "content": "당신은 대화 내용을 한국어로 짧고 정확하게 요약하는 도우미입니다.",
            },
            {"role": "user", "content": prompt},
        ],
        options={"temperature": 0.1, "num_predict": 500},
    )
    return response["message"]["content"].strip()
