from pydantic import BaseModel, Field
class ReviewCreate(BaseModel):
    book_id: int
    rating: float = Field(..., ge=1, le=5)
    review: str