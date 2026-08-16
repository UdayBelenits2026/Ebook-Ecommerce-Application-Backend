from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.domain import ContactMessage
from app.schemas.contact import ContactCreate
from app.schemas.response import ApiResponse

router = APIRouter(prefix="/contact", tags=["Contact"])

@router.post("", response_model=ApiResponse)
def submit_contact(msg: ContactCreate, db: Session = Depends(get_db)):
    db.add(ContactMessage(**msg.model_dump()))
    db.commit()
    return ApiResponse(success=True, message="Message sent successfully")