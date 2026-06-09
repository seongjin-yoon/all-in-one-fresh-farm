from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.db.sales import (
    approve_draft,
    create_draft,
    ensure_demo_purchase_history,
    list_drafts,
    list_listings,
    list_notifications,
    list_orders,
    list_products,
    list_user_orders,
    mark_notification_read,
    place_order,
    register_draft,
    update_draft,
)

router = APIRouter(prefix="/sales", tags=["sales"])


class ProductInventory(BaseModel):
    product_name: str
    size_class: str
    grade: str
    estimated_unit_weight_kg: float
    base_available_kg: int
    available_kg: int
    reserved_kg: int
    listed_kg: int
    sold_kg: int
    remaining_listing_kg: int
    recommended_price_per_kg: int
    package_unit: str
    sales_channel: str


class SalesDraftRequest(BaseModel):
    product_name: str = Field(..., min_length=1)
    size_class: str = Field(..., min_length=1)
    grade: str = Field(..., min_length=1)
    quantity_kg: int = Field(..., ge=1)
    estimated_unit_weight_kg: float = Field(..., gt=0)
    price_per_kg: int = Field(..., ge=1)
    package_unit: str = Field(..., min_length=1)
    sales_channel: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)


class SalesDraft(BaseModel):
    id: int
    product_name: str
    size_class: str
    grade: str
    quantity_kg: int
    estimated_unit_weight_kg: float
    price_per_kg: int
    package_unit: str
    sales_channel: str
    description: str
    status: str
    created_at: datetime
    updated_at: datetime


class SalesListing(BaseModel):
    id: int
    draft_id: int
    product_name: str
    size_class: str
    grade: str
    quantity_kg: int
    original_quantity_kg: int
    estimated_unit_weight_kg: float
    price_per_kg: int
    package_unit: str
    sales_channel: str
    description: str
    status: str
    created_at: datetime


class SalesOrderRequest(BaseModel):
    customer_name: str = Field(..., min_length=1)
    quantity_kg: int = Field(..., ge=1)
    customer_user_id: int | None = None


class SalesOrder(BaseModel):
    id: int
    listing_id: int
    customer_user_id: int | None = None
    customer_name: str
    quantity_kg: int
    total_amount: int
    status: str
    created_at: datetime


class SalesOrderHistory(SalesOrder):
    product_name: str
    size_class: str
    grade: str
    package_unit: str
    price_per_kg: int


class Notification(BaseModel):
    id: int
    event_type: str
    title: str
    message: str
    is_read: bool
    created_at: datetime


@router.get("/products", response_model=list[ProductInventory])
def products() -> list[ProductInventory]:
    return [ProductInventory(**product) for product in list_products()]


@router.get("/drafts", response_model=list[SalesDraft])
def drafts() -> list[SalesDraft]:
    return [SalesDraft(**draft) for draft in list_drafts()]


@router.post("/drafts", response_model=SalesDraft)
def create_sales_draft(request: SalesDraftRequest) -> SalesDraft:
    try:
        return SalesDraft(**create_draft(request.model_dump()))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put("/drafts/{draft_id}", response_model=SalesDraft)
def edit_sales_draft(draft_id: int, request: SalesDraftRequest) -> SalesDraft:
    try:
        return SalesDraft(**update_draft(draft_id, request.model_dump()))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/drafts/{draft_id}/approve", response_model=SalesDraft)
def approve_sales_draft(draft_id: int) -> SalesDraft:
    try:
        return SalesDraft(**approve_draft(draft_id))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/drafts/{draft_id}/register", response_model=SalesListing)
def register_sales_draft(draft_id: int) -> SalesListing:
    try:
        return SalesListing(**register_draft(draft_id))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/listings", response_model=list[SalesListing])
def listings() -> list[SalesListing]:
    return [SalesListing(**listing) for listing in list_listings()]


@router.get("/orders", response_model=list[SalesOrder])
def orders() -> list[SalesOrder]:
    return [SalesOrder(**order) for order in list_orders()]


@router.get("/orders/users/{customer_user_id}", response_model=list[SalesOrderHistory])
def user_orders(customer_user_id: int, customer_name: str = "테스트 고객") -> list[SalesOrderHistory]:
    ensure_demo_purchase_history(customer_user_id, customer_name)
    return [SalesOrderHistory(**order) for order in list_user_orders(customer_user_id)]


@router.post("/listings/{listing_id}/orders", response_model=SalesOrder)
def create_order(listing_id: int, request: SalesOrderRequest) -> SalesOrder:
    try:
        return SalesOrder(
            **place_order(
                listing_id,
                request.customer_name,
                request.quantity_kg,
                customer_user_id=request.customer_user_id,
            )
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/notifications", response_model=list[Notification])
def notifications() -> list[Notification]:
    return [Notification(**notification) for notification in list_notifications()]


@router.post("/notifications/{notification_id}/read", response_model=Notification)
def read_notification(notification_id: int) -> Notification:
    try:
        return Notification(**mark_notification_read(notification_id))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
