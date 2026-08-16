from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database.session import get_db
from app.models.domain import Wishlist, User, Book, Cart, CartItem
from app.schemas.response import ApiResponse
from app.dependencies.auth import get_current_user

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("wishlist")

router = APIRouter(prefix="/wishlist", tags=["Wishlist"])


def get_wishlist_items_with_details(db: Session, user_id: int) -> list:
    """Get wishlist items enriched with book details, avg rating, and in_cart status using a single SQL query."""
    sql = text("""
        SELECT
            w.id                AS id,
            w.book_id           AS book_id,
            b.title             AS title,
            b.author            AS author,
            b.price             AS price,
            b.image             AS image,
            b.stock             AS stock,
            COALESCE(AVG(r.rating), 0) AS rating,
            c.name              AS category_name,
            CASE WHEN ci.id IS NOT NULL THEN 1 ELSE 0 END AS in_cart
        FROM wishlists w
        JOIN books b              ON b.id = w.book_id
        LEFT JOIN categories c     ON c.id = b.category_id
        LEFT JOIN reviews r        ON r.book_id = b.id
        LEFT JOIN carts ct         ON ct.user_id = w.user_id
        LEFT JOIN cart_items ci    ON ci.cart_id = ct.id AND ci.book_id = w.book_id
        WHERE w.user_id = :user_id
        GROUP BY w.id, w.book_id, b.title, b.author, b.price, b.image, b.stock, c.name, ci.id
        ORDER BY w.id DESC
    """)
    rows = db.execute(sql, {"user_id": user_id}).mappings().all()
    return [dict(row) for row in rows]


@router.get("", response_model=ApiResponse)
def get_wishlist(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """
    Retrieve all wishlist items for the currently authenticated user.
    Returns enriched data including book stock, average rating, and in_cart status.
    """
    logger.info(f"Authenticated user ID: {user.id}, Email: {user.email}")

    raw_items = get_wishlist_items_with_details(db, user.id)

    items = []
    for item in raw_items:
        items.append({
            "id": item["id"],
            "book_id": item["book_id"],
            "title": item["title"],
            "author": item["author"],
            "price": item["price"],
            "image": item["image"],
            "category_name": item["category_name"],
            "quantity": 1,
            "stock": item["stock"],
            "rating": float(item["rating"]),
            "in_cart": bool(item["in_cart"]),
        })

    logger.info(f"Returning {len(items)} wishlist items for user {user.id}")

    return ApiResponse(
        success=True,
        message="Wishlist retrieved successfully",
        data={
            "items": items,
            "total": len(items),
            "wishlist_count": len(items),
        },
    )


@router.post("/add/{book_id}", response_model=ApiResponse)
def add_wishlist(book_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Add a book to wishlist. Validates book exists and prevents duplicates."""
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")

    existing = db.query(Wishlist).filter_by(user_id=user.id, book_id=book_id).first()
    if not existing:
        db.add(Wishlist(user_id=user.id, book_id=book_id))
        db.commit()
        logger.info(f"Added book {book_id} to wishlist for user {user.id}")
    else:
        logger.info(f"Book {book_id} already in wishlist for user {user.id}")

    return ApiResponse(success=True, message="Added to wishlist")


@router.post("/move-to-cart/{book_id}", response_model=ApiResponse)
def move_to_cart(book_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Move a wishlist item to the cart. Removes from wishlist after moving."""
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")

    wishlist_item = db.query(Wishlist).filter_by(user_id=user.id, book_id=book_id).first()
    if not wishlist_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found in wishlist")

    cart = db.query(Cart).filter_by(user_id=user.id).first()
    if not cart:
        cart = Cart(user_id=user.id)
        db.add(cart)
        db.commit()
        db.refresh(cart)

    cart_item = db.query(CartItem).filter_by(cart_id=cart.id, book_id=book_id).first()
    if cart_item:
        if cart_item.quantity >= book.stock:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient stock. Available: {book.stock}",
            )
        cart_item.quantity += 1
    else:
        if book.stock < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Book is out of stock",
            )
        db.add(CartItem(cart_id=cart.id, book_id=book_id, quantity=1))

    db.delete(wishlist_item)
    db.commit()

    logger.info(f"Moved book {book_id} from wishlist to cart for user {user.id}")
    return ApiResponse(success=True, message="Moved to cart successfully")


@router.delete("/remove/{book_id}", response_model=ApiResponse)
def remove_wishlist(book_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Remove a book from the authenticated user's wishlist."""
    item = db.query(Wishlist).filter_by(user_id=user.id, book_id=book_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wishlist item not found")

    db.delete(item)
    db.commit()

    logger.info(f"Removed book {book_id} from wishlist for user {user.id}")
    return ApiResponse(success=True, message="Removed from wishlist")


@router.delete("/clear", response_model=ApiResponse)
def clear_wishlist(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Delete every wishlist item belonging to the authenticated user."""
    deleted = db.query(Wishlist).filter_by(user_id=user.id).delete()
    db.commit()
    logger.info(f"Cleared {deleted} wishlist items for user {user.id}")
    return ApiResponse(success=True, message="Wishlist cleared")
