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
PROMO_IMAGE_PATH = ASSET_DIR / "apple-market-banner.png"
PRODUCT_IMAGE_PATHS = {
    ("대", "상"): ASSET_DIR / "apple-large-premium.png",
    ("대", "중"): ASSET_DIR / "apple-large-standard.png",
    ("대", "하"): ASSET_DIR / "apple-large-value.png",
    ("중", "상"): ASSET_DIR / "apple-medium-premium.png",
    ("중", "중"): ASSET_DIR / "apple-medium-standard.png",
    ("중", "하"): ASSET_DIR / "apple-medium-value.png",
}

st.set_page_config(page_title="Apple Market", page_icon="apple", layout="wide")

st.markdown(
    """
    <style>
    .stApp { background: #fbfaf4; color: #17231d; }
    .block-container { max-width: 1180px; padding-top: 2rem; padding-bottom: 3rem; }
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
    .promo-banner, .product-card {
        background: #fffefa;
        border: 1px solid rgba(23,35,29,.13);
        border-radius: 8px;
        padding: 1rem;
        box-shadow: 0 8px 20px rgba(23,35,29,.045);
    }
    .promo-banner {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 1rem;
        margin: .2rem 0 1rem;
        padding: 1rem 1.2rem;
        background: linear-gradient(100deg, #fff8ed 0%, #eef7ea 100%);
    }
    .promo-title { color: #17231d; font-size: 1.34rem; font-weight: 950; margin-bottom: .2rem; }
    .promo-copy { color: #5e6961; line-height: 1.5; font-size: .95rem; }
    .promo-image {
        flex: 0 0 auto;
        width: 220px;
        height: 110px;
        object-fit: cover;
        border-radius: 8px;
        border: 1px solid rgba(23,35,29,.08);
        box-shadow: 0 8px 18px rgba(23,35,29,.08);
    }
    @media (max-width: 760px) {
        .promo-banner { align-items: flex-start; flex-direction: column; }
        .promo-image { width: 100%; height: 150px; }
    }
    .hero-image {
        width: 260px;
        max-height: 118px;
        object-fit: cover;
        border-radius: 8px;
    }
    .catalog-label {
        height: 2.55rem;
        display: flex;
        align-items: center;
        color: #17231d;
        font-size: 1.08rem;
        font-weight: 950;
    }
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
    .order-total {
        color: #c9281f;
        font-size: 1.12rem;
        font-weight: 950;
        margin: .35rem 0 .55rem;
    }
    .history-card {
        background: #fffefa;
        border: 1px solid rgba(23,35,29,.13);
        border-radius: 8px;
        padding: .95rem 1rem;
        margin-bottom: .65rem;
        box-shadow: 0 8px 20px rgba(23,35,29,.045);
    }
    .history-title { color:#17231d; font-weight:950; font-size:1.05rem; }
    .history-meta { color:#5c685f; line-height:1.55; margin-top:.2rem; font-size:.92rem; }
    div[data-testid="stButton"] button { border-radius: 8px; font-weight: 850; }
    div[data-testid="stButton"] button[kind="primary"] {
        background: #c9281f;
        border-color: #c9281f;
        color: #ffffff;
    }
    div[data-testid="stButton"] button[kind="primary"]:hover {
        background: #a91f18;
        border-color: #a91f18;
        color: #ffffff;
    }
    div[data-testid="stButton"] button[kind="secondary"]:hover {
        border-color: #c9281f;
        color: #c9281f;
    }
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


def require_login() -> dict:
    if "shop_user" in st.session_state:
        return st.session_state.shop_user

    st.markdown('<div class="title">Apple Market</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">주문하려면 먼저 로그인하세요.</div>', unsafe_allow_html=True)
    with st.form("shop_login_form"):
        username = st.text_input("아이디", value=os.getenv("APP_CUSTOMER_USERNAME", "customer"))
        password = st.text_input("비밀번호", type="password")
        submitted = st.form_submit_button("로그인", type="primary", use_container_width=True)

    if submitted:
        try:
            user = api_post("/auth/login", {"username": username, "password": password})
        except requests.RequestException:
            st.error("로그인 실패: 아이디와 비밀번호를 확인하세요.")
        else:
            st.session_state.shop_user = user
            st.rerun()

    st.stop()


def format_won(value: int) -> str:
    return f"{int(value):,}원"


def item_name(item: dict) -> str:
    return f"{item['product_name']} {item['size_class']}과 {item['grade']} 등급"


def image_data_uri(path: Path) -> str:
    if not path.exists():
        return ""
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


apple_image_uri = image_data_uri(APPLE_IMAGE_PATH)
promo_banner_uri = image_data_uri(PROMO_IMAGE_PATH)
product_image_uris = {
    key: image_data_uri(path)
    for key, path in PRODUCT_IMAGE_PATHS.items()
}

shop_user = require_login()

hero_image = f'<img class="hero-image" src="{apple_image_uri}" />' if apple_image_uri else ""
st.markdown(
    f"""
    <div class="market-header">
      <div>
        <div class="kicker">FRESH LOCAL APPLES</div>
        <div class="title">Apple Market</div>
        <div class="subtitle">신선한 사과를 합리적인 가격에 만나보세요.</div>
      </div>
      {hero_image}
    </div>
    """,
    unsafe_allow_html=True,
)
user_cols = st.columns([5, 1])
with user_cols[0]:
    st.caption(f"{shop_user['display_name']}님 로그인")
with user_cols[1]:
    if st.button("로그아웃", use_container_width=True):
        st.session_state.pop("shop_user", None)
        st.session_state.pop("shop_page", None)
        st.rerun()
if "shop_page" not in st.session_state:
    st.session_state.shop_page = "상품목록"

page_cols = st.columns([0.8, 0.8, 4.4], gap="small")
with page_cols[0]:
    if st.button(
        "상품목록",
        type="primary" if st.session_state.shop_page == "상품목록" else "secondary",
        use_container_width=True,
    ):
        st.session_state.shop_page = "상품목록"
        st.rerun()
with page_cols[1]:
    if st.button(
        "구매기록",
        type="primary" if st.session_state.shop_page == "구매기록" else "secondary",
        use_container_width=True,
    ):
        st.session_state.shop_page = "구매기록"
        st.rerun()

if st.session_state.shop_page == "구매기록":
    try:
        purchase_history = api_get(
            f"/sales/orders/users/{shop_user['id']}?customer_name={shop_user['display_name']}"
        )
    except requests.RequestException as exc:
        st.error(f"구매기록을 불러오지 못했습니다: {exc}")
        purchase_history = []

    st.markdown('<div class="catalog-label">구매기록</div>', unsafe_allow_html=True)
    if not purchase_history:
        st.info("아직 구매기록이 없습니다.")

    for order in purchase_history:
        st.markdown(
            f"""
            <div class="history-card">
              <div class="history-title">주문 #{int(order['id']):04d} · {html.escape(item_name(order))}</div>
              <div class="history-meta">
                주문일 {html.escape(order['created_at'])}<br>
                수량 {int(order['quantity_kg']):,}kg · kg당 {format_won(order['price_per_kg'])} ·
                결제금액 <strong>{format_won(order['total_amount'])}</strong><br>
                상태 {html.escape(order['status'])} · 판매 단위 {html.escape(order['package_unit'])}
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    st.stop()
try:
    all_listings = [listing for listing in api_get("/sales/listings") if listing["status"] == "active"]
except requests.RequestException as exc:
    st.error(f"상품을 불러오지 못했습니다: {exc}")
    all_listings = []

if "shop_size_filter" not in st.session_state:
    st.session_state.shop_size_filter = "전체"

promo_image = f'<img class="promo-image" src="{promo_banner_uri}" />' if promo_banner_uri else ""
st.markdown(
    f"""
    <div class="promo-banner">
      <div>
        <div class="promo-title">오늘 수확한 신선한 사과를 바로 만나보세요</div>
        <div class="promo-copy">대과는 선물용으로, 중과는 매일 먹기 좋은 실속형으로 준비했습니다.</div>
      </div>
      {promo_image}
    </div>
    """,
    unsafe_allow_html=True,
)

filter_cols = st.columns([0.66, 0.62, 0.62, 0.62, 3.3, 1], gap="small")
with filter_cols[0]:
    st.markdown('<div class="catalog-label">상품목록</div>', unsafe_allow_html=True)
for col, filter_name in zip(filter_cols[1:4], ["전체", "대과", "중과"]):
    with col:
        if st.button(
            filter_name,
            key=f"shop_size_{filter_name}",
            type="primary" if st.session_state.shop_size_filter == filter_name else "secondary",
            use_container_width=True,
        ):
            st.session_state.shop_size_filter = filter_name
            st.rerun()
with filter_cols[5]:
    if st.button("상품 새로고침", use_container_width=True):
        st.rerun()

size_filter = st.session_state.shop_size_filter
selected_size = {"대과": "대", "중과": "중"}.get(size_filter)
listings = [
    listing
    for listing in all_listings
    if selected_size is None or listing["size_class"] == selected_size
]

if not listings:
    st.info("아직 쇼핑몰에 등록된 상품이 없습니다.")

for row_start in range(0, len(listings), 3):
    cols = st.columns(3)
    for col, listing in zip(cols, listings[row_start : row_start + 3]):
        with col:
            unit = 5 if "5kg" in listing["package_unit"] else 10
            max_order = min(int(listing["quantity_kg"]), unit * 20)
            product_image_uri = product_image_uris.get(
                (listing["size_class"], listing["grade"]),
                apple_image_uri,
            )
            st.markdown(
                f"""
                <div class="product-card">
                  {f'<img class="product-image" src="{product_image_uri}" />' if product_image_uri else ''}
                  <div class="product-body">
                    <div class="product-title">{html.escape(item_name(listing))}</div>
                    <div>
                      <span class="pill">{html.escape(listing['package_unit'])}</span>
                      <span class="pill">{float(listing['estimated_unit_weight_kg']):.2f}kg/개 추정</span>
                      <span class="pill">남은 {int(listing['quantity_kg']):,}kg</span>
                    </div>
                    <div class="price">{format_won(listing['price_per_kg'])}/kg</div>
                    <div class="meta">
                      {html.escape(listing['description'])}
                    </div>
                    <div class="order-box"></div>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            quantity = st.number_input(
                "주문 수량(kg)",
                min_value=unit,
                max_value=max_order,
                value=unit,
                step=unit,
                key=f"shop_quantity_{listing['id']}",
            )
            st.markdown(
                f'<div class="order-total">주문 금액: {format_won(int(quantity) * int(listing["price_per_kg"]))}</div>',
                unsafe_allow_html=True,
            )
            if st.button("주문하기", key=f"shop_order_{listing['id']}", use_container_width=True):
                try:
                    api_post(
                        f"/sales/listings/{listing['id']}/orders",
                        {
                            "customer_user_id": int(shop_user["id"]),
                            "customer_name": shop_user["display_name"],
                            "quantity_kg": int(quantity),
                        },
                    )
                except requests.RequestException as exc:
                    st.error(f"주문 처리 실패: {exc}")
                else:
                    st.success("주문이 접수되었습니다. 농부 알림으로 전달했습니다.")
                    st.rerun()
