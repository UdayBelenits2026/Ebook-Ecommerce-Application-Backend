from pydantic import BaseModel, Field
class CartItemAdd(BaseModel):
    book_id: int
    quantity: int = Field(default=1, ge=1)

# .venv\scripts\activate
# python -m uvicorn main:app --reload