from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from app.database.session import get_db
from app.models.domain import Cart, CartItem, User, Book, Wishlist
from app.schemas.cart import CartItemAdd
from app.schemas.response import ApiResponse
from app.dependencies.auth import get_current_user

router = APIRouter(prefix="/cart", tags=["Cart"])


class CartUpdateRequest(BaseModel):
    book_id: int
    quantity: int


def get_or_create_cart(user_id: int, db: Session):
    cart = db.query(Cart).filter_by(user_id=user_id).first()
    if not cart:
        cart = Cart(user_id=user_id)
        db.add(cart)
        db.commit()
        db.refresh(cart)
    return cart


SHIPPING_COST = 50.0
FREE_SHIPPING_THRESHOLD = 500.0


def get_cart_details(db: Session, user_id: int) -> dict:
    """
    Fetch cart items with book details, subtotals, stock, rating, in_wishlist.
    Uses a single SQL query with JOINs.
    """
    sql = text("""
        SELECT
            ci.id               AS id,
            ci.cart_id          AS cart_id,
            ci.book_id          AS book_id,
            ci.quantity         AS quantity,
            b.title             AS title,
            b.author            AS author,
            b.price             AS price,
            b.image             AS image,
            b.stock             AS stock,
            c.name              AS category_name,
            COALESCE(AVG(r.rating), 0) AS rating,
            CASE WHEN w.id IS NOT NULL THEN 1 ELSE 0 END AS in_wishlist
        FROM cart_items ci
        JOIN carts ct            ON ct.id = ci.cart_id
        JOIN books b             ON b.id = ci.book_id
        LEFT JOIN categories c   ON c.id = b.category_id
        LEFT JOIN reviews r      ON r.book_id = b.id
        LEFT JOIN wishlists w    ON w.book_id = ci.book_id AND w.user_id = :uid
        WHERE ct.user_id = :uid
        GROUP BY ci.id, ci.cart_id, ci.book_id, ci.quantity,
                 b.title, b.author, b.price, b.image, b.stock, c.name, w.id
        ORDER BY ci.id
    """)
    rows = db.execute(sql, {"uid": user_id}).mappings().all()

    items = []
    subtotal = 0.0
    for row in rows:
        item_subtotal = float(row["price"]) * row["quantity"]
        subtotal += item_subtotal
        items.append({
            "id": row["id"],
            "cart_id": row["cart_id"],
            "book_id": row["book_id"],
            "quantity": row["quantity"],
            "title": row["title"],
            "author": row["author"],
            "price": float(row["price"]),
            "image": row["image"],
            "stock": row["stock"],
            "category_name": row["category_name"],
            "rating": float(row["rating"]),
            "subtotal": item_subtotal,
            "in_wishlist": bool(row["in_wishlist"]),
        })

    shipping = 0.0 if subtotal >= FREE_SHIPPING_THRESHOLD else SHIPPING_COST
    grand_total = subtotal + shipping

    return {
        "items": items,
        "subtotal": subtotal,
        "shipping": shipping,
        "grand_total": grand_total,
        "cart_count": len(items),
    }


@router.get("", response_model=ApiResponse)
def view_cart(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Get cart with items, subtotals, shipping, and grand total."""
    cart_data = get_cart_details(db, user.id)
    return ApiResponse(success=True, message="Cart retrieved successfully", data=cart_data)


@router.post("/add", response_model=ApiResponse)
def add_to_cart(item: CartItemAdd, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """
    Add a book to the cart. If it already exists, increment quantity by the given amount.
    """
    book = db.query(Book).filter(Book.id == item.book_id).first()
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")

    cart = get_or_create_cart(user.id, db)
    existing = db.query(CartItem).filter_by(cart_id=cart.id, book_id=item.book_id).first()

    if existing:
        new_qty = existing.quantity + item.quantity
        if book.stock < new_qty:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient stock. Available: {book.stock}, already in cart: {existing.quantity}"
            )
        existing.quantity = new_qty
    else:
        if book.stock < item.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient stock. Available: {book.stock}, requested: {item.quantity}"
            )
        db.add(CartItem(cart_id=cart.id, book_id=item.book_id, quantity=item.quantity))

    db.commit()
    return ApiResponse(success=True, message="Item added to cart")


@router.patch("/increase/{book_id}", response_model=ApiResponse)
def increase_cart_item(book_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """
    Increase the quantity of a cart item by 1.
    """
    cart = get_or_create_cart(user.id, db)
    cart_item = db.query(CartItem).filter_by(cart_id=cart.id, book_id=book_id).first()
    if not cart_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found in cart")

    book = db.query(Book).filter(Book.id == book_id).first()
    if cart_item.quantity + 1 > book.stock:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient stock. Available: {book.stock}"
        )

    cart_item.quantity += 1
    db.commit()
    return ApiResponse(success=True, message="Quantity increased")


@router.patch("/decrease/{book_id}", response_model=ApiResponse)
def decrease_cart_item(book_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """
    Decrease the quantity of a cart item by 1.
    If quantity reaches 0, remove the item.
    """
    cart = get_or_create_cart(user.id, db)
    cart_item = db.query(CartItem).filter_by(cart_id=cart.id, book_id=book_id).first()
    if not cart_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found in cart")

    if cart_item.quantity <= 1:
        db.delete(cart_item)
    else:
        cart_item.quantity -= 1

    db.commit()
    return ApiResponse(success=True, message="Quantity decreased")


@router.patch("/update", response_model=ApiResponse)
def update_cart_item(
    data: CartUpdateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Update the quantity of a cart item to a specific value.
    Accepts JSON body: {"book_id": 1, "quantity": 3}
    If quantity is 0 or less, remove the item.
    """
    if data.quantity < 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Quantity cannot be negative")

    cart = get_or_create_cart(user.id, db)
    cart_item = db.query(CartItem).filter_by(cart_id=cart.id, book_id=data.book_id).first()
    if not cart_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found in cart")

    if data.quantity == 0:
        db.delete(cart_item)
    else:
        book = db.query(Book).filter(Book.id == data.book_id).first()
        if data.quantity > book.stock:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient stock. Available: {book.stock}"
            )
        cart_item.quantity = data.quantity

    db.commit()
    return ApiResponse(success=True, message="Cart updated")


@router.delete("/remove/{book_id}", response_model=ApiResponse)
def remove_from_cart(book_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    cart = get_or_create_cart(user.id, db)
    deleted = db.query(CartItem).filter_by(cart_id=cart.id, book_id=book_id).delete()
    db.commit()
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found in cart")
    return ApiResponse(success=True, message="Item removed")


@router.delete("/clear", response_model=ApiResponse)
def clear_cart(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Delete every cart item belonging to the authenticated user."""
    cart = db.query(Cart).filter_by(user_id=user.id).first()
    if cart:
        db.query(CartItem).filter_by(cart_id=cart.id).delete()
        db.delete(cart)
        db.commit()
    return ApiResponse(success=True, message="Cart cleared")


@router.get("/count", response_model=ApiResponse)
def cart_count(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Return the number of items in the user's cart."""
    cart = db.query(Cart).filter_by(user_id=user.id).first()
    count = 0
    if cart:
        count = db.query(CartItem).filter_by(cart_id=cart.id).count()
    return ApiResponse(success=True, message="Success", data={"cart_count": count})
