import base64
import csv
import html
import os
import re
from pathlib import Path

import requests
import streamlit as st

from app.config import load_app_env

load_app_env()

CHAT_API_URL = os.getenv("CHAT_API_URL", "http://localhost:8000/chat")
API_BASE_URL = CHAT_API_URL.rsplit("/", 1)[0]
PROJECT_ROOT = Path(__file__).resolve().parents[2]
PRICE_DATA_PATH = PROJECT_ROOT / "fruits_data" / "garak_apple_prices.csv"
FORECAST_DOC_PATH = PROJECT_ROOT / "rag_docs" / "apple_price_forecast_chronos_mini.md"
NEWS_DOC_PATH = PROJECT_ROOT / "rag_docs" / "fruit_news_2026.md"
ASSET_DIR = Path(__file__).resolve().parent / "assets"
ORCHARD_BACKGROUND_IMAGE_PATH = ASSET_DIR / "apple-orchard-bg.png"
ADMIN_TITLE_IMAGE_PATH = ASSET_DIR / "apple-hero.png"
ADMIN_PROMO_IMAGE_PATH = ASSET_DIR / "apple-market-banner.png"
FREE_PROMO_IMAGE_PATHS = (
    ASSET_DIR / "ai-campus-onsite-ad.png",
    ASSET_DIR / "ai-campus-semiconductor-ad.png",
)
APP_EDITION = os.getenv("APP_EDITION", "free").strip().lower()
IS_PRO_EDITION = APP_EDITION == "pro"
ADMIN_PAGE_TITLE = os.getenv("ADMIN_PAGE_TITLE", "Manage Apple Pro" if IS_PRO_EDITION else "Manage Apple")
ADMIN_LOGIN_DEFAULT_USERNAME = os.getenv(
    "ADMIN_LOGIN_DEFAULT_USERNAME",
    os.getenv("APP_ADMIN_PRO_USERNAME", "adminpro") if IS_PRO_EDITION else os.getenv("APP_ADMIN_USERNAME", "admin"),
)
ADMIN_REQUIRED_ROLE = os.getenv("ADMIN_REQUIRED_ROLE", "admin_pro" if IS_PRO_EDITION else "admin")
CHAT_LLM_PROVIDER = os.getenv("CHAT_LLM_PROVIDER", "openai" if IS_PRO_EDITION else "ollama")
CHAT_PROVIDER_LABEL = "GPT API" if CHAT_LLM_PROVIDER == "openai" else "Local Ollama"
ORCHARD_BACKGROUND_URI = ""
if ORCHARD_BACKGROUND_IMAGE_PATH.exists():
    ORCHARD_BACKGROUND_URI = (
        "data:image/png;base64,"
        + base64.b64encode(ORCHARD_BACKGROUND_IMAGE_PATH.read_bytes()).decode("ascii")
    )

st.set_page_config(page_title=f"{ADMIN_PAGE_TITLE} Admin", page_icon="apple", layout="wide")

st.markdown(
    """
    <style>
    .stApp { background: #f8faf7; color: #17231d; }
    .block-container { max-width: 1360px; padding-top: 2rem; padding-bottom: 3rem; }
    section[data-testid="stSidebar"] {
        background: #fffdf8;
        border-right: 1px solid rgba(23,35,29,.12);
        box-shadow: 8px 0 24px rgba(23,35,29,.035);
    }
    section[data-testid="stSidebar"] > div:first-child {
        padding-top: 1.25rem;
    }
    .hero {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 1rem;
        min-height: 142px;
        padding: 1rem 1.15rem;
        margin-bottom: 1rem;
        background: linear-gradient(90deg, rgba(12,18,14,.78) 0%, rgba(12,18,14,.48) 42%, rgba(255,255,255,.08) 100%), #fffefa;
        background-size: cover;
        background-position: center;
        border: 1px solid rgba(23,35,29,.12);
        border-radius: 8px;
        box-shadow: 0 12px 28px rgba(23,35,29,.13);
    }
    .hero-image {
        display: none;
    }
    .hero .title {
        display: inline-block;
        color: #ffffff;
        background: rgba(12,18,14,.66);
        border: 1px solid rgba(255,255,255,.22);
        border-radius: 8px;
        padding: .42rem .72rem;
        text-shadow: 0 2px 10px rgba(0,0,0,.35);
    }
    .dashboard-panel {
        background: linear-gradient(135deg, #f2f7ef 0%, #fffaf1 100%);
        border: 1px solid rgba(23,35,29,.12);
        border-radius: 8px;
        padding: .2rem 0 .4rem;
        margin-bottom: 1.1rem;
    }
    .dashboard-panel.inventory {
        background: #fffefa;
    }
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.section-shortcuts-marker):not(:has(.section-inventory-marker)):not(:has(.section-listings-marker)) {
        background: rgba(238, 247, 235, .94) !important;
        border-color: rgba(78, 122, 83, .20) !important;
        box-shadow: 0 12px 28px rgba(23,35,29,.075);
        margin-bottom: 1.05rem;
    }
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.section-inventory-marker):not(:has(.section-shortcuts-marker)):not(:has(.section-listings-marker)) {
        background: rgba(255, 247, 226, .94) !important;
        border-color: rgba(170, 122, 38, .20) !important;
        box-shadow: 0 12px 28px rgba(23,35,29,.075);
        margin-bottom: 1.05rem;
    }
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.section-listings-marker):not(:has(.section-shortcuts-marker)):not(:has(.section-inventory-marker)) {
        background: rgba(238, 246, 255, .94) !important;
        border-color: rgba(68, 108, 156, .20) !important;
        box-shadow: 0 12px 28px rgba(23,35,29,.075);
        margin-bottom: 1.05rem;
    }
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.section-shortcuts-marker):not(:has(.section-inventory-marker)):not(:has(.section-listings-marker)) div[data-testid="column"],
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.section-inventory-marker):not(:has(.section-shortcuts-marker)):not(:has(.section-listings-marker)) div[data-testid="column"],
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.section-listings-marker):not(:has(.section-shortcuts-marker)):not(:has(.section-inventory-marker)) div[data-testid="column"] {
        padding-top: .25rem;
        padding-bottom: .35rem;
    }
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.section-shortcuts-marker):not(:has(.section-inventory-marker)):not(:has(.section-listings-marker)) .feature-card {
        background: rgba(255, 254, 250, .96);
        border-color: rgba(78, 122, 83, .18);
    }
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.section-inventory-marker):not(:has(.section-shortcuts-marker)):not(:has(.section-listings-marker)) .product-card {
        background: rgba(255, 254, 250, .96);
        border-color: rgba(170, 122, 38, .18);
    }
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.section-listings-marker):not(:has(.section-shortcuts-marker)):not(:has(.section-inventory-marker)) .product-card,
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.section-listings-marker):not(:has(.section-shortcuts-marker)):not(:has(.section-inventory-marker)) .info-card {
        background: rgba(255, 254, 250, .96);
        border-color: rgba(68, 108, 156, .18);
    }
    .panel-title {
        display: inline-flex;
        align-items: center;
        gap: .35rem;
        background: #17231d;
        color: #fff;
        border-radius: 8px;
        padding: .38rem .68rem;
        font-weight: 950;
        font-size: .96rem;
        margin: .35rem 0 .45rem;
    }
    .kicker { display: none !important; color: #617161; font-size: .82rem; font-weight: 850; }
    .title { color: #17231d; font-size: 2.15rem; line-height: 1.12; font-weight: 900; margin: .15rem 0 .25rem; }
    .section-label { color: #18251f; font-size: 1.02rem; font-weight: 900; margin: .7rem 0 .35rem; }
    .metric-card, .info-card, .product-card, .answer-box, .timeline-card {
        background: #fffefa;
        border: 1px solid rgba(23,35,29,.13);
        border-radius: 8px;
        padding: .9rem 1rem;
        box-shadow: 0 8px 20px rgba(23,35,29,.045);
    }
    .metric-card { min-height: 116px; background: linear-gradient(135deg, #fffefa 0%, #f5fbf2 100%); }
    .metric-card.blue { background: linear-gradient(135deg, #fffefa 0%, #eef6ff 100%); border-color: rgba(36,111,182,.2); }
    .metric-card.warn { background: linear-gradient(135deg, #fffefa 0%, #fff6e5 100%); border-color: rgba(210,139,34,.25); }
    .metric-card.red { background: linear-gradient(135deg, #fffefa 0%, #fff0ef 100%); border-color: rgba(190,55,45,.2); }
    .metric-label { color: #68746b; font-size: .78rem; font-weight: 800; margin-bottom: .25rem; }
    .metric-value { color: #16241d; font-size: 1.48rem; font-weight: 900; line-height: 1.15; }
    .metric-note { color: #7a837b; font-size: .78rem; margin-top: .25rem; }
    .feature-card {
        background: #fffefa;
        border: 1px solid rgba(23,35,29,.13);
        border-radius: 8px;
        padding: .95rem 1rem;
        height: 148px;
        box-sizing: border-box;
        overflow: hidden;
        box-shadow: 0 8px 20px rgba(23,35,29,.045);
        margin-bottom: .35rem;
    }
    .feature-icon { font-size: 1.45rem; margin-bottom: .2rem; }
    .feature-title { color: #17231d; font-weight: 950; font-size: 1.02rem; margin-bottom: .25rem; }
    .feature-metric { color: #16713a; font-weight: 950; font-size: 1.18rem; line-height: 1.2; }
    .feature-note {
        color: #6d7770;
        font-size: .83rem;
        line-height: 1.45;
        margin-top: .22rem;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }
    .answer-box { color: #26362d; line-height: 1.7; margin-top: .3rem; }
    .product-card { margin-bottom: .85rem; }
    .product-title { color: #17231d; font-weight: 900; font-size: 1.03rem; margin-bottom: .2rem; }
    .product-meta { color: #56635b; line-height: 1.55; font-size: .9rem; }
    .pill {
        display: inline-block;
        background: #eef3e7;
        border: 1px solid rgba(63,89,67,.18);
        color: #35473b;
        border-radius: 999px;
        padding: .12rem .5rem;
        margin: .12rem .16rem .12rem 0;
        font-size: .78rem;
        font-weight: 750;
    }
    .price { color: #a33528; font-weight: 900; font-size: 1.18rem; }
    .quiet { color: #717b73; font-size: .86rem; line-height: 1.55; }
    .side-brand { padding: .55rem 0 .8rem; border-bottom:1px solid rgba(23,35,29,.1); margin-bottom:.75rem; }
    .side-logo { font-size:1.45rem; font-weight:950; color:#15231c; }
    .side-sub { display: none !important; color:#6d7770; font-size:.78rem; }
    .side-menu-item { padding:.58rem .7rem; border-radius:8px; color:#223028; font-weight:850; margin:.16rem 0; }
    .side-menu-item.active { background:#16713a; color:#fff; }
    .status-card {
        display: none !important;
        background:#fffefa; border:1px solid rgba(23,35,29,.12); border-radius:8px;
        padding:.75rem; margin-top:1rem; color:#25342b; font-size:.84rem; line-height:1.7;
    }
    section[data-testid="stSidebar"] div[data-testid="stCaptionContainer"] {
        display: none !important;
    }
    .side-ad {
        background: #fffefa;
        border: 1px solid rgba(23,35,29,.13);
        border-radius: 8px;
        padding: .82rem;
        box-shadow: 0 8px 20px rgba(23,35,29,.045);
        margin-top: .8rem;
    }
    .side-ad-label {
        color: #c9281f;
        font-size: .76rem;
        font-weight: 950;
        margin-bottom: .25rem;
    }
    .side-ad-title {
        color: #17231d;
        font-size: 1rem;
        line-height: 1.32;
        font-weight: 950;
        margin-bottom: .35rem;
    }
    .side-ad-copy {
        color: #5e6961;
        font-size: .84rem;
        line-height: 1.45;
        margin-bottom: .65rem;
    }
    .side-ad-image {
        width: 100%;
        height: 118px;
        object-fit: cover;
        border-radius: 8px;
        border: 1px solid rgba(23,35,29,.08);
        display: block;
    }
    .right-ad-rail {
        position: fixed;
        top: 5.25rem;
        right: 1.15rem;
        width: 306px;
        z-index: 50;
        display: flex;
        flex-direction: column;
        gap: .8rem;
    }
    .right-ad-rail img {
        width: 100%;
        max-height: calc((100vh - 7.8rem) / 2);
        object-fit: contain;
        border-radius: 8px;
        border: 1px solid rgba(23,35,29,.16);
        box-shadow: 0 14px 32px rgba(23,35,29,.16);
        background: #54c6ef;
        display: block;
    }
    @media (min-width: 1500px) {
        .block-container { padding-right: 342px; }
    }
    @media (max-width: 1499px) {
        .right-ad-rail {
            position: static;
            width: min(100%, 380px);
            margin: 0 0 1rem auto;
        }
        .right-ad-rail img {
            max-height: 460px;
        }
    }
    .timeline-item {
        border-left: 3px solid #16713a;
        padding: .25rem 0 .65rem .7rem;
        margin-left: .2rem;
        color:#2d3b32;
        font-size:.86rem;
        line-height:1.55;
    }
    .timeline-time { color:#7a847d; font-size:.75rem; font-weight:800; }
    div[data-testid="stButton"] button { border-radius: 8px; font-weight: 850; }
    div[data-testid="stButton"] button {
        transition: background-color .14s ease, color .14s ease, border-color .14s ease;
    }
    section[data-testid="stSidebar"] div[data-testid="stButton"] button {
        justify-content: flex-start;
        width: 100%;
        border: 0;
        background: transparent;
        color: #223028;
        box-shadow: none;
        padding: .58rem .7rem;
    }
    section[data-testid="stSidebar"] div[data-testid="stButton"] button[kind="primary"] {
        background: #16713a;
        color: #fff;
    }
    div[data-testid="stButton"] button[kind="secondary"]:hover,
    section[data-testid="stSidebar"] div[data-testid="stButton"] button:hover,
    section[data-testid="stSidebar"] div[data-testid="stButton"] button[kind="primary"]:hover {
        background: #eef0ef !important;
        color: #c9281f !important;
        border-color: #d7ddda !important;
        box-shadow: none !important;
    }
    div[data-testid="stTextArea"] textarea,
    div[data-testid="stTextInput"] input,
    div[data-testid="stNumberInput"] input,
    div[data-testid="stSelectbox"] div { border-radius: 8px; }
    div[data-testid="stExpander"] {
        background: #fffefa;
        border: 1px solid rgba(23,35,29,.13);
        border-radius: 8px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def api_get(path: str):
    response = requests.get(f"{API_BASE_URL}{path}", timeout=20)
    response.raise_for_status()
    return response.json()


def api_post(path: str, payload: dict | None = None, timeout: int = 30):
    response = requests.post(f"{API_BASE_URL}{path}", json=payload, timeout=timeout)
    response.raise_for_status()
    return response.json()


def api_put(path: str, payload: dict):
    response = requests.put(f"{API_BASE_URL}{path}", json=payload, timeout=30)
    response.raise_for_status()
    return response.json()


def fetch_shop_settings() -> dict:
    try:
        return api_get("/sales/settings/shop")
    except requests.RequestException:
        return {"shop_page_title": "Apple Market"}


@st.cache_data(ttl=30)
def fetch_products() -> list:
    return api_get("/sales/products")


@st.cache_data(ttl=30)
def fetch_listings() -> list:
    return api_get("/sales/listings")


@st.cache_data(ttl=30)
def fetch_orders() -> list:
    return api_get("/sales/orders")


def clear_sales_cache() -> None:
    fetch_products.clear()
    fetch_listings.clear()
    fetch_orders.clear()


@st.cache_data
def image_data_uri(path: Path) -> str:
    if not path.exists():
        return ""
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def format_won(value: int) -> str:
    return f"{int(value):,}원"


def format_kg(value: float) -> str:
    numeric_value = float(value)
    if numeric_value.is_integer():
        return f"{int(numeric_value):,}kg"
    return f"{numeric_value:,.2f}kg"


def item_name(item: dict) -> str:
    return f"{item['product_name']} {item['size_class']}과 {item['grade']} 등급"


def render_metric(label: str, value: str, note: str = "", tone: str = "") -> None:
    class_name = f"metric-card {tone}".strip()
    st.markdown(
        f"""
        <div class="{class_name}">
          <div class="metric-label">{html.escape(label)}</div>
          <div class="metric-value">{html.escape(value)}</div>
          <div class="metric-note">{html.escape(note)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_feature_card(
    icon: str,
    title: str,
    metric: str,
    note: str,
    page_name: str,
) -> None:
    st.markdown(
        f"""
        <div class="feature-card">
          <div class="feature-icon">{html.escape(icon)}</div>
          <div class="feature-title">{html.escape(title)}</div>
          <div class="feature-metric">{html.escape(metric)}</div>
          <div class="feature-note">{html.escape(note)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button(f"{title}로 이동", key=f"dashboard_go_{page_name}", use_container_width=True):
        st.session_state.admin_page = page_name
        st.rerun()


def render_product_card(product: dict) -> None:
    st.markdown(
        f"""
        <div class="product-card">
          <div class="product-title">{html.escape(item_name(product))}</div>
          <div>
            <span class="pill">추정 {float(product['estimated_unit_weight_kg']):.2f}kg/개</span>
            <span class="pill">{html.escape(product['package_unit'])}</span>
          </div>
          <div class="product-meta">
            기준 재고 {format_kg(product['base_available_kg'])} · 쇼핑몰 등록 {format_kg(product['listed_kg'])}<br>
            추가 등록 가능 <strong>{format_kg(product['available_kg'])}</strong> · 판매 완료 {format_kg(product['sold_kg'])}<br>
            <span class="price">{format_won(product['recommended_price_per_kg'])}/kg</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_recent_orders(orders: list[dict], limit: int = 4) -> None:
    st.markdown('<div class="section-label">최근 주문 알림</div>', unsafe_allow_html=True)
    recent_orders = orders[:limit]
    if recent_orders:
        for order in recent_orders:
            with st.container(border=True):
                st.caption(order["created_at"])
                st.write(
                    f"주문 #{int(order['id']):04d} · "
                    f"{int(order['quantity_kg']):,}kg · "
                    f"{format_won(order['total_amount'])}"
                )
    else:
        st.markdown('<div class="info-card quiet">아직 주문 데이터가 없습니다.</div>', unsafe_allow_html=True)


def submit_chat_question(question: str) -> None:
    spinner_text = (
        "GPT API가 답변을 생성하는 중입니다..."
        if IS_PRO_EDITION
        else "로컬 LLM이 답변을 생성하는 중입니다..."
    )
    with st.spinner(spinner_text):
        try:
            response = requests.post(
                CHAT_API_URL,
                json={
                    "question": question,
                    "session_id": st.session_state.session_id,
                    "llm_provider": CHAT_LLM_PROVIDER,
                },
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
            st.session_state.chat_history = st.session_state.chat_history[-20:]
            st.session_state.last_answer = data["answer"]
            st.session_state.last_sources = data.get("sources", [])


def render_chat_thread() -> None:
    if not st.session_state.chat_history:
        st.markdown(
            '<div class="info-card quiet">아직 대화가 없습니다. 추천 질문을 누르거나 직접 질문을 입력해보세요.</div>',
            unsafe_allow_html=True,
        )
        return

    with st.container(height=420):
        for turn in st.session_state.chat_history:
            with st.chat_message("user"):
                st.write(turn["user"])
            with st.chat_message("assistant"):
                st.write(turn["assistant"])


def render_ai_assistant(show_sources: bool = True) -> None:
    st.markdown('<div class="section-label">AI 도우미</div>', unsafe_allow_html=True)
    render_chat_thread()

    example_questions = [
        "중과 하 재고 알려줘",
        "대과 상 50키로 쇼핑몰에 올려줘",
        "1달 내에 가장 팔기 좋은 날이 언제야?",
    ]
    example_cols = st.columns(3)
    for col, example in zip(example_cols, example_questions):
        if col.button(example, use_container_width=True):
            st.session_state.question = example
            submit_chat_question(example)
            st.rerun()

    question = st.text_area(
        "AI 도우미 질문",
        placeholder="예: 중과 하 재고 알려줘",
        height=118,
        key="question",
        label_visibility="collapsed",
    )
    if st.button("질문하기", type="primary", disabled=not question.strip()):
        submit_chat_question(question)
        st.rerun()

    if show_sources and st.session_state.last_sources:
        with st.expander("검색된 문서 chunk"):
            for source in st.session_state.last_sources:
                st.markdown(
                    f"**{source['source_path']} / chunk {source['chunk_index']}** "
                    f"(distance: {source['distance']:.4f})"
                )
                st.write(source["content"])


def read_news_summaries(limit: int = 5) -> list[dict[str, str]]:
    if not NEWS_DOC_PATH.exists():
        return []

    try:
        lines = NEWS_DOC_PATH.read_text(encoding="utf-8").splitlines()
    except Exception:
        return []

    articles: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for line in lines:
        title_match = re.match(r"^\d+\. (.+)", line)
        if title_match:
            if current:
                articles.append(current)
            current = {"title": title_match.group(1).strip(), "summary": ""}
            continue
        if current and line.strip().startswith("- 요약:"):
            current["summary"] = line.split(":", 1)[1].strip()

    if current:
        articles.append(current)
    return articles[:limit]


def render_news_summary(limit: int = 5) -> None:
    st.markdown('<div class="section-label">최신 뉴스 요약</div>', unsafe_allow_html=True)
    articles = read_news_summaries(limit)
    if not articles:
        st.markdown('<div class="info-card quiet">아직 표시할 뉴스 요약이 없습니다.</div>', unsafe_allow_html=True)
        return

    for article in articles:
        st.markdown(
            f"""
            <div class="answer-box">
              <strong>{html.escape(article['title'])}</strong><br>
              <span class="quiet">{html.escape(article['summary'])}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )


def latest_price_info() -> tuple[str, str]:
    if not PRICE_DATA_PATH.exists():
        return "없음", "시세 CSV 없음"

    latest_date = "확인 필요"
    try:
        with PRICE_DATA_PATH.open(encoding="utf-8-sig", newline="") as file:
            rows = list(csv.DictReader(file))
        if rows:
            latest_date = max(row["date"] for row in rows if row.get("date"))
    except Exception:
        latest_date = "확인 실패"

    doc_status = "예측 문서 있음" if FORECAST_DOC_PATH.exists() else "예측 문서 없음"
    return latest_date, doc_status


def latest_news_info() -> tuple[str, str]:
    if not NEWS_DOC_PATH.exists():
        return "없음", "뉴스 문서 없음"

    try:
        content = NEWS_DOC_PATH.read_text(encoding="utf-8")
    except Exception:
        return "확인 실패", "뉴스 문서 읽기 실패"

    generated_at = "확인 필요"
    for line in content.splitlines():
        if line.startswith("업데이트 시각:"):
            generated_at = line.replace("업데이트 시각:", "", 1).strip()
            break
        if line.startswith("갱신 시각:"):
            generated_at = line.replace("갱신 시각:", "", 1).strip()
            break

    article_count = sum(1 for line in content.splitlines() if re.match(r"^\d+\. ", line))
    return generated_at, f"요약 기사 {article_count}개"


@st.fragment(run_every="5s")
def render_notification_toasts() -> None:
    try:
        notifications = api_get("/sales/notifications")
    except requests.RequestException:
        return

    if not st.session_state.toast_notifications_ready:
        st.session_state.last_toasted_notification_id = max(
            [int(notification["id"]) for notification in notifications],
            default=0,
        )
        st.session_state.toast_notifications_ready = True
        return

    toastable_notifications = [
        notification
        for notification in notifications
        if (
            not notification["is_read"]
            and notification["event_type"] in {"order_created", "listing_registered"}
            and int(notification["id"]) > int(st.session_state.last_toasted_notification_id)
        )
    ]
    for notification in reversed(toastable_notifications):
        st.toast(f"{notification['title']}\n\n{notification['message']}")

    latest_notification_id = max(
        [int(notification["id"]) for notification in notifications],
        default=int(st.session_state.last_toasted_notification_id),
    )
    st.session_state.last_toasted_notification_id = max(
        int(st.session_state.last_toasted_notification_id),
        latest_notification_id,
    )


def render_free_right_ad() -> None:
    if IS_PRO_EDITION:
        return

    image_tags = []
    for path in FREE_PROMO_IMAGE_PATHS:
        image_uri = image_data_uri(path)
        if image_uri:
            image_tags.append(f'<img src="{image_uri}" alt="AI campus bootcamp ad">')

    if not image_tags:
        return

    st.markdown(
        """
        <aside class="right-ad-rail">
          {images}
        </aside>
        """.format(images="\n".join(image_tags)),
        unsafe_allow_html=True,
    )


def render_notifications_panel() -> None:
    try:
        notifications = api_get("/sales/notifications")
    except requests.RequestException as exc:
        st.error(f"알림을 불러오지 못했습니다: {exc}")
        return

    if not notifications:
        st.info("아직 알림이 없습니다.")
        return

    for notification in notifications:
        state = "읽음" if notification["is_read"] else "새 알림"
        with st.expander(f"{state} | {notification['title']}"):
            st.write(notification["message"])
            st.caption(notification["created_at"])
            if not notification["is_read"]:
                if st.button("읽음 처리", key=f"read_{notification['id']}"):
                    try:
                        api_post(f"/sales/notifications/{notification['id']}/read")
                    except requests.RequestException as exc:
                        st.error(f"읽음 처리 실패: {exc}")
                    else:
                        st.rerun()


if "question" not in st.session_state:
    st.session_state.question = ""
if "session_id" not in st.session_state:
    st.session_state.session_id = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "last_answer" not in st.session_state:
    st.session_state.last_answer = None
if "last_sources" not in st.session_state:
    st.session_state.last_sources = []
if "last_toasted_notification_id" not in st.session_state:
    st.session_state.last_toasted_notification_id = 0
if "toast_notifications_ready" not in st.session_state:
    st.session_state.toast_notifications_ready = False
if "admin_page" not in st.session_state:
    st.session_state.admin_page = "대시보드"
legacy_pages = {
    "챗봇": "AI 도우미",
    "판매등록": "판매상품등록",
    "등록상품": "판매중인상품",
    "쇼핑몰 재고": "판매중인상품",
    "시세갱신": "가격 정보 업데이트",
    "뉴스갱신": "최신 뉴스 업데이트",
}
if st.session_state.admin_page in legacy_pages:
    st.session_state.admin_page = legacy_pages[st.session_state.admin_page]


def set_session_value(key: str, value: str) -> None:
    st.session_state[key] = value


def require_login() -> dict:
    if "admin_user" in st.session_state:
        return st.session_state.admin_user

    st.markdown(f'<div class="title">{html.escape(ADMIN_PAGE_TITLE)}</div>', unsafe_allow_html=True)
    with st.form("admin_login_form"):
        username = st.text_input("아이디", value=ADMIN_LOGIN_DEFAULT_USERNAME)
        password = st.text_input("비밀번호", type="password")
        submitted = st.form_submit_button("로그인", type="primary", use_container_width=True)

    if submitted:
        try:
            user = api_post("/auth/login", {"username": username, "password": password})
        except requests.RequestException:
            st.error("로그인 실패: 아이디와 비밀번호를 확인하세요.")
        else:
            if user["role"] != ADMIN_REQUIRED_ROLE:
                st.error("이 페이지에 접근할 수 있는 관리자 계정이 아닙니다.")
            else:
                st.session_state.admin_user = user
                st.rerun()

    st.stop()


admin_user = require_login()

render_notification_toasts()


with st.sidebar:
    st.markdown(
        """
        <div class="side-brand">
          <div class="side-logo">{title}</div>
          <div class="side-sub">{edition}</div>
        </div>
        """.format(
            title=html.escape(ADMIN_PAGE_TITLE),
            edition="GPT API Pro 시스템" if IS_PRO_EDITION else "AI 과일 자동화 시스템",
        ),
        unsafe_allow_html=True,
    )
    nav_items = [
        ("대시보드", "📊  대시보드"),
        ("판매상품등록", "📝  판매상품등록"),
        ("판매중인상품", "🍎  판매중인상품"),
        ("판매페이지 관리", "🛒  판매페이지 관리"),
        ("AI 도우미", "🤖  AI 도우미"),
        ("가격 정보 업데이트", "🔄  가격 정보 업데이트"),
        ("최신 뉴스 업데이트", "📰  최신 뉴스 업데이트"),
        ("알림", "🔔  알림"),
    ]
    for page_name, label in nav_items:
        if st.button(
            label,
            key=f"nav_{page_name}",
            type="primary" if st.session_state.admin_page == page_name else "secondary",
            use_container_width=True,
        ):
            st.session_state.admin_page = page_name
            st.rerun()
    selected_page = st.session_state.admin_page
    st.markdown(
        """
        <div class="status-card">
          <strong>시스템 상태</strong><br>
          FastAPI 정상<br>
          MariaDB 정상<br>
          {llm_status}<br>
          {embedding_status}<br>
          Chronos 시세예측 정상
        </div>
        """.format(
            llm_status="GPT API 정상" if IS_PRO_EDITION else "Ollama Qwen 정상",
            embedding_status="OpenAI 임베딩 정상" if IS_PRO_EDITION else "bge-m3 임베딩 정상",
        ),
        unsafe_allow_html=True,
    )
    st.markdown("<div style='height: 1.2rem'></div>", unsafe_allow_html=True)
    if st.button("로그아웃", key="sidebar_logout", use_container_width=True):
        st.session_state.pop("admin_user", None)
        st.rerun()

render_free_right_ad()

title_image_uri = image_data_uri(ADMIN_TITLE_IMAGE_PATH)
hero_background_style = (
    f' style="background-image: linear-gradient(90deg, rgba(12,18,14,.80) 0%, rgba(12,18,14,.56) 44%, rgba(255,255,255,.06) 100%), url({title_image_uri});"'
    if title_image_uri
    else ""
)
st.markdown(
    """
    <div class="hero"{hero_background_style}>
      <div>
        <div class="kicker">{kicker}</div>
        <div class="title">{title}</div>
      </div>
    </div>
    """.format(
        hero_background_style=hero_background_style,
        kicker=(
            "GPT API · CLOUD BACKEND · SALES OPS"
            if IS_PRO_EDITION
            else "LOCAL LLM · ROBOT HARVEST · SALES OPS"
        ),
        title=html.escape(ADMIN_PAGE_TITLE),
    ),
    unsafe_allow_html=True,
)

if ORCHARD_BACKGROUND_URI:
    st.markdown(
        f"""
        <style>
        .stApp {{
            background:
                linear-gradient(rgba(248, 250, 247, .74), rgba(248, 250, 247, .82)),
                url("{ORCHARD_BACKGROUND_URI}") center center / cover fixed no-repeat !important;
        }}
        .block-container {{
            background: rgba(255, 253, 248, .86);
            border: 1px solid rgba(23,35,29,.12);
            border-radius: 10px;
            box-shadow: 0 18px 44px rgba(23,35,29,.12);
            padding-left: 1.35rem;
            padding-right: 1.35rem;
            margin-top: .85rem;
        }}
        div[data-testid="stVerticalBlockBorderWrapper"] {{
            background: rgba(255, 254, 250, .94);
            backdrop-filter: blur(2px);
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

try:
    products = fetch_products()
except requests.RequestException as exc:
    st.error(f"재고 정보를 불러오지 못했습니다: {exc}")
    products = []

try:
    listings = fetch_listings()
except requests.RequestException:
    listings = []

try:
    orders = fetch_orders()
except requests.RequestException:
    orders = []

active_listings = [listing for listing in listings if listing["status"] == "active"]
latest_date, doc_status = latest_price_info()
latest_news_date, news_doc_status = latest_news_info()

if selected_page == "대시보드":
    total_available_kg = sum(float(product["available_kg"]) for product in products)
    total_listed_kg = sum(int(product["listed_kg"]) for product in products)

    with st.container(border=True):
        st.markdown(
            '<span class="section-shortcuts-marker"></span><div class="panel-title">📊 기능 바로가기</div>',
            unsafe_allow_html=True,
        )
        feature_cards = [
            (
                "🤖",
                "AI 도우미",
                CHAT_PROVIDER_LABEL,
                "재고, 시세, 판매 판단을 질문으로 확인합니다.",
                "AI 도우미",
            ),
            (
                "📝",
                "판매상품등록",
                format_kg(total_available_kg),
                "쇼핑몰에 추가 등록 가능한 재고를 상품으로 올립니다.",
                "판매상품등록",
            ),
            (
                "🍎",
                "판매중인상품",
                f"{len(active_listings)}개",
                f"현재 쇼핑몰 등록량 {total_listed_kg:,}kg을 확인합니다.",
                "판매중인상품",
            ),
            (
                "🔄",
                "가격 정보 업데이트",
                latest_date,
                "시세 수집, 예측 문서 생성, RAG 반영을 실행합니다.",
                "가격 정보 업데이트",
            ),
            (
                "📰",
                "최신 뉴스 업데이트",
                latest_news_date,
                "과일 뉴스를 수집하고 요약 문서로 반영합니다.",
                "최신 뉴스 업데이트",
            ),
            (
                "🔔",
                "알림",
                f"{len(orders)}건",
                "주문 접수와 판매 등록 알림을 확인합니다.",
                "알림",
            ),
        ]
        for row_start in range(0, len(feature_cards), 3):
            card_cols = st.columns(3)
            for col, card in zip(card_cols, feature_cards[row_start : row_start + 3]):
                with col:
                    render_feature_card(*card)

    with st.container(border=True):
        st.markdown(
            '<span class="section-inventory-marker"></span><div class="panel-title">🍎 재고 요약</div>',
            unsafe_allow_html=True,
        )
        inventory_cols = st.columns(3, gap="medium")
        for index, product in enumerate(products[:6]):
            with inventory_cols[index % 3]:
                render_product_card(product)

    with st.container(border=True):
        st.markdown(
            '<span class="section-listings-marker"></span><div class="panel-title">🛒 판매중인 상품</div>',
            unsafe_allow_html=True,
        )
        if active_listings:
            listing_cols = st.columns(3, gap="medium")
            for index, listing in enumerate(active_listings[:6]):
                with listing_cols[index % 3]:
                    total_amount = int(listing["quantity_kg"]) * int(listing["price_per_kg"])
                    st.markdown(
                        f"""
                        <div class="product-card">
                          <div class="product-title">{html.escape(item_name(listing))}</div>
                          <div>
                            <span class="pill">{html.escape(listing['package_unit'])}</span>
                            <span class="pill">남은 수량 {int(listing['quantity_kg']):,}kg</span>
                          </div>
                          <div class="product-meta">
                            <span class="price">{format_won(listing['price_per_kg'])}/kg</span><br>
                            판매 가능 금액 {total_amount:,}원
                          </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
        else:
            st.markdown('<div class="info-card quiet">판매중인 상품이 없습니다.</div>', unsafe_allow_html=True)

if selected_page == "판매페이지 관리":
    st.markdown('<div class="section-label">🛒 판매페이지 관리</div>', unsafe_allow_html=True)
    settings = fetch_shop_settings()
    current_title = settings.get("shop_page_title", "Apple Market")

    with st.container(border=True):
        shop_page_title = st.text_input(
            "판매페이지 제목",
            value=current_title,
            max_chars=80,
        )
        if st.button("제목 저장", type="primary", use_container_width=True):
            try:
                updated = api_put(
                    "/sales/settings/shop",
                    {"shop_page_title": shop_page_title.strip()},
                )
            except requests.RequestException as exc:
                st.error(f"판매페이지 제목 저장 실패: {exc}")
            else:
                st.success(f"판매페이지 제목을 '{updated['shop_page_title']}'로 저장했습니다.")
                st.rerun()

if selected_page == "AI 도우미":
    render_ai_assistant(show_sources=True)

if selected_page == "판매상품등록":
    st.markdown('<div class="section-label">📝 판매상품등록</div>', unsafe_allow_html=True)
    if products:
        labels = [
            f"{item_name(item)} · 추가 가능 {format_kg(item['available_kg'])} · {format_won(item['recommended_price_per_kg'])}/kg"
            for item in products
        ]
        selected_label = st.selectbox("재고 선택", labels)
        product = products[labels.index(selected_label)]
        max_quantity = max(int(product["available_kg"]), 1)
        default_quantity = min(max_quantity, 100)

        form_col, preview_col = st.columns([1.2, 1])
        with form_col:
            quantity_kg = st.number_input(
                "판매 수량(kg)",
                min_value=1,
                max_value=max_quantity,
                value=default_quantity,
                step=10,
            )
            price_per_kg = st.number_input(
                "kg당 판매가",
                min_value=1,
                value=int(product["recommended_price_per_kg"]),
                step=100,
            )
            package_unit = st.text_input("판매 단위", value=product["package_unit"])
            sales_channel = st.text_input("판매 채널", value=product["sales_channel"])
            default_description = (
                f"{item_name(product)}를 {package_unit} 단위로 판매합니다. "
                f"선별 기준을 통과한 상품으로, 주문 확인 후 신선하게 출고합니다."
            )
            description = st.text_area("상품 설명", value=default_description, height=118)

        with preview_col:
            st.markdown(
                f"""
                <div class="product-card">
                  <div class="product-title">{html.escape(item_name(product))}</div>
                  <div class="product-meta">
                    추가 등록 가능 <strong>{format_kg(product['available_kg'])}</strong><br>
                    추천 판매가 <span class="price">{format_won(product['recommended_price_per_kg'])}/kg</span><br>
                    등록 예정 수량 {int(quantity_kg):,}kg
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        payload = {
            "product_name": product["product_name"],
            "size_class": product["size_class"],
            "grade": product["grade"],
            "quantity_kg": int(quantity_kg),
            "estimated_unit_weight_kg": float(product["estimated_unit_weight_kg"]),
            "price_per_kg": int(price_per_kg),
            "package_unit": package_unit,
            "sales_channel": sales_channel,
            "description": description,
        }
        if st.button("상품등록", type="primary", use_container_width=True):
            try:
                draft = api_post("/sales/drafts", payload)
                listing = api_post(f"/sales/drafts/{draft['id']}/register")
            except requests.RequestException as exc:
                st.error(f"상품등록 실패: {exc}")
            else:
                clear_sales_cache()
                st.success(f"{item_name(listing)} {int(listing['quantity_kg']):,}kg을 판매중인상품에 등록했습니다.")
                st.rerun()
    else:
        st.info("등록 가능한 재고가 없습니다.")

if selected_page == "판매중인상품":
    st.markdown('<div class="section-label">🍎 판매중인상품</div>', unsafe_allow_html=True)
    if not active_listings:
        st.info("판매 등록된 상품이 아직 없습니다.")
    listing_cols = st.columns(3)
    for index, listing in enumerate(active_listings):
        with listing_cols[index % 3]:
            total_amount = int(listing["quantity_kg"]) * int(listing["price_per_kg"])
            st.markdown(
                f"""
                <div class="product-card">
                  <div class="product-title">{html.escape(item_name(listing))}</div>
                  <div>
                    <span class="pill">{html.escape(listing['package_unit'])}</span>
                    <span class="pill">최초 {int(listing.get('original_quantity_kg', listing['quantity_kg'])):,}kg</span>
                  </div>
                  <div class="product-meta">
                    남은 판매수량 <strong>{int(listing['quantity_kg']):,}kg</strong><br>
                    <span class="price">{format_won(listing['price_per_kg'])}/kg</span><br>
                    남은 재고 기준 금액 {total_amount:,}원
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

if selected_page == "가격 정보 업데이트":
    st.markdown('<div class="section-label">🔄 가격 정보 업데이트</div>', unsafe_allow_html=True)
    price_cols = st.columns(3)
    with price_cols[0]:
        render_metric("최신 관측일", latest_date, "가락시장 CSV 기준")
    with price_cols[1]:
        render_metric("예측 문서", doc_status, "Chronos mini RAG")
    with price_cols[2]:
        render_metric("업데이트 방식", "수동 실행", "크롤링·예측·재임베딩")

    if st.button("가격 정보 업데이트", type="primary"):
        with st.spinner("시세 수집, 예측, RAG 반영을 진행하는 중입니다..."):
            try:
                result = api_post("/prices/refresh", timeout=600)
            except requests.RequestException as exc:
                st.error(f"가격 정보 업데이트 실패: {exc}")
            else:
                st.success("시세 예측 RAG 문서를 업데이트했습니다.")

if selected_page == "최신 뉴스 업데이트":
    st.markdown('<div class="section-label">📰 최신 뉴스 업데이트</div>', unsafe_allow_html=True)
    news_cols = st.columns(3)
    with news_cols[0]:
        render_metric("최근 뉴스 문서 업데이트", latest_news_date, "fruit_news_2026.md 기준")
    with news_cols[1]:
        render_metric("뉴스 요약 상태", news_doc_status, "원문 저장 없이 요약 저장")
    with news_cols[2]:
        render_metric("업데이트 방식", "수동 실행", "뉴스 수집·요약·재임베딩")

    render_news_summary(limit=5)
    if st.button("최신 뉴스 업데이트", type="primary"):
        with st.spinner("뉴스 수집, 요약 문서 생성, RAG 반영을 진행하는 중입니다..."):
            try:
                result = api_post("/news/refresh", timeout=240)
            except requests.RequestException as exc:
                st.error(f"최신 뉴스 업데이트 실패: {exc}")
            else:
                st.success("과일 뉴스 요약 RAG 문서를 업데이트했습니다.")

if selected_page == "알림":
    st.markdown('<div class="section-label">🔔 농부 알림</div>', unsafe_allow_html=True)
    render_notifications_panel()
