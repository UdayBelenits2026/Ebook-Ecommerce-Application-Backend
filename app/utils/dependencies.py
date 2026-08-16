from fastapi import Depends, HTTPException, status
from app.dependencies.auth import get_current_user, get_admin_user, oauth2_scheme
from app.models.domain import User


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions. Admin access required."
        )
    return current_user


def require_customer(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "customer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions. Customer access required."
        )
    return current_user