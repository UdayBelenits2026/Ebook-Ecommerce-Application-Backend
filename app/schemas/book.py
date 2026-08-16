from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime

class BookBase(BaseModel):
    title: str
    author: str
    category_id: int
    publisher: str
    isbn: str = Field(..., max_length=20)
    language: str
    pages: int
    price: float = Field(..., gt=0)
    stock: int = Field(..., ge=0)
    description: str

class BookCreate(BookBase): pass
class BookUpdate(BookBase): pass

class BookOut(BaseModel):
    id: int
    title: str
    author: str
    category_id: Optional[int] = None
    publisher: Optional[str] = None
    isbn: Optional[str] = None
    language: Optional[str] = None
    pages: Optional[int] = None
    price: float
    stock: int
    description: Optional[str] = None
    image: Optional[str] = None
    rating: Optional[float] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # allow model validation from ORM objects (SQLAlchemy instances)
    model_config = ConfigDict(from_attributes=True)