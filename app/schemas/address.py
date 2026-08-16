from pydantic import BaseModel, ConfigDict
from typing import Optional


class AddressCreate(BaseModel):
    full_name: str
    mobile: str
    house_no: str
    street: str
    area: str
    village_city: str
    district: str
    state: str
    pincode: str
    landmark: Optional[str] = None
    is_default: bool = False


class AddressResponse(BaseModel):
    id: int
    full_name: str
    mobile: str
    house_no: str
    street: str
    area: str
    village_city: str
    district: str
    state: str
    pincode: str
    landmark: Optional[str] = None
    is_default: bool

    model_config = ConfigDict(from_attributes=True)