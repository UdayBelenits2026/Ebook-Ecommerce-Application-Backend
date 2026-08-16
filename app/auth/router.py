from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
import random

from app.database.session import get_db
from app.models.domain import User, OTPVerification
from app.schemas.auth import UserCreate, UserLogin, OTPVerify, OTPRequest, ResetPasswordRequest
from app.schemas.response import ApiResponse
from app.utils.security import get_password_hash, verify_password, create_access_token
from app.utils.email import send_otp_email

router = APIRouter(prefix="/auth", tags=["Auth"])

@router.post("/register", response_model=ApiResponse)
def register(user: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == user.email).first():
        return ApiResponse(success=False, message="Email already exists")
        
    db_user = User(**user.model_dump(exclude={"password"}), password=get_password_hash(user.password))
    db.add(db_user)
    db.commit()
    
    return ApiResponse(success=True, message="Registration successful. Please request an OTP to verify your email.")

@router.post("/send-otp", response_model=ApiResponse)
def send_otp(data: OTPRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user:
        return ApiResponse(success=False, message="User not found")
    if user.is_verified:
        return ApiResponse(success=False, message="Email is already verified")
        
    otp = str(random.randint(100000, 999999))
    expiry = datetime.now(timezone.utc) + timedelta(minutes=10)
    
    # Check if an OTP record already exists for this email
    otp_record = db.query(OTPVerification).filter_by(email=data.email).first()
    if otp_record:
        otp_record.otp = otp
        otp_record.expiry_time = expiry
    else:
        db.add(OTPVerification(email=data.email, otp=otp, expiry_time=expiry))
        
    db.commit()
    send_otp_email(data.email, otp)
    
    return ApiResponse(success=True, message="OTP sent successfully.")

@router.post("/resend-otp", response_model=ApiResponse)
def resend_otp(data: OTPRequest, db: Session = Depends(get_db)):
    # The underlying logic for resending is identical to sending
    return send_otp(data, db)

@router.post("/verify-email", response_model=ApiResponse)
def verify_email(data: OTPVerify, db: Session = Depends(get_db)):
    record = db.query(OTPVerification).filter_by(email=data.email, otp=data.otp).first()
    if not record or record.expiry_time.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        return ApiResponse(success=False, message="Invalid or expired OTP")
        
    user = db.query(User).filter_by(email=data.email).first()
    if user:
        user.is_verified = True
        
    db.delete(record)
    db.commit()
    return ApiResponse(success=True, message="Email verified.")

@router.post("/login", response_model=ApiResponse)
def login(data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    
    if not user or not verify_password(data.password, user.password):
        return ApiResponse(success=False, message="Invalid credentials")
        
    if not user.is_verified:
        return ApiResponse(success=False, message="Verify email first")
        
    # Build the enhanced JWT payload
    token_data = {
        "sub": user.email,
        "user_id": user.id,
        "role": user.role
    }
    
    token = create_access_token(token_data)
    
    # Return the exact payload Angular requires
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

@router.post("/logout", response_model=ApiResponse)
def logout():
    # The frontend removes the JWT. Backend simply acknowledges.
    return ApiResponse(success=True, message="Logout successful")

@router.post("/forgot-password", response_model=ApiResponse)
def forgot_password(data: OTPRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user:
        # For security, we still return a generic success message
        return ApiResponse(success=True, message="If that email is registered, an OTP has been sent.")
        
    otp = str(random.randint(100000, 999999))
    expiry = datetime.now(timezone.utc) + timedelta(minutes=10)
    
    # Update existing or create new OTP record
    otp_record = db.query(OTPVerification).filter_by(email=data.email).first()
    if otp_record:
        otp_record.otp = otp
        otp_record.expiry_time = expiry
    else:
        db.add(OTPVerification(email=data.email, otp=otp, expiry_time=expiry))
        
    db.commit()
    send_otp_email(data.email, otp)
    
    return ApiResponse(success=True, message="If that email is registered, an OTP has been sent.")

@router.post("/reset-password", response_model=ApiResponse)
def reset_password(data: ResetPasswordRequest, db: Session = Depends(get_db)):
    record = db.query(OTPVerification).filter_by(email=data.email, otp=data.otp).first()
    
    if not record or record.expiry_time.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        return ApiResponse(success=False, message="Invalid or expired OTP")
        
    user = db.query(User).filter_by(email=data.email).first()
    if not user:
        return ApiResponse(success=False, message="User not found")
        
    # Hash the new password and update the user
    user.password = get_password_hash(data.new_password)
    
    # Delete the OTP record so it can't be reused
    db.delete(record)
    db.commit()
    
    return ApiResponse(success=True, message="Password has been reset successfully. You can now login.")