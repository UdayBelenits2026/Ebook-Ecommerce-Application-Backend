from fastapi import APIRouter, Depends, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import shutil, os
from app.database.session import get_db
from app.models.domain import Category
from app.schemas.category import CategoryCreate
from app.schemas.response import ApiResponse
from app.dependencies.auth import get_admin_user
from app.utils.serialization import orm_list_to_dicts

router = APIRouter(prefix="/categories", tags=["Categories"])
os.makedirs("uploads/categories", exist_ok=True)

@router.get("", response_model=ApiResponse)
def get_categories(db: Session = Depends(get_db)):
    categories = db.query(Category).all()
    return ApiResponse(success=True, message="Success", data=orm_list_to_dicts(categories))

@router.post("", response_model=ApiResponse, dependencies=[Depends(get_admin_user)])
def create_category(
    name: str = Form(...),
    description: str = Form(...),
    image: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    if db.query(Category).filter(Category.name == name).first():
        return ApiResponse(success=False, message="Category already exists")
    db_category = Category(name=name, description=description)
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    if image and image.filename:
        img_ext = os.path.splitext(image.filename)[1]
        img_path = f"uploads/categories/{db_category.id}{img_ext}"
        with open(img_path, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)
        db.query(Category).filter(Category.id == db_category.id).update({"image": img_path})
        db.commit()
    return ApiResponse(success=True, message="Category created")

@router.delete("/{id}", response_model=ApiResponse, dependencies=[Depends(get_admin_user)])
def delete_category(id: int, db: Session = Depends(get_db)):
    db.query(Category).filter(Category.id == id).delete()
    db.commit()
    return ApiResponse(success=True, message="Category deleted")