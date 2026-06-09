import csv
import html
import os
from pathlib import Path

import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

CHAT_API_URL = os.getenv("CHAT_API_URL", "http://localhost:8000/chat")
API_BASE_URL = CHAT_API_URL.rsplit("/", 1)[0]
PROJECT_ROOT = Path(__file__).resolve().parents[2]
PRICE_DATA_PATH = PROJECT_ROOT / "fruits_data" / "garak_apple_prices.csv"
FORECAST_DOC_PATH = PROJECT_ROOT / "rag_docs" / "apple_price_forecast_chronos_mini.md"

st.set_page_config(page_title="Manage Apple Admin", page_icon="apple", layout="wide")

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
        padding: .8rem 0 .65rem;
        margin-bottom: .7rem;
    }
    .kicker { color: #617161; font-size: .82rem; font-weight: 850; }
    .title { color: #17231d; font-size: 2.15rem; line-height: 1.12; font-weight: 900; margin: .15rem 0 .25rem; }
    .subtitle { color: #5b675f; font-size: .98rem; line-height: 1.55; max-width: 760px; }
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
    .answer-box { color: #26362d; line-height: 1.7; margin-top: .3rem; }
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
    .side-sub { color:#6d7770; font-size:.78rem; }
    .side-menu-item { padding:.58rem .7rem; border-radius:8px; color:#223028; font-weight:850; margin:.16rem 0; }
    .side-menu-item.active { background:#16713a; color:#fff; }
    .status-card {
        background:#fffefa; border:1px solid rgba(23,35,29,.12); border-radius:8px;
        padding:.75rem; margin-top:1rem; color:#25342b; font-size:.84rem; line-height:1.7;
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


def format_won(value: int) -> str:
    return f"{int(value):,}원"


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
            기준 재고 {int(product['base_available_kg']):,}kg · 쇼핑몰 등록 {int(product['listed_kg']):,}kg<br>
            추가 등록 가능 <strong>{int(product['available_kg']):,}kg</strong> · 판매 완료 {int(product['sold_kg']):,}kg<br>
            <span class="price">{format_won(product['recommended_price_per_kg'])}/kg</span>
          </div>
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


@st.fragment(run_every="5s")
def render_live_notification_sidebar() -> None:
    st.markdown("### 실시간 알림")
    try:
        notifications = api_get("/sales/notifications")
    except requests.RequestException:
        st.error("알림 연결 대기 중")
        return

    unread = [notification for notification in notifications if not notification["is_read"]]
    st.caption(f"새 알림 {len(unread)}개")
    if not st.session_state.toast_notifications_ready:
        st.session_state.last_toasted_notification_id = max(
            [int(notification["id"]) for notification in notifications],
            default=0,
        )
        st.session_state.toast_notifications_ready = True

    toastable_notifications = [
        notification
        for notification in notifications
        if (
            not notification["is_read"]
            and notification["event_type"] == "order_created"
            and int(notification["id"]) > int(st.session_state.last_toasted_notification_id)
        )
    ]
    for notification in reversed(toastable_notifications):
        st.toast(f"{notification['title']}\n\n{notification['message']}")
        st.session_state.last_toasted_notification_id = max(
            int(st.session_state.last_toasted_notification_id),
            int(notification["id"]),
        )

    for notification in notifications[:4]:
        marker = "●" if not notification["is_read"] else "○"
        st.markdown(
            f"**{marker} {html.escape(notification['title'])}**  \n"
            f"{html.escape(notification['message'])}"
        )


@st.fragment(run_every="5s")
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


def set_session_value(key: str, value: str) -> None:
    st.session_state[key] = value


with st.sidebar:
    st.markdown(
        """
        <div class="side-brand">
          <div class="side-logo">Manage Apple</div>
          <div class="side-sub">AI 과일 자동화 시스템</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    nav_items = [
        ("대시보드", "▣  대시보드"),
        ("챗봇", "◌  챗봇"),
        ("판매등록", "□  판매등록"),
        ("쇼핑몰 재고", "▤  쇼핑몰 재고"),
        ("등록상품", "▥  등록상품"),
        ("시세갱신", "↻  시세갱신"),
        ("알림", "!  알림"),
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
          Ollama Qwen 정상<br>
          bge-m3 임베딩 정상<br>
          Chronos 시세예측 정상
        </div>
        """,
        unsafe_allow_html=True,
    )
    render_live_notification_sidebar()

st.markdown(
    """
    <div class="hero">
      <div class="kicker">LOCAL LLM · ROBOT HARVEST · SALES OPS</div>
      <div class="title">Manage Apple</div>
      <div class="subtitle">로봇 수확 이벤트, 사과 재고, 쇼핑몰 등록, 주문 알림, 시세예측 RAG 갱신을 한 화면에서 관리합니다.</div>
    </div>
    """,
    unsafe_allow_html=True,
)

try:
    products = api_get("/sales/products")
except requests.RequestException as exc:
    st.error(f"재고 정보를 불러오지 못했습니다: {exc}")
    products = []

try:
    listings = api_get("/sales/listings")
except requests.RequestException:
    listings = []

try:
    orders = api_get("/sales/orders")
except requests.RequestException:
    orders = []

active_listings = [listing for listing in listings if listing["status"] == "active"]
total_base_stock = sum(int(product["base_available_kg"]) for product in products)
total_listed_stock = sum(int(product["listed_kg"]) for product in products)
total_available_stock = sum(int(product["available_kg"]) for product in products)
latest_date, doc_status = latest_price_info()

metric_cols = st.columns(4)
with metric_cols[0]:
    render_metric("총 기준 재고", f"{total_base_stock:,}kg", "대과/중과 더미 기준")
with metric_cols[1]:
    render_metric("쇼핑몰 등록 재고", f"{total_listed_stock:,}kg", f"활성 상품 {len(active_listings)}개", "blue")
with metric_cols[2]:
    render_metric("추가 등록 가능", f"{total_available_stock:,}kg", "등록 가능한 잔여 재고", "warn")
with metric_cols[3]:
    render_metric("최근 주문", f"{len(orders):,}건", f"최신 시세 {latest_date}", "red")

if selected_page == "대시보드":
    dash_left, dash_right = st.columns([1.35, 1])
    with dash_left:
        st.markdown('<div class="section-label">챗봇</div>', unsafe_allow_html=True)
        dashboard_question = st.text_input(
            "대시보드 질문",
            placeholder="예: 중과 하 재고 알려줘",
            label_visibility="collapsed",
            key="dashboard_question",
        )
        dash_btn_a, dash_btn_b, dash_btn_c = st.columns([1, 1, 1])
        if dash_btn_a.button("질문하기", type="primary", disabled=not dashboard_question.strip(), use_container_width=True):
            with st.spinner("답변을 생성하는 중입니다..."):
                try:
                    response = requests.post(
                        CHAT_API_URL,
                        json={
                            "question": dashboard_question,
                            "session_id": st.session_state.session_id,
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
                        {"user": dashboard_question, "assistant": data["answer"]}
                    )
                    st.session_state.chat_history = st.session_state.chat_history[-3:]
                    st.session_state.last_answer = data["answer"]
                    st.session_state.last_sources = data.get("sources", [])
        dash_btn_b.button(
            "중과 하 재고",
            use_container_width=True,
            on_click=set_session_value,
            args=("dashboard_question", "중과 하 재고 알려줘"),
        )
        dash_btn_c.button(
            "시세 전망",
            use_container_width=True,
            on_click=set_session_value,
            args=("dashboard_question", "1달 내에 가장 팔기 좋은 날이 언제야?"),
        )

        if st.session_state.last_answer:
            safe_answer = html.escape(st.session_state.last_answer).replace("\n", "<br>")
            st.markdown('<div class="section-label">최신 답변</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="answer-box">{safe_answer}</div>', unsafe_allow_html=True)

        st.markdown('<div class="section-label">재고현황 요약</div>', unsafe_allow_html=True)
        summary_cols = st.columns(2)
        for index, product in enumerate(products[:6]):
            with summary_cols[index % 2]:
                render_product_card(product)

    with dash_right:
        st.markdown('<div class="section-label">최근 주문 알림</div>', unsafe_allow_html=True)
        if orders:
            st.markdown('<div class="timeline-card">', unsafe_allow_html=True)
            for order in orders[:6]:
                st.markdown(
                    f"""
                    <div class="timeline-item">
                      <div class="timeline-time">{html.escape(order['created_at'])}</div>
                      주문 #{int(order['id']):04d} · {int(order['quantity_kg']):,}kg · {format_won(order['total_amount'])}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.markdown('<div class="info-card quiet">아직 주문 데이터가 없습니다.</div>', unsafe_allow_html=True)

        st.markdown('<div class="section-label">쇼핑몰 노출 재고</div>', unsafe_allow_html=True)
        for listing in active_listings[:4]:
            st.markdown(
                f"""
                <div class="answer-box">
                <strong>{html.escape(item_name(listing))}</strong><br>
                남은 판매수량 {int(listing['quantity_kg']):,}kg · {format_won(listing['price_per_kg'])}/kg
                </div>
                """,
                unsafe_allow_html=True,
            )

if selected_page == "챗봇":
    left, right = st.columns([1.45, 1])
    with left:
        st.markdown('<div class="section-label">질문</div>', unsafe_allow_html=True)
        example_questions = [
            "중과 하 재고 알려줘",
            "대과 상 50키로 쇼핑몰에 올려줘",
            "1달 내에 가장 팔기 좋은 날이 언제야?",
        ]
        example_cols = st.columns(3)
        for col, example in zip(example_cols, example_questions):
            if col.button(example, use_container_width=True):
                st.session_state.question = example

        question = st.text_area(
            "질문",
            placeholder="예: 중과 하 재고 알려줘",
            height=118,
            key="question",
            label_visibility="collapsed",
        )
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
                    st.session_state.last_answer = data["answer"]
                    st.session_state.last_sources = data.get("sources", [])

        if st.session_state.last_answer:
            safe_answer = html.escape(st.session_state.last_answer).replace("\n", "<br>")
            st.markdown('<div class="section-label">최신 답변</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="answer-box">{safe_answer}</div>', unsafe_allow_html=True)
            with st.expander("검색된 문서 chunk"):
                for source in st.session_state.last_sources:
                    st.markdown(
                        f"**{source['source_path']} / chunk {source['chunk_index']}** "
                        f"(distance: {source['distance']:.4f})"
                    )
                    st.write(source["content"])

    with right:
        st.markdown('<div class="section-label">최근 대화</div>', unsafe_allow_html=True)
        if st.session_state.chat_history:
            for turn in reversed(st.session_state.chat_history[-3:]):
                st.chat_message("user").write(turn["user"])
                st.chat_message("assistant").write(turn["assistant"])
        else:
            st.markdown('<div class="info-card quiet">아직 대화가 없습니다. 왼쪽에서 질문을 입력해보세요.</div>', unsafe_allow_html=True)

        if st.session_state.session_id:
            st.caption(f"대화 세션 #{st.session_state.session_id}")

        st.markdown('<div class="section-label">최근 주문 알림</div>', unsafe_allow_html=True)
        recent_orders = orders[:4]
        if recent_orders:
            st.markdown('<div class="timeline-card">', unsafe_allow_html=True)
            for order in recent_orders:
                st.markdown(
                    f"""
                    <div class="timeline-item">
                      <div class="timeline-time">{html.escape(order['created_at'])}</div>
                      주문 #{int(order['id']):04d} · {int(order['quantity_kg']):,}kg · {format_won(order['total_amount'])}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.markdown('<div class="info-card quiet">아직 주문 데이터가 없습니다.</div>', unsafe_allow_html=True)

if selected_page == "판매등록":
    st.markdown('<div class="section-label">판매등록 워크플로우</div>', unsafe_allow_html=True)
    if products:
        setup_col, draft_col = st.columns([1, 1])
        with setup_col:
            labels = [
                f"{item_name(item)} · 추가 가능 {int(item['available_kg']):,}kg · {format_won(item['recommended_price_per_kg'])}/kg"
                for item in products
            ]
            selected_label = st.selectbox("재고 선택", labels)
            product = products[labels.index(selected_label)]
            render_product_card(product)

            max_quantity = max(int(product["available_kg"]), 1)
            default_quantity = min(max_quantity, 100)
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
            description = st.text_area(
                "상품 설명",
                value=(
                    f"{item_name(product)} 상품입니다. "
                    f"{package_unit} 단위로 판매하며, 주문 확인 후 순차 출고합니다."
                ),
                height=96,
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
            if st.button("판매 초안 생성", type="primary", use_container_width=True):
                try:
                    draft = api_post("/sales/drafts", payload)
                except requests.RequestException as exc:
                    st.error(f"판매 초안 생성 실패: {exc}")
                else:
                    st.success(f"판매 초안 #{draft['id']}이 생성되었습니다.")
                    st.rerun()

        with draft_col:
            st.markdown('<div class="section-label">초안 승인·등록</div>', unsafe_allow_html=True)
            try:
                drafts = api_get("/sales/drafts")
            except requests.RequestException as exc:
                st.error(f"판매 초안을 불러오지 못했습니다: {exc}")
                drafts = []

            if not drafts:
                st.info("아직 판매 초안이 없습니다.")

            for draft in drafts[:8]:
                with st.expander(
                    f"#{draft['id']} {draft['product_name']} {draft['size_class']}과 {draft['grade']} "
                    f"{int(draft['quantity_kg']):,}kg · {draft['status']}"
                ):
                    edited_quantity = st.number_input(
                        "수량(kg)",
                        min_value=1,
                        value=int(draft["quantity_kg"]),
                        key=f"quantity_{draft['id']}",
                    )
                    edited_price = st.number_input(
                        "kg당 판매가",
                        min_value=1,
                        value=int(draft["price_per_kg"]),
                        key=f"price_{draft['id']}",
                    )
                    edited_description = st.text_area(
                        "설명",
                        value=draft["description"],
                        key=f"description_{draft['id']}",
                        height=76,
                    )
                    update_payload = {
                        "product_name": draft["product_name"],
                        "size_class": draft["size_class"],
                        "grade": draft["grade"],
                        "quantity_kg": int(edited_quantity),
                        "estimated_unit_weight_kg": float(draft["estimated_unit_weight_kg"]),
                        "price_per_kg": int(edited_price),
                        "package_unit": draft["package_unit"],
                        "sales_channel": draft["sales_channel"],
                        "description": edited_description,
                    }
                    btn_a, btn_b, btn_c = st.columns(3)
                    if btn_a.button("수정", key=f"save_{draft['id']}"):
                        try:
                            api_put(f"/sales/drafts/{draft['id']}", update_payload)
                        except requests.RequestException as exc:
                            st.error(f"수정 실패: {exc}")
                        else:
                            st.rerun()
                    if btn_b.button("승인", key=f"approve_{draft['id']}", disabled=draft["status"] != "draft"):
                        try:
                            api_post(f"/sales/drafts/{draft['id']}/approve")
                        except requests.RequestException as exc:
                            st.error(f"승인 실패: {exc}")
                        else:
                            st.rerun()
                    if btn_c.button("등록", key=f"register_{draft['id']}", disabled=draft["status"] not in {"draft", "approved"}):
                        try:
                            api_post(f"/sales/drafts/{draft['id']}/register")
                        except requests.RequestException as exc:
                            st.error(f"판매 등록 실패: {exc}")
                        else:
                            st.rerun()

if selected_page == "쇼핑몰 재고":
    st.markdown('<div class="section-label">쇼핑몰 노출 재고</div>', unsafe_allow_html=True)
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

if selected_page == "등록상품":
    st.markdown('<div class="section-label">등록상품 전체</div>', unsafe_allow_html=True)
    if not listings:
        st.info("아직 등록된 상품이 없습니다.")
    for listing in listings:
        total_amount = int(listing["quantity_kg"]) * int(listing["price_per_kg"])
        st.markdown(
            f"""
            <div class="answer-box">
            <strong>{html.escape(item_name(listing))}</strong><br>
            수량 {int(listing['quantity_kg']):,}kg · 최초 {int(listing.get('original_quantity_kg', listing['quantity_kg'])):,}kg ·
            kg당 {format_won(listing['price_per_kg'])}<br>
            추정 단위중량 {float(listing['estimated_unit_weight_kg']):.2f}kg/개 · 채널 {html.escape(listing['sales_channel'])} · 상태 {listing['status']}<br>
            예상 총액 {total_amount:,}원
            </div>
            """,
            unsafe_allow_html=True,
        )

if selected_page == "시세갱신":
    st.markdown('<div class="section-label">시세 데이터 갱신</div>', unsafe_allow_html=True)
    price_cols = st.columns(3)
    with price_cols[0]:
        render_metric("최신 관측일", latest_date, "가락시장 CSV 기준")
    with price_cols[1]:
        render_metric("예측 문서", doc_status, "Chronos mini RAG")
    with price_cols[2]:
        render_metric("갱신 방식", "수동 실행", "크롤링·예측·재임베딩")

    st.markdown(
        """
        <div class="info-card quiet">
        버튼을 누르면 가락시장 사과 시세를 수집하고 Chronos mini 예측 문서를 다시 생성한 뒤 MariaDB Vector에 재임베딩합니다.
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("최신 시세 가져와서 RAG 갱신", type="primary"):
        with st.spinner("시세 수집, 예측, RAG 재임베딩을 진행하는 중입니다..."):
            try:
                result = api_post("/prices/refresh", timeout=600)
            except requests.RequestException as exc:
                st.error(f"시세 갱신 실패: {exc}")
            else:
                st.success("시세 예측 RAG 문서를 갱신했습니다.")
                st.json(result)

if selected_page == "알림":
    st.markdown('<div class="section-label">농부 알림</div>', unsafe_allow_html=True)
    render_notifications_panel()
