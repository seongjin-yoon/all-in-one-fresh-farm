import re
from pathlib import Path

from app.db.connection import db_cursor

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FORECAST_DOC_PATH = PROJECT_ROOT / "rag_docs" / "apple_price_forecast_chronos_mini.md"

SIZE_WEIGHT_KG = {
    "대": 0.32,
    "중": 0.24,
}
SIZE_MARKET_GRADE = {
    "대": "상",
    "중": "중",
}
QUALITY_PRICE_MULTIPLIER = {
    "상": 1.12,
    "중": 1.00,
    "하": 0.82,
}


SAMPLE_PRODUCTS = [
    {
        "product_name": "사과",
        "size_class": "대",
        "grade": "상",
        "available_kg": 620,
        "reserved_kg": 120,
        "recommended_price_per_kg": 9200,
        "package_unit": "5kg 박스",
        "sales_channel": "내부 온라인몰",
    },
    {
        "product_name": "사과",
        "size_class": "대",
        "grade": "중",
        "available_kg": 520,
        "reserved_kg": 90,
        "recommended_price_per_kg": 7900,
        "package_unit": "5kg 박스",
        "sales_channel": "내부 온라인몰",
    },
    {
        "product_name": "사과",
        "size_class": "대",
        "grade": "하",
        "available_kg": 260,
        "reserved_kg": 40,
        "recommended_price_per_kg": 6200,
        "package_unit": "10kg 박스",
        "sales_channel": "가공/특가몰",
    },
    {
        "product_name": "사과",
        "size_class": "중",
        "grade": "상",
        "available_kg": 700,
        "reserved_kg": 110,
        "recommended_price_per_kg": 8200,
        "package_unit": "5kg 박스",
        "sales_channel": "내부 온라인몰",
    },
    {
        "product_name": "사과",
        "size_class": "중",
        "grade": "중",
        "available_kg": 620,
        "reserved_kg": 80,
        "recommended_price_per_kg": 6900,
        "package_unit": "5kg 박스",
        "sales_channel": "내부 온라인몰",
    },
    {
        "product_name": "사과",
        "size_class": "중",
        "grade": "하",
        "available_kg": 320,
        "reserved_kg": 30,
        "recommended_price_per_kg": 5200,
        "package_unit": "10kg 박스",
        "sales_channel": "가공/특가몰",
    },
]


def decimal_to_float(value) -> float:
    return round(float(value or 0), 3)


def get_sample_product(product_name: str, size_class: str, grade: str) -> dict:
    return next(
        item
        for item in SAMPLE_PRODUCTS
        if (
            item["product_name"] == product_name
            and item["size_class"] == size_class
            and item["grade"] == grade
        )
    )


def ensure_inventory_tables() -> None:
    with db_cursor() as cursor:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS apple_inventory (
                id BIGINT PRIMARY KEY AUTO_INCREMENT,
                product_name VARCHAR(128) NOT NULL DEFAULT '사과',
                size_class VARCHAR(32) NOT NULL,
                grade VARCHAR(32) NOT NULL,
                available_kg DECIMAL(12, 3) NOT NULL DEFAULT 0,
                reserved_kg DECIMAL(12, 3) NOT NULL DEFAULT 0,
                package_unit VARCHAR(64) NOT NULL,
                sales_channel VARCHAR(64) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                UNIQUE KEY uq_apple_inventory_product_grade (product_name, size_class, grade)
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS harvest_events (
                id BIGINT PRIMARY KEY AUTO_INCREMENT,
                product_name VARCHAR(128) NOT NULL DEFAULT '사과',
                size_class VARCHAR(32) NOT NULL,
                quality_grade VARCHAR(32) NOT NULL,
                estimated_weight_kg DECIMAL(8, 3) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_harvest_events_created_at (created_at),
                INDEX idx_harvest_events_product_grade (product_name, size_class, quality_grade)
            )
            """
        )

        for product in SAMPLE_PRODUCTS:
            cursor.execute(
                """
                INSERT IGNORE INTO apple_inventory (
                    product_name, size_class, grade, available_kg, reserved_kg,
                    package_unit, sales_channel
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    product["product_name"],
                    product["size_class"],
                    product["grade"],
                    product["available_kg"],
                    product["reserved_kg"],
                    product["package_unit"],
                    product["sales_channel"],
                ),
            )


def list_inventory_products() -> list[dict]:
    ensure_inventory_tables()
    with db_cursor() as cursor:
        cursor.execute(
            """
            SELECT product_name, size_class, grade, available_kg, reserved_kg,
                   package_unit, sales_channel
            FROM apple_inventory
            ORDER BY
                FIELD(size_class, '대', '중'),
                FIELD(grade, '상', '중', '하')
            """
        )
        rows = cursor.fetchall()

    products = []
    for row in rows:
        sample_product = get_sample_product(
            row["product_name"],
            row["size_class"],
            row["grade"],
        )
        products.append(
            {
                **sample_product,
                **row,
                "available_kg": decimal_to_float(row["available_kg"]),
                "reserved_kg": decimal_to_float(row["reserved_kg"]),
            }
        )
    return products


def normalize_quality_grade(grade: str | None) -> str:
    if grade in {"상", "중", "하"}:
        return grade
    if grade == "특":
        return "상"
    if grade == "보통":
        return "중"
    return "상"


def normalize_size_class(size_class: str | None) -> str:
    return size_class if size_class in SIZE_WEIGHT_KG else "대"


def get_product_template(product_name: str, size_class: str, grade: str) -> dict:
    size_class = normalize_size_class(size_class)
    grade = normalize_quality_grade(grade)
    sample_product = get_sample_product(product_name, size_class, grade)
    ensure_inventory_tables()
    with db_cursor() as cursor:
        cursor.execute(
            """
            SELECT product_name, size_class, grade, available_kg, reserved_kg,
                   package_unit, sales_channel
            FROM apple_inventory
            WHERE product_name = ? AND size_class = ? AND grade = ?
            """,
            (product_name, size_class, grade),
        )
        product = cursor.fetchone()
    if not product:
        product = sample_product
    else:
        product = {
            **sample_product,
            **product,
            "available_kg": decimal_to_float(product["available_kg"]),
            "reserved_kg": decimal_to_float(product["reserved_kg"]),
        }
    return {
        **product,
        "recommended_price_per_kg": get_recommended_price_per_kg(
            size_class,
            grade,
            fallback_price=int(product["recommended_price_per_kg"]),
        ),
    }


def round_price(value: float) -> int:
    return int(round(value / 100) * 100)


def parse_price_int(value: str) -> int | None:
    digits = re.sub(r"[^0-9]", "", value)
    return int(digits) if digits else None


def load_forecast_recommended_prices() -> dict[tuple[str, str], int]:
    if not FORECAST_DOC_PATH.exists():
        return {}

    try:
        lines = FORECAST_DOC_PATH.read_text(encoding="utf-8").splitlines()
    except OSError:
        return {}

    prices: dict[tuple[str, str], int] = {}
    in_price_table = False
    for line in lines:
        if line.startswith("## 판매 기준가 산정표"):
            in_price_table = True
            continue
        if in_price_table and line.startswith("## "):
            break
        if not in_price_table or not line.startswith("|"):
            continue
        if line.startswith("|---") or "추천 판매가" in line:
            continue

        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) < 6:
            continue
        size_class = cells[0].replace("과", "").strip()
        grade = cells[1].strip()
        price = parse_price_int(cells[5])
        if size_class in SIZE_WEIGHT_KG and grade in QUALITY_PRICE_MULTIPLIER and price:
            prices[(size_class, grade)] = price
    return prices


def get_latest_market_prices() -> dict[str, int]:
    if not FORECAST_DOC_PATH.exists():
        return {}

    try:
        content = FORECAST_DOC_PATH.read_text(encoding="utf-8")
    except OSError:
        return {}

    prices: dict[str, int] = {}
    for market_grade in SIZE_MARKET_GRADE.values():
        pattern = rf"## 가락시장 {market_grade} 등급 예측.*?- 30영업일 중앙값 평균: ([\d,]+)원/kg"
        match = re.search(pattern, content, flags=re.S)
        if match:
            prices[market_grade] = int(match.group(1).replace(",", ""))
    return prices


def get_recommended_price_per_kg(
    size_class: str,
    grade: str,
    fallback_price: int,
) -> int:
    size_class = normalize_size_class(size_class)
    grade = normalize_quality_grade(grade)

    forecast_prices = load_forecast_recommended_prices()
    forecast_price = forecast_prices.get((size_class, grade))
    if forecast_price:
        return forecast_price

    market_grade = SIZE_MARKET_GRADE[size_class]
    market_prices = get_latest_market_prices()
    base_price = market_prices.get(market_grade)
    if base_price:
        return round_price(base_price * QUALITY_PRICE_MULTIPLIER[grade])

    return fallback_price


def get_listing_commitments() -> dict[tuple[str, str, str], dict[str, int]]:
    with db_cursor() as cursor:
        cursor.execute(
            """
            SELECT
                product_name,
                size_class,
                grade,
                COALESCE(SUM(original_quantity_kg), 0) AS listed_kg,
                COALESCE(SUM(original_quantity_kg - quantity_kg), 0) AS sold_kg,
                COALESCE(SUM(quantity_kg), 0) AS remaining_listing_kg
            FROM sales_listings
            WHERE status IN ('active', 'sold_out')
            GROUP BY product_name, size_class, grade
            """
        )
        rows = cursor.fetchall()

    return {
        (row["product_name"], row["size_class"], row["grade"]): {
            "listed_kg": int(row["listed_kg"]),
            "sold_kg": int(row["sold_kg"]),
            "remaining_listing_kg": int(row["remaining_listing_kg"]),
        }
        for row in rows
    }


def get_available_kg(product_name: str, size_class: str, grade: str) -> float:
    size_class = normalize_size_class(size_class)
    grade = normalize_quality_grade(grade)
    product = get_product_template(product_name, size_class, grade)
    commitments = get_listing_commitments().get((product_name, size_class, grade), {})
    return round(
        max(decimal_to_float(product["available_kg"]) - int(commitments.get("listed_kg", 0)), 0),
        3,
    )


def validate_new_listing_quantity(
    product_name: str,
    size_class: str,
    grade: str,
    quantity_kg: int,
) -> None:
    size_class = normalize_size_class(size_class)
    grade = normalize_quality_grade(grade)
    available_kg = get_available_kg(product_name, size_class, grade)
    if quantity_kg > available_kg:
        raise ValueError(
            f"{product_name} {size_class}과 {grade} 등급 신규 등록 가능 재고는 {available_kg}kg입니다."
        )


def extract_quantity_kg(text: str) -> int | None:
    quantity_match = re.search(r"(\d[\d,]*)\s*(?:kg|키로|킬로)", text, re.IGNORECASE)
    if not quantity_match:
        return None
    return int(quantity_match.group(1).replace(",", ""))


def extract_grade(text: str) -> str | None:
    for candidate in ("상", "중", "하"):
        if re.search(rf"{candidate}\s*(?:등급|품질|상품성)", text):
            return candidate

    quality_text = (
        text.replace("중과", "")
        .replace("대과", "")
        .replace("중 크기", "")
        .replace("대 크기", "")
        .replace("중 사이즈", "")
        .replace("대 사이즈", "")
    )
    for candidate in ("상", "중", "하", "보통", "특"):
        if candidate in quality_text:
            return normalize_quality_grade(candidate)
    return None


def extract_size_class(text: str) -> str | None:
    if any(keyword in text for keyword in ("중과", "중 크기", "중 사이즈")):
        return "중"
    if any(keyword in text for keyword in ("대과", "대 크기", "대 사이즈", "큰")):
        return "대"
    return None


def list_products() -> list[dict]:
    commitments = get_listing_commitments()
    products: list[dict] = []
    for product in list_inventory_products():
        committed = commitments.get(
            (product["product_name"], product["size_class"], product["grade"]),
            {},
        )
        listed_kg = int(committed.get("listed_kg", 0))
        sold_kg = int(committed.get("sold_kg", 0))
        remaining_listing_kg = int(committed.get("remaining_listing_kg", 0))
        products.append(
            {
                **product,
                "estimated_unit_weight_kg": SIZE_WEIGHT_KG[product["size_class"]],
                "base_available_kg": decimal_to_float(product["available_kg"]),
                "available_kg": round(max(decimal_to_float(product["available_kg"]) - listed_kg, 0), 3),
                "listed_kg": listed_kg,
                "sold_kg": sold_kg,
                "remaining_listing_kg": remaining_listing_kg,
                "recommended_price_per_kg": get_recommended_price_per_kg(
                    product["size_class"],
                    product["grade"],
                    fallback_price=int(product["recommended_price_per_kg"]),
                ),
            }
        )
    return products


def parse_sales_registration_request(text: str, context_text: str | None = None) -> dict | None:
    action_keywords = (
        "올려",
        "등록해",
        "등록해줘",
        "판매해",
        "판매 등록",
        "쇼핑몰에",
    )
    if not any(keyword in text for keyword in action_keywords):
        return None

    context_text = context_text or ""

    quantity_kg = extract_quantity_kg(text)
    if quantity_kg is None:
        quantity_kg = extract_quantity_kg(context_text)
    if quantity_kg is None:
        return None

    product_name = "사과"
    size_class = extract_size_class(text) or extract_size_class(context_text) or "대"
    grade = extract_grade(text) or extract_grade(context_text) or "상"
    product = get_product_template(product_name, size_class, grade)
    validate_new_listing_quantity(product_name, size_class, grade, quantity_kg)

    return {
        "product_name": product_name,
        "size_class": size_class,
        "grade": grade,
        "quantity_kg": quantity_kg,
        "estimated_unit_weight_kg": SIZE_WEIGHT_KG[size_class],
        "price_per_kg": product["recommended_price_per_kg"],
        "package_unit": product["package_unit"],
        "sales_channel": product["sales_channel"],
        "description": (
            f"{product_name} {size_class}과 {grade} 등급 상품입니다. "
            f"{product['package_unit']} 단위로 판매하며, 주문 확인 후 순차 출고합니다."
        ),
    }


def register_listing_from_chat_request(
    text: str,
    history: list[dict[str, str]] | None = None,
    summary: str | None = None,
) -> dict | None:
    history_text = "\n".join(
        f"사용자: {turn['user']}\n답변: {turn['assistant']}"
        for turn in history or []
    )
    context_text = "\n".join(part for part in (summary, history_text) if part)

    data = parse_sales_registration_request(text, context_text=context_text)
    if data is None:
        return None

    draft = create_draft(data)
    return register_draft(int(draft["id"]))


def create_notification(event_type: str, title: str, message: str) -> int:
    with db_cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO notifications (event_type, title, message)
            VALUES (?, ?, ?)
            """,
            (event_type, title, message),
        )
        return int(cursor.lastrowid)


def record_harvest_event(
    size_class: str,
    quality_grade: str,
    product_name: str = "사과",
) -> dict:
    if size_class not in SIZE_WEIGHT_KG:
        raise ValueError("size_class must be one of: 대, 중")
    if quality_grade not in QUALITY_PRICE_MULTIPLIER:
        raise ValueError("quality_grade must be one of: 상, 중, 하")

    product_name = product_name.strip() or "사과"
    grade = normalize_quality_grade(quality_grade)
    product = get_product_template(product_name, size_class, grade)
    estimated_weight_kg = float(SIZE_WEIGHT_KG[size_class])

    with db_cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO harvest_events (
                product_name, size_class, quality_grade, estimated_weight_kg
            )
            VALUES (?, ?, ?, ?)
            """,
            (product_name, size_class, grade, estimated_weight_kg),
        )
        event_id = int(cursor.lastrowid)
        cursor.execute(
            """
            UPDATE apple_inventory
            SET available_kg = available_kg + ?
            WHERE product_name = ? AND size_class = ? AND grade = ?
            """,
            (estimated_weight_kg, product_name, size_class, grade),
        )
        if cursor.rowcount == 0:
            cursor.execute(
                """
                INSERT INTO apple_inventory (
                    product_name, size_class, grade, available_kg, reserved_kg,
                    package_unit, sales_channel
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    product_name,
                    size_class,
                    grade,
                    estimated_weight_kg,
                    0,
                    product["package_unit"],
                    product["sales_channel"],
                ),
            )
        cursor.execute(
            """
            SELECT available_kg
            FROM apple_inventory
            WHERE product_name = ? AND size_class = ? AND grade = ?
            """,
            (product_name, size_class, grade),
        )
        inventory = cursor.fetchone()

    current_base_available_kg = decimal_to_float(inventory["available_kg"])
    current_available_kg = get_available_kg(product_name, size_class, grade)
    return {
        "id": event_id,
        "product_name": product_name,
        "size_class": size_class,
        "quality_grade": grade,
        "estimated_weight_kg": estimated_weight_kg,
        "current_base_available_kg": current_base_available_kg,
        "current_available_kg": current_available_kg,
    }


def create_draft(data: dict) -> dict:
    validate_new_listing_quantity(
        data["product_name"],
        data["size_class"],
        data["grade"],
        int(data["quantity_kg"]),
    )
    with db_cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO sales_drafts (
                product_name, size_class, grade, quantity_kg, estimated_unit_weight_kg, price_per_kg,
                package_unit, sales_channel, description
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data["product_name"],
                data["size_class"],
                data["grade"],
                data["quantity_kg"],
                data["estimated_unit_weight_kg"],
                data["price_per_kg"],
                data["package_unit"],
                data["sales_channel"],
                data["description"],
            ),
        )
        draft_id = int(cursor.lastrowid)

    create_notification(
        "draft_created",
        "상품등록 준비",
        f"{data['product_name']} {data['size_class']}과 {data['grade']} 등급 {data['quantity_kg']}kg 상품등록 정보가 준비되었습니다.",
    )
    return get_draft(draft_id)


def get_draft(draft_id: int) -> dict:
    with db_cursor() as cursor:
        cursor.execute("SELECT * FROM sales_drafts WHERE id = ?", (draft_id,))
        row = cursor.fetchone()
    if not row:
        raise ValueError("Sales draft not found")
    return row


def list_drafts() -> list[dict]:
    with db_cursor() as cursor:
        cursor.execute("SELECT * FROM sales_drafts ORDER BY id DESC")
        return list(cursor.fetchall())


def update_draft(draft_id: int, data: dict) -> dict:
    validate_new_listing_quantity(
        data["product_name"],
        data["size_class"],
        data["grade"],
        int(data["quantity_kg"]),
    )
    with db_cursor() as cursor:
        cursor.execute(
            """
            UPDATE sales_drafts
            SET product_name = ?, size_class = ?, grade = ?, quantity_kg = ?,
                estimated_unit_weight_kg = ?, price_per_kg = ?,
                package_unit = ?, sales_channel = ?, description = ?
            WHERE id = ? AND status IN ('draft', 'approved')
            """,
            (
                data["product_name"],
                data["size_class"],
                data["grade"],
                data["quantity_kg"],
                data["estimated_unit_weight_kg"],
                data["price_per_kg"],
                data["package_unit"],
                data["sales_channel"],
                data["description"],
                draft_id,
            ),
        )
        if cursor.rowcount == 0:
            raise ValueError("Editable sales draft not found")
    return get_draft(draft_id)


def approve_draft(draft_id: int) -> dict:
    with db_cursor() as cursor:
        cursor.execute(
            "UPDATE sales_drafts SET status = 'approved' WHERE id = ? AND status = 'draft'",
            (draft_id,),
        )
        if cursor.rowcount == 0:
            raise ValueError("Draft status must be draft")

    draft = get_draft(draft_id)
    create_notification(
        "draft_approved",
        "상품등록 확인",
        f"{draft['product_name']} {draft['size_class']}과 {draft['grade']} 등급 상품등록 정보가 확인되었습니다.",
    )
    return draft


def register_draft(draft_id: int) -> dict:
    draft = get_draft(draft_id)
    if draft["status"] not in {"draft", "approved"}:
        raise ValueError("Draft is already registered or closed")

    validate_new_listing_quantity(
        draft["product_name"],
        draft["size_class"],
        draft["grade"],
        int(draft["quantity_kg"]),
    )

    with db_cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO sales_listings (
                draft_id, product_name, size_class, grade, quantity_kg, original_quantity_kg,
                estimated_unit_weight_kg, price_per_kg,
                package_unit, sales_channel, description
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                draft_id,
                draft["product_name"],
                draft["size_class"],
                draft["grade"],
                draft["quantity_kg"],
                draft["quantity_kg"],
                draft["estimated_unit_weight_kg"],
                draft["price_per_kg"],
                draft["package_unit"],
                draft["sales_channel"],
                draft["description"],
            ),
        )
        listing_id = int(cursor.lastrowid)
        cursor.execute(
            "UPDATE sales_drafts SET status = 'registered' WHERE id = ?",
            (draft_id,),
        )

    create_notification(
        "listing_registered",
        "판매 등록 완료",
        (
            f"{draft['product_name']} {draft['size_class']}과 {draft['grade']} 등급 {draft['quantity_kg']}kg이 "
            f"{draft['sales_channel']}에 등록되었습니다. kg당 판매가: {draft['price_per_kg']:,}원"
        ),
    )
    return get_listing(listing_id)


def get_listing(listing_id: int) -> dict:
    with db_cursor() as cursor:
        cursor.execute("SELECT * FROM sales_listings WHERE id = ?", (listing_id,))
        row = cursor.fetchone()
    if not row:
        raise ValueError("Sales listing not found")
    return row


def list_listings() -> list[dict]:
    with db_cursor() as cursor:
        cursor.execute("SELECT * FROM sales_listings ORDER BY id DESC")
        return list(cursor.fetchall())


def place_order(
    listing_id: int,
    customer_name: str,
    quantity_kg: int,
    customer_user_id: int | None = None,
) -> dict:
    with db_cursor() as cursor:
        cursor.execute(
            "SELECT * FROM sales_listings WHERE id = ? FOR UPDATE",
            (listing_id,),
        )
        listing = cursor.fetchone()
        if not listing:
            raise ValueError("Sales listing not found")
        if listing["status"] != "active":
            raise ValueError("Only active listings can receive orders")
        if quantity_kg < 1 or quantity_kg > int(listing["quantity_kg"]):
            raise ValueError("Order quantity exceeds listing quantity")

        total_amount = quantity_kg * int(listing["price_per_kg"])
        remaining_quantity = int(listing["quantity_kg"]) - quantity_kg
        next_status = "sold_out" if remaining_quantity == 0 else "active"

        cursor.execute(
            """
            INSERT INTO sales_orders (
                listing_id, customer_user_id, customer_name, quantity_kg, total_amount
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (listing_id, customer_user_id, customer_name, quantity_kg, total_amount),
        )
        order_id = int(cursor.lastrowid)
        cursor.execute(
            """
            UPDATE sales_listings
            SET quantity_kg = ?, status = ?
            WHERE id = ?
            """,
            (remaining_quantity, next_status, listing_id),
        )
        cursor.execute(
            """
            INSERT INTO notifications (event_type, title, message)
            VALUES (?, ?, ?)
            """,
            (
                "order_created",
                "쇼핑몰 주문 발생",
                (
                    f"{customer_name} 고객이 {listing['product_name']} {listing['size_class']}과 {listing['grade']} 등급 "
                    f"{quantity_kg}kg을 주문했습니다. 주문 금액: {total_amount:,}원, "
                    f"남은 판매수량: {remaining_quantity:,}kg"
                ),
            ),
        )
    return get_order(order_id)


def get_order(order_id: int) -> dict:
    with db_cursor() as cursor:
        cursor.execute("SELECT * FROM sales_orders WHERE id = ?", (order_id,))
        row = cursor.fetchone()
    if not row:
        raise ValueError("Sales order not found")
    return row


def list_orders() -> list[dict]:
    with db_cursor() as cursor:
        cursor.execute("SELECT * FROM sales_orders ORDER BY id DESC")
        return list(cursor.fetchall())


def list_user_orders(customer_user_id: int) -> list[dict]:
    with db_cursor() as cursor:
        cursor.execute(
            """
            SELECT
                sales_orders.*,
                sales_listings.product_name,
                sales_listings.size_class,
                sales_listings.grade,
                sales_listings.package_unit,
                sales_listings.price_per_kg
            FROM sales_orders
            JOIN sales_listings
              ON sales_orders.listing_id = sales_listings.id
            WHERE sales_orders.customer_user_id = ?
            ORDER BY sales_orders.id DESC
            """,
            (customer_user_id,),
        )
        return list(cursor.fetchall())


def ensure_demo_purchase_history(customer_user_id: int, customer_name: str) -> None:
    with db_cursor() as cursor:
        cursor.execute(
            "SELECT COUNT(*) AS count FROM sales_orders WHERE customer_user_id = ?",
            (customer_user_id,),
        )
        if int(cursor.fetchone()["count"]) > 0:
            return

    listings = [
        listing
        for listing in list_listings()
        if listing["status"] == "active" and int(listing["quantity_kg"]) >= 5
    ]
    if not listings:
        return

    demo_quantities = [5, 10, 5]
    for index, quantity_kg in enumerate(demo_quantities):
        listing = listings[index % len(listings)]
        unit = 5 if "5kg" in listing["package_unit"] else 10
        quantity = max(unit, quantity_kg)
        if quantity <= int(get_listing(int(listing["id"]))["quantity_kg"]):
            place_order(
                int(listing["id"]),
                customer_name,
                quantity,
                customer_user_id=customer_user_id,
            )


def list_notifications(limit: int = 20) -> list[dict]:
    with db_cursor() as cursor:
        cursor.execute(
            """
            SELECT *
            FROM notifications
            WHERE event_type <> 'harvest_recorded'
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        )
        return list(cursor.fetchall())


def mark_notification_read(notification_id: int) -> dict:
    with db_cursor() as cursor:
        cursor.execute(
            "UPDATE notifications SET is_read = TRUE WHERE id = ?",
            (notification_id,),
        )
    with db_cursor() as cursor:
        cursor.execute("SELECT * FROM notifications WHERE id = ?", (notification_id,))
        row = cursor.fetchone()
    if not row:
        raise ValueError("Notification not found")
    return row


def ensure_app_settings_table() -> None:
    with db_cursor() as cursor:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS app_settings (
                setting_key VARCHAR(120) PRIMARY KEY,
                setting_value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
            """
        )


def get_app_setting(setting_key: str, default_value: str) -> str:
    ensure_app_settings_table()
    with db_cursor() as cursor:
        cursor.execute(
            "SELECT setting_value FROM app_settings WHERE setting_key = ?",
            (setting_key,),
        )
        row = cursor.fetchone()
    if not row:
        return default_value
    return str(row["setting_value"])


def set_app_setting(setting_key: str, setting_value: str) -> str:
    ensure_app_settings_table()
    value = setting_value.strip()
    if not value:
        raise ValueError("Setting value must not be empty")

    with db_cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO app_settings (setting_key, setting_value)
            VALUES (?, ?)
            ON DUPLICATE KEY UPDATE
                setting_value = VALUES(setting_value),
                updated_at = CURRENT_TIMESTAMP
            """,
            (setting_key, value),
        )
    return value
