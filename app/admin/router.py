from fastapi import APIRouter, Depends, UploadFile, File
import os
import shutil
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database.session import get_db
from app.models.domain import User, Book, Category, Order, Review, ContactMessage, Notification
from app.schemas.book import BookOut
from app.schemas.response import ApiResponse
from app.utils.serialization import orm_to_dict, orm_list_to_dicts
from app.schemas.admin import StatusUpdate, OrderStatusUpdate, ChangePassword, AdminProfileUpdate, TrackingUpdate
from app.utils.security import verify_password, get_password_hash
from app.utils.dependencies import require_admin
from app.email.service import EmailService
from app.email.templates import order_status_email

router = APIRouter(prefix="/admin", tags=["Admin Panel"])

# ==========================================
# ADMIN PROFILE & SETTINGS
# ==========================================
@router.get("/profile", response_model=ApiResponse)
def get_admin_profile(admin: User = Depends(require_admin)):
    return ApiResponse(
        success=True,
        message="Profile fetched",
        data={
            "full_name": admin.full_name,
            "email": admin.email,
            "phone": admin.phone,
            "profile_image": admin.profile_image
        }
    )

@router.put("/change-password", response_model=ApiResponse)
def change_admin_password(data: ChangePassword, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    if not verify_password(data.old_password, admin.password):
        return ApiResponse(success=False, message="Incorrect old password")
    admin.password = get_password_hash(data.new_password)
    db.commit()
    return ApiResponse(success=True, message="Password updated successfully")

@router.put("/profile", response_model=ApiResponse)
def update_admin_profile(data: AdminProfileUpdate, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    if data.full_name:
        admin.full_name = data.full_name
    if data.phone:
        admin.phone = data.phone
        
    db.commit()
    
    return ApiResponse(
        success=True, 
        message="Profile updated successfully", 
        data={
            "full_name": admin.full_name, 
            "phone": admin.phone,
            "profile_image": admin.profile_image
        }
    )

@router.post("/profile/upload-image", response_model=ApiResponse)
def upload_admin_image(file: UploadFile = File(...), admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    # Create the uploads directory if it doesn't exist
    upload_dir = "static/uploads/users"
    os.makedirs(upload_dir, exist_ok=True)
    
    # Generate a unique filename using timestamp
    file_extension = file.filename.split(".")[-1]
    file_name = f"admin_{admin.id}_{int(datetime.now().timestamp())}.{file_extension}"
    file_path = f"{upload_dir}/{file_name}"
    
    # Save the file to the local directory
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # Update the database with the file path
    admin.profile_image = f"/{file_path}"
    db.commit()
    
    return ApiResponse(
        success=True, 
        message="Profile image uploaded successfully", 
        data={"profile_image": admin.profile_image}
    )

# ==========================================
# DASHBOARD
# ==========================================
@router.get("/dashboard", response_model=ApiResponse)
def get_dashboard_stats(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    total_users = db.query(User).filter(User.role == "customer").count()
    total_books = db.query(Book).count()
    total_categories = db.query(Category).count()
    total_orders = db.query(Order).count()
    
    # Assuming Order has a total_amount column
    total_revenue = db.query(func.sum(Order.total_amount)).scalar() or 0.0
    
    # Books with stock less than 10
    low_stock_books = db.query(Book).filter(Book.stock < 10).all()
    low_stock_books_out = [BookOut.model_validate(book).model_dump() for book in low_stock_books]
    
    return ApiResponse(success=True, message="Dashboard stats retrieved", data={
        "total_users": total_users,
        "total_books": total_books,
        "total_categories": total_categories,
        "total_orders": total_orders,
        "total_revenue": total_revenue,
        "low_stock_books": low_stock_books_out
    })

# ==========================================
# USER MANAGEMENT
# ==========================================
@router.get("/users", response_model=ApiResponse)
def get_all_users(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    users = db.query(User).all()
    return ApiResponse(success=True, message="Users fetched", data=orm_list_to_dicts(users))

@router.get("/users/{id}", response_model=ApiResponse)
def get_user(id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    user = db.query(User).filter(User.id == id).first()
    if not user: return ApiResponse(success=False, message="User not found")
    return ApiResponse(success=True, message="User fetched", data=orm_to_dict(user))

@router.patch("/users/{id}/status", response_model=ApiResponse)
def update_user_status(id: int, data: StatusUpdate, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    user = db.query(User).filter(User.id == id).first()
    if not user: return ApiResponse(success=False, message="User not found")
    
    user.is_active = (data.status.lower() == "active")
    db.commit()
    return ApiResponse(success=True, message=f"User status updated to {data.status}")

@router.delete("/users/{id}", response_model=ApiResponse)
def delete_user(id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    user = db.query(User).filter(User.id == id).first()
    if not user: return ApiResponse(success=False, message="User not found")
    db.delete(user)
    db.commit()
    return ApiResponse(success=True, message="User deleted successfully")

# ==========================================
# MARK CONTACT MESSAGE AS READ
# ==========================================
@router.patch("/contact-messages/{id}/read", response_model=ApiResponse)
def mark_contact_message_read(id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    message = db.query(ContactMessage).filter(ContactMessage.id == id).first()

    if not message:
        return ApiResponse(success=False, message="Message not found")

    message.is_read = True

    db.commit()
    db.refresh(message)

    return ApiResponse(
        success=True,
        message="Message marked as read",
        data=orm_to_dict(message)
    )

# ==========================================
# ORDER MANAGEMENT
# ==========================================
@router.get("/orders", response_model=ApiResponse)
def get_all_orders(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    orders = db.query(Order).all()
    data = []

    for order in orders:
        user = db.query(User).filter(User.id == order.user_id).first()
        data.append({
            "id": order.id,
            "user_id": order.user_id,
            "user_name": user.full_name if user else "Unknown",
            "email": user.email if user else "",
            "phone": user.phone if user else "",
            "total_amount": order.total_amount,
            "payment_method": order.payment_method,
            "order_status": order.order_status,
            "shipping_address": order.shipping_address,
            "tracking_number": order.tracking_number,
            "courier_name": order.courier_name,
            "estimated_delivery": order.estimated_delivery,
            "created_at": order.created_at
        })

    return ApiResponse(success=True, message="Orders fetched", data=data)
@router.patch("/orders/{id}/status", response_model=ApiResponse)
def update_order_status(
    id: int,
    data: OrderStatusUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    valid_statuses = [
        "PENDING",
        "PROCESSING",
        "SHIPPED",
        "DELIVERED",
        "CANCELLED"
    ]

    status = data.status.upper()

    if status not in valid_statuses:
        return ApiResponse(
            success=False,
            message="Invalid status"
        )

    order = db.query(Order).filter(
        Order.id == id
    ).first()

    if not order:
        return ApiResponse(
            success=False,
            message="Order not found"
        )

    # Update order status
    order.order_status = status

    # Create notification for this customer
    notification = Notification(
        user_id=order.user_id,
        title="Order Status Updated",
        message=f"Your order #{order.id} status has been updated to {status}.",
        type="order"
    )

    db.add(notification)

    # Save order and notification
    db.commit()
    db.refresh(order)

    # Get customer details
    user = db.query(User).filter(
        User.id == order.user_id
    ).first()

    # Send email
    if user:

        html, text = order_status_email(
            customer_name=user.full_name,
            order_id=order.id,
            status=order.order_status,
            tracking_number=order.tracking_number,
            courier_name=order.courier_name,
            estimated_delivery=order.estimated_delivery
        )

        EmailService.send_email(
            to_email=user.email,
            subject=f"Order #{order.id} Status Updated",
            html_body=html,
            text_body=text
        )

    return ApiResponse(
        success=True,
        message=f"Order status updated to {status}"
    )
@router.patch("/orders/{id}/status", response_model=ApiResponse)
def update_order_status(
    id: int,
    data: OrderStatusUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    valid_statuses = [
        "PENDING",
        "PROCESSING",
        "SHIPPED",
        "DELIVERED",
        "CANCELLED"
    ]

    status = data.status.upper()

    if status not in valid_statuses:
        return ApiResponse(success=False, message="Invalid status")

    order = db.query(Order).filter(Order.id == id).first()

    if not order:
        return ApiResponse(success=False, message="Order not found")

    # Update status
    order.order_status = status
    db.commit()
    db.refresh(order)

    # Get customer details & Send Email
    user = db.query(User).filter(User.id == order.user_id).first()

    if user:
        html, text = order_status_email(
            customer_name=user.full_name,
            order_id=order.id,
            status=order.order_status,
            tracking_number=order.tracking_number,
            courier_name=order.courier_name,
            estimated_delivery=order.estimated_delivery
        )

        EmailService.send_email(
            to_email=user.email,
            subject=f"Order #{order.id} Status Updated",
            html_body=html,
            text_body=text
        )

    return ApiResponse(
        success=True,
        message=f"Order status updated to {status}"
    )

@router.patch("/orders/{id}/tracking", response_model=ApiResponse)
def update_tracking_details(
    id: int,
    data: TrackingUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    order = db.query(Order).filter(Order.id == id).first()

    if not order:
        return ApiResponse(success=False, message="Order not found")

    order.tracking_number = data.tracking_number
    order.courier_name = data.courier_name
    order.estimated_delivery = data.estimated_delivery

    db.commit()
    db.refresh(order)

    return ApiResponse(
        success=True,
        message="Tracking details updated successfully",
        data={
            "tracking_number": order.tracking_number,
            "courier_name": order.courier_name,
            "estimated_delivery": order.estimated_delivery
        }
    )
@router.get("/orders/{id}", response_model=ApiResponse)
def get_order(
    id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    order = db.query(Order).filter(
        Order.id == id
    ).first()

    if not order:
        return ApiResponse(
            success=False,
            message="Order not found",
            data=None
        )

    user = db.query(User).filter(
        User.id == order.user_id
    ).first()

    data = {
        "id": order.id,
        "user_id": order.user_id,

        "user_name": (
            user.full_name
            if user
            else "Unknown"
        ),

        "email": (
            user.email
            if user
            else ""
        ),

        "phone": (
            user.phone
            if user
            else ""
        ),

        "total_amount": order.total_amount,

        "payment_method": order.payment_method,

        "order_status": order.order_status,

        "shipping_address": order.shipping_address,

        "tracking_number": order.tracking_number,

        "courier_name": order.courier_name,

        "estimated_delivery": order.estimated_delivery,

        "created_at": order.created_at
    }

    return ApiResponse(
        success=True,
        message="Order fetched successfully",
        data=data
    )


# ==========================================
# REVIEW MANAGEMENT
# ==========================================
@router.get("/reviews", response_model=ApiResponse)
def get_all_reviews(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    reviews = db.query(Review).all()
    data = []

    for review in reviews:
        user = db.query(User).filter(User.id == review.user_id).first()
        book = db.query(Book).filter(Book.id == review.book_id).first()
        data.append({
            "id": review.id,
            "user_id": review.user_id,
            "user_name": user.full_name if user else "Unknown",
            "book_id": review.book_id,
            "book_title": book.title if book else "Unknown",
            "rating": review.rating,
            "review": review.review,
            "created_at": review.created_at
        })

    return ApiResponse(success=True, message="Reviews fetched", data=data)

@router.delete("/reviews/{id}", response_model=ApiResponse)
def delete_review(id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    review = db.query(Review).filter(Review.id == id).first()
    if not review: return ApiResponse(success=False, message="Review not found")
    db.delete(review)
    db.commit()
    return ApiResponse(success=True, message="Review deleted successfully")


# ==========================================
# CONTACT MANAGEMENT
# ==========================================
@router.get("/contact-messages", response_model=ApiResponse)
def get_contact_messages(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    messages = db.query(ContactMessage).all()
    return ApiResponse(success=True, message="Contact messages fetched", data=orm_list_to_dicts(messages))

@router.delete("/contact-messages/{id}", response_model=ApiResponse)
def delete_contact_message(id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    message = db.query(ContactMessage).filter(ContactMessage.id == id).first()
    if not message: return ApiResponse(success=False, message="Message not found")
    db.delete(message)
    db.commit()
    return ApiResponse(success=True, message="Message deleted successfully")