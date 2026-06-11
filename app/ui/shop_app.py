import base64
import html
import os
from pathlib import Path

import requests
import streamlit as st

from app.config import load_app_env

load_app_env()

CHAT_API_URL = os.getenv("CHAT_API_URL", "http://localhost:8000/chat")
API_BASE_URL = CHAT_API_URL.rsplit("/", 1)[0]
ASSET_DIR = Path(__file__).resolve().parent / "assets"
ORCHARD_BACKGROUND_IMAGE_PATH = ASSET_DIR / "apple-orchard-bg.png"
APPLE_IMAGE_PATH = ASSET_DIR / "apple-hero.png"
PROMO_IMAGE_PATH = ASSET_DIR / "apple-market-banner.png"
FREE_PROMO_IMAGE_PATHS = (
    ASSET_DIR / "ai-campus-onsite-ad.png",
    ASSET_DIR / "ai-campus-semiconductor-ad.png",
)
PRODUCT_IMAGE_PATHS = {
    ("대", "상"): ASSET_DIR / "apple-large-premium.png",
    ("대", "중"): ASSET_DIR / "apple-large-standard.png",
    ("대", "하"): ASSET_DIR / "apple-large-value.png",
    ("중", "상"): ASSET_DIR / "apple-medium-premium.png",
    ("중", "중"): ASSET_DIR / "apple-medium-standard.png",
    ("중", "하"): ASSET_DIR / "apple-medium-value.png",
}
SHOP_EDITION = os.getenv("SHOP_EDITION", "free").strip().lower()
IS_PRO_SHOP = SHOP_EDITION == "pro"
DEFAULT_SHOP_PAGE_TITLE = os.getenv("SHOP_PAGE_TITLE", "Apple Market Pro" if IS_PRO_SHOP else "Apple Market")
SHOP_PAGE_TITLE = DEFAULT_SHOP_PAGE_TITLE
SHOP_LOGIN_DEFAULT_USERNAME = os.getenv(
    "SHOP_LOGIN_DEFAULT_USERNAME",
    os.getenv("APP_CUSTOMER_PRO_USERNAME", "customerpro") if IS_PRO_SHOP else os.getenv("APP_CUSTOMER_USERNAME", "customer"),
)
SHOP_REQUIRED_ROLE = os.getenv("SHOP_REQUIRED_ROLE", "customer_pro" if IS_PRO_SHOP else "")
ORCHARD_BACKGROUND_URI = ""
if ORCHARD_BACKGROUND_IMAGE_PATH.exists():
    ORCHARD_BACKGROUND_URI = (
        "data:image/png;base64,"
        + base64.b64encode(ORCHARD_BACKGROUND_IMAGE_PATH.read_bytes()).decode("ascii")
    )

st.set_page_config(page_title=SHOP_PAGE_TITLE, page_icon="apple", layout="wide")

st.markdown(
    """
    <style>
    .stApp { background: #fbfaf4; color: #17231d; }
    .block-container { max-width: 1180px; padding-top: 2rem; padding-bottom: 3rem; }
    .market-header {
        padding: 1rem 1.15rem;
        border: 1px solid rgba(23,35,29,.10);
        border-radius: 8px;
        margin-bottom: 1rem;
        background: linear-gradient(90deg, rgba(12,18,14,.80) 0%, rgba(12,18,14,.54) 44%, rgba(255,255,255,.08) 100%), #fffefa;
        background-size: cover;
        background-position: center;
        min-height: 142px;
        display:flex;
        justify-content:space-between;
        align-items:center;
        gap:1rem;
        box-shadow: 0 12px 28px rgba(23,35,29,.13);
    }
    .kicker { display: none !important; color: #657261; font-size: .82rem; font-weight: 850; }
    .title { color: #17231d; font-size: 2.35rem; line-height: 1.1; font-weight: 900; margin: .15rem 0 .35rem; }
    .market-header .title {
        display: inline-block;
        color: #ffffff;
        background: rgba(12,18,14,.66);
        border: 1px solid rgba(255,255,255,.22);
        border-radius: 8px;
        padding: .42rem .72rem;
        text-shadow: 0 2px 10px rgba(0,0,0,.35);
    }
    .product-card {
        background: #fffefa;
        border: 1px solid rgba(23,35,29,.13);
        border-radius: 8px;
        padding: 1rem;
        box-shadow: 0 8px 20px rgba(23,35,29,.045);
    }
    .side-ad {
        background: #fffefa;
        border: 1px solid rgba(23,35,29,.13);
        border-radius: 8px;
        padding: .85rem;
        box-shadow: 0 8px 20px rgba(23,35,29,.045);
        margin-top: .7rem;
    }
    .side-ad-label {
        color: #c9281f;
        font-size: .78rem;
        font-weight: 950;
        margin-bottom: .25rem;
    }
    .side-ad-title {
        color: #17231d;
        font-size: 1.05rem;
        line-height: 1.3;
        font-weight: 950;
        margin-bottom: .35rem;
    }
    .side-ad-copy {
        color: #5e6961;
        font-size: .88rem;
        line-height: 1.45;
        margin-bottom: .65rem;
    }
    .side-ad-image {
        width: 100%;
        height: 132px;
        object-fit: cover;
        border-radius: 8px;
        border: 1px solid rgba(23,35,29,.08);
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
    .hero-image {
        display: none;
    }
    .catalog-label {
        height: 2.55rem;
        display: flex;
        align-items: center;
        color: #17231d;
        font-size: 1.08rem;
        font-weight: 950;
        white-space: nowrap;
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
    div[data-testid="stButton"] button,
    div[data-testid="stButton"] button p {
        white-space: nowrap;
    }
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
    div[data-testid="stCaptionContainer"] {
        display: none !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

if ORCHARD_BACKGROUND_URI:
    st.markdown(
        f"""
        <style>
        .stApp {{
            background:
                linear-gradient(rgba(251, 250, 244, .70), rgba(251, 250, 244, .82)),
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
        .market-header,
        .product-card,
        .history-card {{
            background-color: rgba(255, 254, 250, .96);
            backdrop-filter: blur(2px);
        }}
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


def get_shop_page_title() -> str:
    try:
        settings = api_get("/sales/settings/shop")
    except requests.RequestException:
        return DEFAULT_SHOP_PAGE_TITLE
    return settings.get("shop_page_title") or DEFAULT_SHOP_PAGE_TITLE


def require_login() -> dict:
    if "shop_user" in st.session_state:
        return st.session_state.shop_user

    st.markdown(f'<div class="title">{html.escape(SHOP_PAGE_TITLE)}</div>', unsafe_allow_html=True)
    with st.form("shop_login_form"):
        username = st.text_input("아이디", value=SHOP_LOGIN_DEFAULT_USERNAME)
        password = st.text_input("비밀번호", type="password")
        submitted = st.form_submit_button("로그인", type="primary", use_container_width=True)

    if submitted:
        try:
            user = api_post("/auth/login", {"username": username, "password": password})
        except requests.RequestException:
            st.error("로그인 실패: 아이디와 비밀번호를 확인하세요.")
        else:
            if SHOP_REQUIRED_ROLE and user["role"] != SHOP_REQUIRED_ROLE:
                st.error("이 판매페이지에 접근할 수 있는 고객 계정이 아닙니다.")
            else:
                st.session_state.shop_user = user
                st.rerun()

    st.stop()


def format_won(value: int) -> str:
    return f"{int(value):,}원"


def item_name(item: dict) -> str:
    return f"{item['product_name']} {item['size_class']}과 {item['grade']} 등급"


@st.cache_data
def image_data_uri(path: Path) -> str:
    if not path.exists():
        return ""
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


@st.cache_data(ttl=30)
def fetch_active_listings() -> list:
    return [listing for listing in api_get("/sales/listings") if listing["status"] == "active"]


@st.cache_data(ttl=30)
def fetch_purchase_history(user_id: int, display_name: str) -> list:
    return api_get(f"/sales/orders/users/{user_id}?customer_name={display_name}")


def render_free_sidebar_ad() -> None:
    if IS_PRO_SHOP:
        return

    promo_image = f'<img class="side-ad-image" src="{promo_banner_uri}" />' if promo_banner_uri else ""
    st.sidebar.markdown(
        f"""
        <div class="side-ad">
          <div class="side-ad-label">오늘의 추천</div>
          <div class="side-ad-title">농장에서 바로 선별한 신선한 사과</div>
          <div class="side-ad-copy">대과는 선물용으로, 중과는 매일 먹기 좋은 실속형으로 준비했습니다.</div>
          {promo_image}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_free_right_ad() -> None:
    if IS_PRO_SHOP:
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


apple_image_uri = image_data_uri(APPLE_IMAGE_PATH)
promo_banner_uri = image_data_uri(PROMO_IMAGE_PATH)
product_image_uris = {
    key: image_data_uri(path)
    for key, path in PRODUCT_IMAGE_PATHS.items()
}

SHOP_PAGE_TITLE = get_shop_page_title()
shop_user = require_login()
render_free_right_ad()

hero_background_style = (
    f' style="background-image: linear-gradient(90deg, rgba(12,18,14,.80) 0%, rgba(12,18,14,.54) 44%, rgba(255,255,255,.08) 100%), url({apple_image_uri});"'
    if apple_image_uri
    else ""
)
st.markdown(
    """
    <div class="market-header"{hero_background_style}>
      <div>
        <div class="kicker">FRESH LOCAL APPLES</div>
        <div class="title">{title}</div>
      </div>
    </div>
    """.format(
        hero_background_style=hero_background_style,
        title=html.escape(SHOP_PAGE_TITLE),
    ),
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

page_cols = st.columns([1.05, 1.05, 3.9], gap="small")
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
        purchase_history = fetch_purchase_history(shop_user["id"], shop_user["display_name"])
    except requests.RequestException as exc:
        st.error(f"구매기록을 불러오지 못했습니다: {exc}")
        purchase_history = []

    st.markdown('<div class="catalog-label">📋 구매기록</div>', unsafe_allow_html=True)
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
    all_listings = fetch_active_listings()
except requests.RequestException as exc:
    st.error(f"상품을 불러오지 못했습니다: {exc}")
    all_listings = []

if "shop_size_filter" not in st.session_state:
    st.session_state.shop_size_filter = "전체"

filter_cols = st.columns([1.05, 0.72, 0.72, 0.78, 2.95, 1.2], gap="small")
with filter_cols[0]:
    st.markdown('<div class="catalog-label">🛒 상품목록</div>', unsafe_allow_html=True)
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
        fetch_active_listings.clear()
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
                    fetch_active_listings.clear()
                    fetch_purchase_history.clear()
                    st.success("주문이 접수되었습니다. 농부 알림으로 전달했습니다.")
                    st.rerun()
