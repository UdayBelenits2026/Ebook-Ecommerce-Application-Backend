from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
import random

from app.database.session import get_db
from app.models.domain import User, OTPVerification
from app.schemas.auth import (
    UserCreate,
    UserLogin,
    OTPVerify,
    OTPRequest,
    ResetPasswordRequest,
)
from app.schemas.response import ApiResponse
from app.utils.security import (
    get_password_hash,
    verify_password,
    create_access_token,
)
from app.utils.email import send_otp_email


router = APIRouter(
    prefix="/auth",
    tags=["Auth"]
)


# ============================================================
# REGISTER
# ============================================================

@router.post(
    "/register",
    response_model=ApiResponse
)
def register(
    user: UserCreate,
    db: Session = Depends(get_db)
):
    # Check whether email already exists
    existing_user = (
        db.query(User)
        .filter(User.email == user.email)
        .first()
    )

    if existing_user:
        return ApiResponse(
            success=False,
            message="Email already exists"
        )

    # Create user
    db_user = User(
        **user.model_dump(exclude={"password"}),
        password=get_password_hash(user.password)
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return ApiResponse(
        success=True,
        message=(
            "Registration successful. "
            "Please request an OTP to verify your email."
        )
    )


# ============================================================
# SEND OTP
# ============================================================

@router.post(
    "/send-otp",
    response_model=ApiResponse
)
def send_otp(
    data: OTPRequest,
    db: Session = Depends(get_db)
):
    # Find user
    user = (
        db.query(User)
        .filter(User.email == data.email)
        .first()
    )

    if not user:
        return ApiResponse(
            success=False,
            message="User not found"
        )

    # Check whether email is already verified
    if user.is_verified:
        return ApiResponse(
            success=False,
            message="Email is already verified"
        )

    # Generate 6-digit OTP
    otp = str(
        random.randint(100000, 999999)
    )

    # OTP expires after 10 minutes
    expiry = (
        datetime.now(timezone.utc)
        + timedelta(minutes=10)
    )

    # Check whether OTP record already exists
    otp_record = (
        db.query(OTPVerification)
        .filter_by(email=data.email)
        .first()
    )

    if otp_record:

        otp_record.otp = otp
        otp_record.expiry_time = expiry

    else:

        otp_record = OTPVerification(
            email=data.email,
            otp=otp,
            expiry_time=expiry
        )

        db.add(otp_record)

    db.commit()

    # ========================================================
    # SEND OTP USING RESEND
    # ========================================================

    email_sent = send_otp_email(
        data.email,
        otp
    )

    # IMPORTANT:
    # Do not return success if email sending failed.
    if not email_sent:

        return ApiResponse(
            success=False,
            message=(
                "Unable to send OTP email. "
                "Please try again."
            )
        )

    return ApiResponse(
        success=True,
        message="OTP sent successfully."
    )


# ============================================================
# RESEND OTP
# ============================================================

@router.post(
    "/resend-otp",
    response_model=ApiResponse
)
def resend_otp(
    data: OTPRequest,
    db: Session = Depends(get_db)
):
    # Reuse the same OTP logic
    return send_otp(
        data,
        db
    )


# ============================================================
# VERIFY EMAIL
# ============================================================

@router.post(
    "/verify-email",
    response_model=ApiResponse
)
def verify_email(
    data: OTPVerify,
    db: Session = Depends(get_db)
):
    record = (
        db.query(OTPVerification)
        .filter_by(
            email=data.email,
            otp=data.otp
        )
        .first()
    )

    if not record:
        return ApiResponse(
            success=False,
            message="Invalid or expired OTP"
        )

    # Make expiry timezone-aware
    expiry_time = record.expiry_time

    if expiry_time.tzinfo is None:
        expiry_time = expiry_time.replace(
            tzinfo=timezone.utc
        )

    # Check expiration
    if expiry_time < datetime.now(timezone.utc):

        db.delete(record)
        db.commit()

        return ApiResponse(
            success=False,
            message="Invalid or expired OTP"
        )

    # Find user
    user = (
        db.query(User)
        .filter_by(email=data.email)
        .first()
    )

    if not user:
        return ApiResponse(
            success=False,
            message="User not found"
        )

    # Verify email
    user.is_verified = True

    # Remove OTP after successful verification
    db.delete(record)

    db.commit()

    return ApiResponse(
        success=True,
        message="Email verified."
    )


# ============================================================
# LOGIN
# ============================================================

@router.post(
    "/login",
    response_model=ApiResponse
)
def login(
    data: UserLogin,
    db: Session = Depends(get_db)
):
    user = (
        db.query(User)
        .filter(User.email == data.email)
        .first()
    )

    # Validate user/password
    if not user or not verify_password(
        data.password,
        user.password
    ):
        return ApiResponse(
            success=False,
            message="Invalid credentials"
        )

    # Require email verification
    if not user.is_verified:
        return ApiResponse(
            success=False,
            message="Verify email first"
        )

    # JWT payload
    token_data = {
        "sub": user.email,
        "user_id": user.id,
        "role": user.role
    }

    token = create_access_token(
        token_data
    )

    return ApiResponse(
        success=True,
        message="Login Successful",
        data={
            "access_token": token,
            "token_type": "bearer",
            "role": user.role,
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email
        }
    )


# ============================================================
# LOGOUT
# ============================================================

@router.post(
    "/logout",
    response_model=ApiResponse
)
def logout():

    # JWT is removed by Angular.
    # Backend simply acknowledges logout.

    return ApiResponse(
        success=True,
        message="Logout successful"
    )


# ============================================================
# FORGOT PASSWORD
# ============================================================

@router.post(
    "/forgot-password",
    response_model=ApiResponse
)
def forgot_password(
    data: OTPRequest,
    db: Session = Depends(get_db)
):
    user = (
        db.query(User)
        .filter(User.email == data.email)
        .first()
    )

    # Don't reveal whether email exists
    if not user:
        return ApiResponse(
            success=True,
            message=(
                "If that email is registered, "
                "an OTP has been sent."
            )
        )

    # Generate OTP
    otp = str(
        random.randint(100000, 999999)
    )

    expiry = (
        datetime.now(timezone.utc)
        + timedelta(minutes=10)
    )

    # Update existing OTP or create new one
    otp_record = (
        db.query(OTPVerification)
        .filter_by(email=data.email)
        .first()
    )

    if otp_record:

        otp_record.otp = otp
        otp_record.expiry_time = expiry

    else:

        otp_record = OTPVerification(
            email=data.email,
            otp=otp,
            expiry_time=expiry
        )

        db.add(otp_record)

    db.commit()

    # Send OTP using Resend
    email_sent = send_otp_email(
        data.email,
        otp
    )

    if not email_sent:

        return ApiResponse(
            success=False,
            message="Unable to send OTP email. Please try again."
        )

    return ApiResponse(
        success=True,
        message=(
            "If that email is registered, "
            "an OTP has been sent."
        )
    )


# ============================================================
# RESET PASSWORD
# ============================================================

@router.post(
    "/reset-password",
    response_model=ApiResponse
)
def reset_password(
    data: ResetPasswordRequest,
    db: Session = Depends(get_db)
):
    record = (
        db.query(OTPVerification)
        .filter_by(
            email=data.email,
            otp=data.otp
        )
        .first()
    )

    if not record:
        return ApiResponse(
            success=False,
            message="Invalid or expired OTP"
        )

    # Make expiry timezone-aware
    expiry_time = record.expiry_time

    if expiry_time.tzinfo is None:
        expiry_time = expiry_time.replace(
            tzinfo=timezone.utc
        )

    # Check expiry
    if expiry_time < datetime.now(timezone.utc):

        db.delete(record)
        db.commit()

        return ApiResponse(
            success=False,
            message="Invalid or expired OTP"
        )

    # Find user
    user = (
        db.query(User)
        .filter_by(email=data.email)
        .first()
    )

    if not user:
        return ApiResponse(
            success=False,
            message="User not found"
        )

    # Update password
    user.password = get_password_hash(
        data.new_password
    )

    # Delete OTP
    db.delete(record)

    db.commit()

    return ApiResponse(
        success=True,
        message=(
            "Password has been reset successfully. "
            "You can now login."
        )
    )