from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.domain import Notification, User
from app.schemas.notification import NotificationCreate, NotificationResponse
from app.schemas.response import ApiResponse
from app.dependencies.auth import get_current_user
from app.utils.dependencies import require_admin

router = APIRouter(
    prefix="/admin/notifications",
    tags=["Admin Notifications"]
)
@router.post("", response_model=ApiResponse)
def create_notification(
    data: NotificationCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):

    users = (
        db.query(User)
        .filter(User.role == "customer")
        .all()
    )

    for user in users:

        notification = Notification(
            user_id=user.id,
            title=data.title,
            message=data.message,
            type=data.type
        )

        db.add(notification)

    db.commit()

    return ApiResponse(
        success=True,
        message="Notification sent to all users"
    )
@router.get("", response_model=ApiResponse)
def get_notifications(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):

    notifications = (
        db.query(Notification)
        .order_by(Notification.created_at.desc())
        .all()
    )

    # Convert SQLAlchemy models to Pydantic models for serialization
    pdata = [NotificationResponse.model_validate(n) for n in notifications]

    return ApiResponse(
        success=True,
        message="Notifications fetched successfully",
        data=pdata
    )
@router.delete("/{id}", response_model=ApiResponse)
def delete_notification(
    id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):

    notifications = (
        db.query(Notification)
        .filter(Notification.id == id)
        .all()
    )

    if not notifications:
        return ApiResponse(
            success=False,
            message="Notification not found"
        )

    for notification in notifications:
        db.delete(notification)

    db.commit()

    return ApiResponse(
        success=True,
        message="Notification deleted successfully"
    )
@router.get("/user", response_model=ApiResponse)
def get_my_notifications(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):

    notifications = (
        db.query(Notification)
        .filter(Notification.user_id == user.id)
        .order_by(Notification.created_at.desc())
        .all()
    )

    pdata = [NotificationResponse.model_validate(n) for n in notifications]

    return ApiResponse(
        success=True,
        message="Notifications fetched successfully",
        data=pdata
    )
@router.patch("/user/{notification_id}/read", response_model=ApiResponse)
def mark_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    notification = (
        db.query(Notification)
        .filter(
            Notification.id == notification_id,
            Notification.user_id == user.id
        )
        .first()
    )

    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )

    notification.is_read = True

    db.commit()
    db.refresh(notification)

    pdata = NotificationResponse.model_validate(notification)

    return ApiResponse(
        success=True,
        message="Notification marked as read",
        data=pdata
    )
@router.delete("/user/{notification_id}", response_model=ApiResponse)
def delete_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    notification = (
        db.query(Notification)
        .filter(
            Notification.id == notification_id,
            Notification.user_id == user.id
        )
        .first()
    )

    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )

    db.delete(notification)
    db.commit()

    return ApiResponse(
        success=True,
        message="Notification deleted successfully"
    )