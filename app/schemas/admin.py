from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import date

class StatusUpdate(BaseModel):
    status: str

class OrderStatusUpdate(BaseModel):
    status: str  # Pending, Processing, Shipped, Delivered, Cancelled

class AdminLogin(BaseModel):
    email: EmailStr
    password: str

class ChangePassword(BaseModel):
    old_password: str
    new_password: str
class AdminProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
class TrackingUpdate(BaseModel):
    tracking_number: Optional[str] = None
    courier_name: Optional[str] = None
    estimated_delivery: Optional[date] = None