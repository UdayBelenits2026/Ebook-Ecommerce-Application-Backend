from fastapi import APIRouter, Depends, UploadFile, File
import os
import shutil
from datetime import datetime
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.domain import User
from app.schemas.response import ApiResponse
from app.schemas.user import CustomerProfileUpdate, ChangePassword
from app.utils.security import verify_password, get_password_hash
from app.utils.dependencies import require_customer
from app.dependencies.auth import get_current_user

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=ApiResponse)
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """Get the currently authenticated user's profile."""
    return ApiResponse(
        success=True,
        message="Profile fetched successfully",
        data={
            "id": current_user.id,
            "full_name": current_user.full_name,
            "email": current_user.email,
            "phone": current_user.phone or "",
            "profile_image": current_user.profile_image or "",
            "role": current_user.role,
            "is_verified": current_user.is_verified,
            "joined_date": current_user.created_at.isoformat() if current_user.created_at else None,
        }
    )


@router.put("/me", response_model=ApiResponse)
def update_current_user_profile(
    data: CustomerProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update the currently authenticated user's profile."""
    if data.full_name:
        current_user.full_name = data.full_name
    if data.phone is not None:
        current_user.phone = data.phone

    db.commit()

    return ApiResponse(
        success=True,
        message="Profile updated successfully",
      data={
    "id": current_user.id,
    "full_name": current_user.full_name,
    "email": current_user.email,
    "phone": current_user.phone or "",
    "profile_image": current_user.profile_image or "",
    "role": current_user.role,
    "is_verified": current_user.is_verified,
    "joined_date": current_user.created_at.isoformat() if current_user.created_at else None,
}
    )


@router.post("/me/avatar", response_model=ApiResponse)
def upload_current_user_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload avatar image for the currently authenticated user."""
    upload_dir = "static/uploads/users"
    os.makedirs(upload_dir, exist_ok=True)

    file_extension = file.filename.split(".")[-1] if "." in file.filename else "jpg"
    file_name = f"user_{current_user.id}_{int(datetime.now().timestamp())}.{file_extension}"
    file_path = f"{upload_dir}/{file_name}"

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    current_user.profile_image = f"/{file_path}"
    db.commit()

    return ApiResponse(
        success=True,
        message="Avatar uploaded successfully",
     data={
    "id": current_user.id,
    "full_name": current_user.full_name,
    "email": current_user.email,
    "phone": current_user.phone or "",
    "profile_image": current_user.profile_image or "",
    "role": current_user.role,
    "is_verified": current_user.is_verified,
    "joined_date": current_user.created_at.isoformat() if current_user.created_at else None,
}
    )


# Keep existing customer routes for backward compatibility

customer_router = APIRouter(prefix="/customer", tags=["Customer Profile"])


@customer_router.get("/me", response_model=ApiResponse)
def get_customer_me(current_user: User = Depends(require_customer)):
    """Alias for customer profile - returns basic profile info."""
    return ApiResponse(
        success=True,
        message="Profile fetched",
        data={
            "id": current_user.id,
            "full_name": current_user.full_name,
            "email": current_user.email,
            "phone": current_user.phone,
            "profile_image": current_user.profile_image
        }
    )


@customer_router.get("/profile", response_model=ApiResponse)
def get_customer_profile(current_user: User = Depends(require_customer)):
    return ApiResponse(
        success=True,
        message="Profile fetched",
        data={
            "id": current_user.id,
            "full_name": current_user.full_name,
            "email": current_user.email,
            "phone": current_user.phone,
            "profile_image": current_user.profile_image
        }
    )


@customer_router.put("/profile", response_model=ApiResponse)
def update_customer_profile(
    data: CustomerProfileUpdate,
    current_user: User = Depends(require_customer),
    db: Session = Depends(get_db)
):
    if data.full_name:
        current_user.full_name = data.full_name
    if data.phone:
        current_user.phone = data.phone

    db.commit()

    return ApiResponse(
        success=True,
        message="Profile updated successfully",
        data={
            "id": current_user.id,
            "full_name": current_user.full_name,
            "email": current_user.email,
            "phone": current_user.phone,
            "profile_image": current_user.profile_image
        }
    )


@customer_router.post("/profile/upload-image", response_model=ApiResponse)
def upload_customer_image(
    file: UploadFile = File(...),
    current_user: User = Depends(require_customer),
    db: Session = Depends(get_db)
):
    upload_dir = "static/uploads/users"
    os.makedirs(upload_dir, exist_ok=True)

    file_extension = file.filename.split(".")[-1]
    file_name = f"customer_{current_user.id}_{int(datetime.now().timestamp())}.{file_extension}"
    file_path = f"{upload_dir}/{file_name}"

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    current_user.profile_image = f"/{file_path}"
    db.commit()

    return ApiResponse(
        success=True,
        message="Profile image uploaded successfully",
        data={
            "id": current_user.id,
            "full_name": current_user.full_name,
            "email": current_user.email,
            "phone": current_user.phone,
            "profile_image": current_user.profile_image
        }
    )


@customer_router.put("/change-password", response_model=ApiResponse)
def change_customer_password(
    data: ChangePassword,
    current_user: User = Depends(require_customer),
    db: Session = Depends(get_db)
):
    if not verify_password(data.old_password, current_user.password):
        return ApiResponse(success=False, message="Incorrect old password")

    current_user.password = get_password_hash(data.new_password)
    db.commit()

    return ApiResponse(success=True, message="Password updated successfully")
