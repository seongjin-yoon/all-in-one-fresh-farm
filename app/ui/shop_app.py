import base64
import html
import os
from pathlib import Path

import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

CHAT_API_URL = os.getenv("CHAT_API_URL", "http://localhost:8000/chat")
API_BASE_URL = CHAT_API_URL.rsplit("/", 1)[0]
ASSET_DIR = Path(__file__).resolve().parent / "assets"
APPLE_IMAGE_PATH = ASSET_DIR / "apple-hero.png"

st.set_page_config(page_title="Fruits Ninja Market", page_icon="apple", layout="wide")

st.markdown(
    """
    <style>
    .stApp { background: #fbfaf4; color: #17231d; }
    .block-container { max-width: 1180px; padding-top: 1.1rem; padding-bottom: 3rem; }
    .market-nav {
        background: rgba(255,255,255,.94);
        border: 1px solid rgba(23,35,29,.12);
        border-radius: 8px;
        padding: .72rem .95rem;
        display:flex;
        justify-content:space-between;
        align-items:center;
        margin-bottom: .9rem;
    }
    .nav-brand { font-size:1.25rem; font-weight:950; color:#17231d; }
    .nav-links { color:#33443a; font-size:.86rem; font-weight:850; }
    .market-header {
        padding: 1.2rem 1.25rem;
        border: 1px solid rgba(23,35,29,.10);
        border-radius: 8px;
        margin-bottom: 1rem;
        background: linear-gradient(90deg, #eff7eb 0%, #fff8ed 100%);
        min-height: 138px;
        display:flex;
        justify-content:space-between;
        align-items:center;
        gap:1rem;
    }
    .kicker { color: #657261; font-size: .82rem; font-weight: 850; }
    .title { color: #17231d; font-size: 2.35rem; line-height: 1.1; font-weight: 900; margin: .15rem 0 .35rem; }
    .subtitle { color: #5e6961; line-height: 1.55; max-width: 720px; }
    .summary-card, .product-card {
        background: #fffefa;
        border: 1px solid rgba(23,35,29,.13);
        border-radius: 8px;
        padding: 1rem;
        box-shadow: 0 8px 20px rgba(23,35,29,.045);
    }
    .summary-label { color: #6e796f; font-size: .78rem; font-weight: 850; }
    .summary-value { color: #17231d; font-size: 1.45rem; font-weight: 900; }
    .hero-image {
        width: 260px;
        max-height: 118px;
        object-fit: cover;
        border-radius: 8px;
    }
    .filter-row {
        display:flex; justify-content:space-between; align-items:center; gap:.65rem;
        margin: .75rem 0 1rem;
    }
    .filter-chip {
        display:inline-block; background:#fffefa; border:1px solid rgba(23,35,29,.12);
        color:#29382f; border-radius:8px; padding:.48rem .85rem; font-weight:850; margin-right:.35rem;
    }
    .filter-chip.active { background:#16713a; color:#fff; }
    .product-card { min-height: 366px; margin-bottom: .8rem; overflow:hidden; padding:0; }
    .product-image {
        width:100%;
        height:150px;
        object-fit:cover;
        display:block;
        border-bottom:1px solid rgba(23,35,29,.10);
    }
    .product-body { padding: .9rem 1rem 1rem; }
    .product-title { font-size: 1.18rem; font-weight: 900; color: #17231d; margin-bottom: .28rem; }
    .price { color: #a33528; font-size: 1.45rem; font-weight: 900; margin: .55rem 0 .25rem; }
    .meta { color: #5c685f; line-height: 1.55; font-size: .92rem; }
    .pill {
        display: inline-block;
        background: #eef3e7;
        border: 1px solid rgba(63,89,67,.18);
        color: #35473b;
        border-radius: 999px;
        padding: .12rem .52rem;
        margin: .12rem .16rem .12rem 0;
        font-size: .78rem;
        font-weight: 750;
    }
    .order-box {
        border-top: 1px solid rgba(23,35,29,.10);
        margin-top: .8rem;
        padding-top: .7rem;
    }
    div[data-testid="stButton"] button { border-radius: 8px; font-weight: 850; }
    div[data-testid="stNumberInput"] input,
    div[data-testid="stTextInput"] input {
        border-radius: 8px;
        background: #fffefa;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def api_get(path: str):
    response = requests.get(f"{API_BASE_URL}{path}", timeout=20)
    response.raise_for_status()
    return response.json()


def api_post(path: str, payload: dict):
    response = requests.post(f"{API_BASE_URL}{path}", json=payload, timeout=30)
    response.raise_for_status()
    return response.json()


def format_won(value: int) -> str:
    return f"{int(value):,}원"


def item_name(item: dict) -> str:
    return f"{item['product_name']} {item['size_class']}과 {item['grade']} 등급"


def image_data_uri(path: Path) -> str:
    if not path.exists():
        return ""
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def render_summary(label: str, value: str) -> None:
    st.markdown(
        f"""
        <div class="summary-card">
          <div class="summary-label">{html.escape(label)}</div>
          <div class="summary-value">{html.escape(value)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


apple_image_uri = image_data_uri(APPLE_IMAGE_PATH)

st.markdown(
    """
    <div class="market-nav">
      <div class="nav-brand">프루츠닌자 마켓</div>
      <div class="nav-links">상품&nbsp;&nbsp;&nbsp;주문내역&nbsp;&nbsp;&nbsp;공지사항&nbsp;&nbsp;&nbsp;고객센터&nbsp;&nbsp;&nbsp;장바구니</div>
    </div>
    """,
    unsafe_allow_html=True,
)

hero_image = f'<img class="hero-image" src="{apple_image_uri}" />' if apple_image_uri else ""
st.markdown(
    f"""
    <div class="market-header">
      <div>
        <div class="kicker">FRESH LOCAL APPLES</div>
        <div class="title">상철 사과 마켓</div>
        <div class="subtitle">신선한 사과를 합리적인 가격에 만나보세요.</div>
      </div>
      {hero_image}
    </div>
    """,
    unsafe_allow_html=True,
)
try:
    all_listings = [listing for listing in api_get("/sales/listings") if listing["status"] == "active"]
except requests.RequestException as exc:
    st.error(f"상품을 불러오지 못했습니다: {exc}")
    all_listings = []

if "shop_size_filter" not in st.session_state:
    st.session_state.shop_size_filter = "전체"

filter_cols = st.columns([0.75, 0.75, 0.75, 2.7, 1])
for col, filter_name in zip(filter_cols[:3], ["전체", "대과", "중과"]):
    with col:
        if st.button(
            filter_name,
            key=f"shop_size_{filter_name}",
            type="primary" if st.session_state.shop_size_filter == filter_name else "secondary",
            use_container_width=True,
        ):
            st.session_state.shop_size_filter = filter_name
            st.rerun()
with filter_cols[4]:
    if st.button("상품 새로고침", type="primary", use_container_width=True):
        st.rerun()

size_filter = st.session_state.shop_size_filter
selected_size = {"대과": "대", "중과": "중"}.get(size_filter)
listings = [
    listing
    for listing in all_listings
    if selected_size is None or listing["size_class"] == selected_size
]
total_quantity = sum(int(listing["quantity_kg"]) for listing in listings)
total_value = sum(int(listing["quantity_kg"]) * int(listing["price_per_kg"]) for listing in listings)

summary_cols = st.columns(3)
with summary_cols[0]:
    render_summary("판매 중인 상품", f"{len(listings)}개")
with summary_cols[1]:
    render_summary("남은 판매수량", f"{total_quantity:,}kg")
with summary_cols[2]:
    render_summary("등록 금액", f"{total_value:,}원")

st.markdown(
    f"""
    <div class="filter-row">
      <div>
        <span class="filter-chip active">{html.escape(size_filter)}</span>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

if not listings:
    st.info("아직 쇼핑몰에 등록된 상품이 없습니다.")

for row_start in range(0, len(listings), 3):
    cols = st.columns(3)
    for col, listing in zip(cols, listings[row_start : row_start + 3]):
        with col:
            total_amount = int(listing["quantity_kg"]) * int(listing["price_per_kg"])
            unit = 5 if "5kg" in listing["package_unit"] else 10
            max_order = min(int(listing["quantity_kg"]), unit * 20)
            st.markdown(
                f"""
                <div class="product-card">
                  {f'<img class="product-image" src="{apple_image_uri}" />' if apple_image_uri else ''}
                  <div class="product-body">
                    <span class="pill">{listing['size_class']}과 · {listing['grade']} 등급</span>
                    <div class="product-title">{html.escape(item_name(listing))}</div>
                    <div>
                      <span class="pill">{html.escape(listing['package_unit'])}</span>
                      <span class="pill">{float(listing['estimated_unit_weight_kg']):.2f}kg/개 추정</span>
                      <span class="pill">남은 {int(listing['quantity_kg']):,}kg</span>
                    </div>
                    <div class="price">{format_won(listing['price_per_kg'])}/kg</div>
                    <div class="meta">
                      {html.escape(listing['description'])}<br>
                      현재 등록 금액 {total_amount:,}원
                    </div>
                    <div class="order-box"></div>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            customer_name = st.text_input(
                "주문자",
                value="테스트 고객",
                key=f"shop_customer_{listing['id']}",
            )
            quantity = st.number_input(
                "주문 수량(kg)",
                min_value=unit,
                max_value=max_order,
                value=unit,
                step=unit,
                key=f"shop_quantity_{listing['id']}",
            )
            st.caption(f"주문 금액: {format_won(int(quantity) * int(listing['price_per_kg']))}")
            if st.button("주문 테스트", key=f"shop_order_{listing['id']}", use_container_width=True):
                try:
                    api_post(
                        f"/sales/listings/{listing['id']}/orders",
                        {"customer_name": customer_name, "quantity_kg": int(quantity)},
                    )
                except requests.RequestException as exc:
                    st.error(f"주문 처리 실패: {exc}")
                else:
                    st.success("주문이 접수되었습니다. 농부 알림으로 전달했습니다.")
                    st.rerun()
