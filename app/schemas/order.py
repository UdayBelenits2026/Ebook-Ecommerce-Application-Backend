from pydantic import BaseModel
class OrderPlace(BaseModel):
    payment_method: str
    address_id: int