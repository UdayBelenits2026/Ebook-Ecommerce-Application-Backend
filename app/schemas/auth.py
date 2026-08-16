from pydantic import BaseModel, EmailStr, Field

class UserCreate(BaseModel):
    full_name: str
    email: EmailStr
    phone: str = Field(..., min_length=10, max_length=15)
    password: str = Field(..., min_length=8)

class UserLogin(BaseModel):
    email: EmailStr
    password: str
class ResendOTP(BaseModel):
    email: EmailStr
class OTPRequest(BaseModel):
    email: EmailStr
class OTPVerify(BaseModel):
    email: EmailStr
    otp: str = Field(..., min_length=6, max_length=6)
class ResetPasswordRequest(BaseModel):
    email: EmailStr
    otp: str = Field(..., min_length=6, max_length=6)
    new_password: str = Field(..., min_length=8)