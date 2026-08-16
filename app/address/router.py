from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies.auth import get_current_user

from app.models.domain import Address, User
from app.schemas.address import AddressCreate, AddressResponse
from app.schemas.response import ApiResponse

router = APIRouter(
    prefix="/addresses",
    tags=["Addresses"]
)


# ----------------------------------------------------
# ADD NEW ADDRESS
# ----------------------------------------------------
@router.post("", response_model=ApiResponse)
def create_address(
    data: AddressCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):

    if data.is_default:
        db.query(Address).filter(
            Address.user_id == user.id
        ).update({"is_default": False})

    address = Address(
        user_id=user.id,
        full_name=data.full_name,
        mobile=data.mobile,
        house_no=data.house_no,
        street=data.street,
        area=data.area,
        village_city=data.village_city,
        district=data.district,
        state=data.state,
        pincode=data.pincode,
        landmark=data.landmark,
        is_default=data.is_default
    )

    db.add(address)
    db.commit()
    db.refresh(address)

    return ApiResponse(
        success=True,
        message="Address added successfully",
        data=AddressResponse.model_validate(address).model_dump()
    )


# ----------------------------------------------------
# GET ALL ADDRESSES
# ----------------------------------------------------
@router.get("", response_model=ApiResponse)
def get_addresses(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):

    addresses = (
        db.query(Address)
        .filter(Address.user_id == user.id)
        .order_by(Address.is_default.desc(), Address.id.desc())
        .all()
    )

    return ApiResponse(
        success=True,
        message="Addresses fetched successfully",
        data=[
            AddressResponse.model_validate(address).model_dump()
            for address in addresses
        ]
    )


# ----------------------------------------------------
# GET SINGLE ADDRESS
# ----------------------------------------------------
@router.get("/{address_id}", response_model=ApiResponse)
def get_address(
    address_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):

    address = (
        db.query(Address)
        .filter(
            Address.id == address_id,
            Address.user_id == user.id
        )
        .first()
    )

    if not address:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Address not found"
        )

    return ApiResponse(
        success=True,
        message="Success",
        data=AddressResponse.model_validate(address).model_dump()
    )


# ----------------------------------------------------
# UPDATE ADDRESS
# ----------------------------------------------------
@router.put("/{address_id}", response_model=ApiResponse)
def update_address(
    address_id: int,
    data: AddressCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):

    address = (
        db.query(Address)
        .filter(
            Address.id == address_id,
            Address.user_id == user.id
        )
        .first()
    )

    if not address:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Address not found"
        )

    if data.is_default:
        db.query(Address).filter(
            Address.user_id == user.id
        ).update({"is_default": False})

    address.full_name = data.full_name
    address.mobile = data.mobile
    address.house_no = data.house_no
    address.street = data.street
    address.area = data.area
    address.village_city = data.village_city
    address.district = data.district
    address.state = data.state
    address.pincode = data.pincode
    address.landmark = data.landmark
    address.is_default = data.is_default

    db.commit()
    db.refresh(address)

    return ApiResponse(
        success=True,
        message="Address updated successfully",
        data=AddressResponse.model_validate(address).model_dump()
    )


# ----------------------------------------------------
# DELETE ADDRESS
# ----------------------------------------------------
@router.delete("/{address_id}", response_model=ApiResponse)
def delete_address(
    address_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):

    address = (
        db.query(Address)
        .filter(
            Address.id == address_id,
            Address.user_id == user.id
        )
        .first()
    )

    if not address:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Address not found"
        )

    db.delete(address)
    db.commit()

    return ApiResponse(
        success=True,
        message="Address deleted successfully",
        data=None
    )