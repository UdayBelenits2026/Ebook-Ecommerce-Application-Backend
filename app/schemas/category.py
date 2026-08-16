from pydantic import BaseModel
from typing import Optional

class CategoryBase(BaseModel):
    name: str
    description: str
    image: Optional[str] = None

class CategoryCreate(CategoryBase): pass