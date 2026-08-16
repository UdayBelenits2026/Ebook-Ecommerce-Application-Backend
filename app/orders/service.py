from datetime import datetime
from typing import Dict, Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.email.service import EmailService
from app.email.templates import order_confirmation_email
from app.models.domain import (
    Address,
    Book,
    Cart,
    CartItem,
    Order,
    OrderItem,
    OrderStatus,
    User,
)


class OrderService:
    """
    Unified Order Service responsible for order processing in the database.
    Contains 100% of order creation, stock deduction, cart clearing, and email triggers.
    Used by both Cash on Delivery (COD) and Online Payments (Cashfree).
    """

    @staticmethod
    def place_order(
        *,
        db: Session,
        user: User,
        payment_method: str,
        address_id: int,
    ) -> Dict[str, Any]:
        """
        Creates an order after validating:
            • Cart existence & items
            • Shipping Address validity
            • Book stock availability

        This method is used by both COD and Online payments.
        """
        # --------------------------------------------------
        # 1. Fetch & Validate Cart
        # --------------------------------------------------
        cart = db.query(Cart).filter(Cart.user_id == user.id).first()

        if not cart or not cart.items:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cart is empty or not found"
            )

        # --------------------------------------------------
        # 2. Fetch & Validate Address
        # --------------------------------------------------
        address = db.query(Address).filter(
            Address.id == address_id,
            Address.user_id == user.id
        ).first()

        if not address:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Selected shipping address not found"
            )

        # --------------------------------------------------
        # 3. Calculate Amount & Validate Stock
        # --------------------------------------------------
        subtotal = 0.0

        for item in cart.items:
            book = db.query(Book).filter(Book.id == item.book_id).first()

            if not book:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Book ID {item.book_id} not found"
                )

            if book.stock < item.quantity:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Insufficient stock for '{book.title}'. Requested: {item.quantity}, Available: {book.stock}"
                )

            subtotal += float(book.price) * item.quantity

        # --------------------------------------------------
        # 4. Shipping Calculation
        # --------------------------------------------------
        shipping = 0.0 if subtotal >= 500.0 else 50.0
        grand_total = subtotal + shipping

        # --------------------------------------------------
        # 5. Build Shipping Address Snapshot
        # --------------------------------------------------
        shipping_address = f"""
Name: {address.full_name}
Mobile: {address.mobile}
House No: {address.house_no}
Street: {address.street or ""}
Area: {address.area}
Village/City: {address.village_city}
District: {address.district}
State: {address.state}
Pincode: {address.pincode}
Landmark: {address.landmark or ""}
""".strip()

        # --------------------------------------------------
        # 6. Create Order Entity
        # --------------------------------------------------
        new_order = Order(
            user_id=user.id,
            total_amount=grand_total,
            payment_method=payment_method,
            address_id=address.id,
            shipping_address=shipping_address,
            order_status=OrderStatus.PENDING,
        )

        db.add(new_order)
        db.flush()  # Obtain order ID before creating items

        # --------------------------------------------------
        # 7. Create Order Items & Deduct Stock
        # --------------------------------------------------
        email_items = []

        for item in cart.items:
            book = db.query(Book).filter(Book.id == item.book_id).first()

            order_item = OrderItem(
                order_id=new_order.id,
                book_id=book.id,
                quantity=item.quantity,
                price=book.price
            )
            db.add(order_item)

            email_items.append({
                "title": book.title,
                "quantity": item.quantity,
                "price": float(book.price),
                "subtotal": float(book.price) * item.quantity
            })

            # Deduct inventory stock
            book.stock -= item.quantity

        # --------------------------------------------------
        # 8. Clear User Cart
        # --------------------------------------------------
        db.query(CartItem).filter(CartItem.cart_id == cart.id).delete()
        db.delete(cart)

        # --------------------------------------------------
        # 9. Commit Database Changes
        # --------------------------------------------------
        db.commit()
        db.refresh(new_order)

        # --------------------------------------------------
        # 10. Send Order Confirmation Email
        # --------------------------------------------------
        try:
            html, text_body = order_confirmation_email(
                customer_name=user.full_name,
                order_id=new_order.id,
                order_date=datetime.now(),
                payment_method=new_order.payment_method,
                shipping_address=shipping_address,
                items=email_items,
                subtotal=subtotal,
                shipping=shipping,
                grand_total=grand_total
            )

            EmailService.send_email(
                to_email=user.email,
                subject=f"Order Confirmation #{new_order.id}",
                html_body=html,
                text_body=text_body
            )
        except Exception as e:
            print(f"[Email Error] Failed to send order confirmation email: {e}")

        # --------------------------------------------------
        # 11. Return Order Response
        # --------------------------------------------------
        return {
            "order_id": new_order.id,
            "subtotal": subtotal,
            "shipping": shipping,
            "total_amount": grand_total,
            "payment_method": payment_method,
            "order_status": new_order.order_status.value if hasattr(new_order.order_status, "value") else str(new_order.order_status),
            "shipping_address": shipping_address,
            "items": email_items,
            "message": "Order placed successfully"
        }
