from pydantic import BaseModel
from typing import Optional

class CustomerProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None

class ChangePassword(BaseModel):
    old_password: str
    new_password: str