from pydantic import BaseModel


class CreatePaymentRequest(BaseModel):
    address_id: int


class CreatePaymentResponse(BaseModel):
    success: bool
    payment_session_id: str
    order_id: str
    amount: float


class VerifyPaymentResponse(BaseModel):
    success: bool
    payment_status: str
    message: str