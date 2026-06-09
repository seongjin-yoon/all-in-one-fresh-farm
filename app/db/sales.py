import re

from app.db.connection import db_cursor


SIZE_WEIGHT_KG = {
    "대": 0.32,
    "중": 0.24,
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
    return next(
        item
        for item in SAMPLE_PRODUCTS
        if (
            item["product_name"] == product_name
            and item["size_class"] == size_class
            and item["grade"] == grade
        )
    )


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


def get_available_kg(product_name: str, size_class: str, grade: str) -> int:
    size_class = normalize_size_class(size_class)
    grade = normalize_quality_grade(grade)
    product = get_product_template(product_name, size_class, grade)
    commitments = get_listing_commitments().get((product_name, size_class, grade), {})
    return max(int(product["available_kg"]) - int(commitments.get("listed_kg", 0)), 0)


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
    for product in SAMPLE_PRODUCTS:
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
                "base_available_kg": int(product["available_kg"]),
                "available_kg": max(int(product["available_kg"]) - listed_kg, 0),
                "listed_kg": listed_kg,
                "sold_kg": sold_kg,
                "remaining_listing_kg": remaining_listing_kg,
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
        "판매 초안 생성",
        f"{data['product_name']} {data['size_class']}과 {data['grade']} 등급 {data['quantity_kg']}kg 판매 초안이 생성되었습니다.",
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
        "판매 초안 승인",
        f"{draft['product_name']} {draft['size_class']}과 {draft['grade']} 등급 판매 초안이 승인되었습니다. 최종 등록을 진행할 수 있습니다.",
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
