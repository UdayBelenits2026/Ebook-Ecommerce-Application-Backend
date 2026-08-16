from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.email.service import EmailService
from app.email.templates import order_confirmation_email
from app.database.session import get_db
from app.models.domain import (
    Order,
    OrderItem,
    Cart,
    CartItem,
    User,
    Book,
    OrderStatus,
    Address
)

from app.schemas.order import OrderPlace
from app.schemas.response import ApiResponse
from app.dependencies.auth import get_current_user
from datetime import datetime
from app.orders.service import OrderService

router = APIRouter(
    prefix="/orders",
    tags=["Orders"]
)
@router.get("/{order_id}", response_model=ApiResponse)
def get_order_detail(
    order_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Get detailed information about a single order.
    """

    sql = text("""
        SELECT
            o.id,
            o.user_id,
            o.total_amount,
            o.payment_method,
            o.order_status,
            o.address_id,
            o.shipping_address,
            o.created_at,

            oi.id AS item_id,
            oi.book_id,
            oi.quantity,
            oi.price AS item_price,

            b.title,
            b.author,
            b.image

        FROM orders o

        LEFT JOIN order_items oi
            ON oi.order_id = o.id

        LEFT JOIN books b
            ON b.id = oi.book_id

        WHERE
            o.id = :oid
            AND o.user_id = :uid

        ORDER BY oi.id
    """)

    rows = db.execute(
        sql,
        {
            "oid": order_id,
            "uid": user.id
        }
    ).mappings().all()

    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    items = []
    subtotal = 0.0

    for row in rows:

        if row["item_id"]:

            item_subtotal = float(row["item_price"]) * row["quantity"]

            subtotal += item_subtotal

            items.append({
                "id": row["item_id"],
                "book_id": row["book_id"],
                "title": row["title"],
                "author": row["author"],
                "image": row["image"],
                "quantity": row["quantity"],
                "price": float(row["item_price"]),
                "subtotal": item_subtotal
            })

    shipping = 0.0 if subtotal >= 500 else 50.0
    grand_total = subtotal + shipping

    first_row = dict(rows[0])

    return ApiResponse(
        success=True,
        message="Success",
        data={
            "id": first_row["id"],
            "user_id": first_row["user_id"],
            "total_amount": float(first_row["total_amount"]),
            "payment_method": first_row["payment_method"],
            "order_status": first_row["order_status"],

            "address_id": first_row["address_id"],

            "shipping_address": first_row["shipping_address"],

            "created_at": first_row["created_at"],

            "items": items,

            "subtotal": subtotal,
            "shipping": shipping,
            "grand_total": grand_total
        }
    )
@router.get("", response_model=ApiResponse)
def get_orders(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Get all orders for the authenticated user,
    including order items with book details.
    """

    sql = text("""
        SELECT
            o.id,
            o.user_id,
            o.total_amount,
            o.payment_method,
            o.order_status,
            o.address_id,
            o.shipping_address,
            o.created_at,

            oi.id AS item_id,
            oi.book_id,
            oi.quantity,
            oi.price AS item_price,

            b.title,
            b.author,
            b.image

        FROM orders o

        LEFT JOIN order_items oi
            ON oi.order_id = o.id

        LEFT JOIN books b
            ON b.id = oi.book_id

        WHERE
            o.user_id = :uid

        ORDER BY
            o.created_at DESC,
            oi.id
    """)

    rows = db.execute(
        sql,
        {"uid": user.id}
    ).mappings().all()

    orders_map = {}

    for row in rows:

        oid = row["id"]

        if oid not in orders_map:

            orders_map[oid] = {
                "id": row["id"],
                "user_id": row["user_id"],
                "total_amount": float(row["total_amount"]),
                "payment_method": row["payment_method"],
                "order_status": row["order_status"],

                "address_id": row["address_id"],

                "shipping_address": row["shipping_address"],

                "created_at": row["created_at"],

                "items": []
            }

        if row["item_id"]:

            orders_map[oid]["items"].append({
                "id": row["item_id"],
                "book_id": row["book_id"],
                "quantity": row["quantity"],
                "price": float(row["item_price"]),
                "title": row["title"],
                "author": row["author"],
                "image": row["image"]
            })

    orders = list(orders_map.values())

    return ApiResponse(
        success=True,
        message="Success",
        data=orders
    )
@router.delete("/cancel/{id}", response_model=ApiResponse)
def cancel_order(
    id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Cancel an order.
    Restores stock for all ordered books.
    """

    order = db.query(Order).filter_by(
        id=id,
        user_id=user.id
    ).first()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    if order.order_status == OrderStatus.CANCELLED:
        return ApiResponse(
            success=True,
            message="Order was already cancelled"
        )

    if order.order_status not in [OrderStatus.PENDING, OrderStatus.PROCESSING]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel order with status '{order.order_status.value if hasattr(order.order_status, 'value') else order.order_status}'"
        )

    # Restore stock for each book in the cancelled order
    for item in order.items:
        book = db.query(Book).filter(Book.id == item.book_id).first()
        if book:
            book.stock += item.quantity

    order.order_status = OrderStatus.CANCELLED
    db.commit()

    return ApiResponse(
        success=True,
        message="Order cancelled successfully"
    )
@router.post("/place", response_model=ApiResponse)
def place_order(
    order_data: OrderPlace,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    result = OrderService.place_order(
        db=db,
        user=user,
        payment_method=order_data.payment_method,
        address_id=order_data.address_id,
    )

    return ApiResponse(
        success=True,
        message=result["message"],
        data=result,
    )