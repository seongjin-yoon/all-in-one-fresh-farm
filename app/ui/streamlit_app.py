import html
import os
from pathlib import Path

import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

CHAT_API_URL = os.getenv("CHAT_API_URL", "http://localhost:8000/chat")
ASSET_DIR = Path(__file__).resolve().parent / "assets"
HERO_IMAGE = ASSET_DIR / "apple-hero.png"

st.set_page_config(page_title="Fruits RAG Chatbot", page_icon="apple", layout="centered")

st.markdown(
    """
    <style>
    .stApp {
        background: #f7f8f4;
    }
    .block-container {
        max-width: 860px;
        padding-top: 1.5rem;
        padding-bottom: 3rem;
    }
    .hero-wrap img {
        border-radius: 8px;
        border: 1px solid rgba(28, 48, 38, 0.12);
    }
    .app-kicker {
        color: #55705f;
        font-size: 0.9rem;
        font-weight: 700;
        margin-top: 1.1rem;
        letter-spacing: 0;
    }
    .app-title {
        color: #1d2d24;
        font-size: 2.3rem;
        line-height: 1.15;
        font-weight: 800;
        margin: 0.15rem 0 0.35rem;
        letter-spacing: 0;
    }
    .app-subtitle {
        color: #59685f;
        font-size: 1rem;
        line-height: 1.6;
        margin-bottom: 1.25rem;
    }
    .section-label {
        color: #26362d;
        font-weight: 800;
        margin: 0.5rem 0 0.25rem;
    }
    div[data-testid="stTextArea"] textarea {
        border-radius: 8px;
        border-color: rgba(28, 48, 38, 0.18);
        background: #fffefa;
    }
    div[data-testid="stButton"] button {
        border-radius: 8px;
        font-weight: 700;
    }
    div[data-testid="stExpander"] {
        border-radius: 8px;
        background: #fffefa;
        border-color: rgba(28, 48, 38, 0.14);
    }
    .answer-box {
        background: #fffefa;
        border: 1px solid rgba(28, 48, 38, 0.14);
        border-radius: 8px;
        padding: 1.05rem 1.1rem;
        margin-top: 0.4rem;
        color: #26362d;
        line-height: 1.72;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

if HERO_IMAGE.exists():
    st.markdown('<div class="hero-wrap">', unsafe_allow_html=True)
    st.image(str(HERO_IMAGE), use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown('<div class="app-kicker">LOCAL LLM + MARIADB VECTOR</div>', unsafe_allow_html=True)
st.markdown('<h1 class="app-title">과일 자동화 RAG 챗봇</h1>', unsafe_allow_html=True)
st.markdown(
    '<p class="app-subtitle">수확, 선별, 가격산정, 판매등록 기준을 바탕으로 현장 질문에 답변합니다.</p>',
    unsafe_allow_html=True,
)

if "question" not in st.session_state:
    st.session_state.question = ""
if "session_id" not in st.session_state:
    st.session_state.session_id = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

example_questions = [
    "사과 선별 기준은 무엇인가요?",
    "가격산정 기준을 쉽게 알려줘",
    "판매등록 전에 무엇을 확인해야 해?",
]

cols = st.columns(3)
for col, example in zip(cols, example_questions):
    if col.button(example, use_container_width=True):
        st.session_state.question = example

st.markdown('<div class="section-label">질문</div>', unsafe_allow_html=True)
question = st.text_area(
    "질문",
    placeholder="예: 덜 익은 사과는 어떻게 처리해?",
    height=130,
    key="question",
    label_visibility="collapsed",
)

if st.session_state.chat_history:
    st.markdown('<div class="section-label">최근 대화</div>', unsafe_allow_html=True)
    for turn in st.session_state.chat_history[-3:]:
        st.chat_message("user").write(turn["user"])
        st.chat_message("assistant").write(turn["assistant"])

if st.button("질문하기", type="primary", disabled=not question.strip()):
    with st.spinner("로컬 LLM이 답변을 생성하는 중입니다..."):
        try:
            response = requests.post(
                CHAT_API_URL,
                json={"question": question, "session_id": st.session_state.session_id},
                timeout=120,
            )
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as exc:
            st.error(f"API 호출 실패: {exc}")
        else:
            st.session_state.session_id = data["session_id"]
            st.session_state.chat_history.append(
                {"user": question, "assistant": data["answer"]}
            )
            st.session_state.chat_history = st.session_state.chat_history[-3:]
            safe_answer = html.escape(data["answer"]).replace("\n", "<br>")
            st.markdown('<div class="section-label">답변</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="answer-box">{safe_answer}</div>', unsafe_allow_html=True)

            with st.expander("검색된 문서 chunk"):
                for source in data.get("sources", []):
                    st.markdown(
                        f"**{source['source_path']} / chunk {source['chunk_index']}** "
                        f"(distance: {source['distance']:.4f})"
                    )
                    st.write(source["content"])

if st.session_state.session_id:
    st.caption(f"현재 대화 세션 #{st.session_state.session_id} | 오래된 대화는 MariaDB에 요약 저장됩니다.")
