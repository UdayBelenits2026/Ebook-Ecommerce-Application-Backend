from fastapi import (
    APIRouter,
    Depends,
    UploadFile,
    File,
    Form,
    HTTPException,
    status,
    Request,
)
from sqlalchemy.orm import Session
from sqlalchemy import text
import shutil
import os
from typing import Optional, Tuple, List

from app.database.session import get_db
from app.models.domain import Book, User
from app.schemas.book import BookCreate
from app.schemas.response import ApiResponse
from app.dependencies.auth import get_admin_user


router = APIRouter(prefix="/books", tags=["Books"])

os.makedirs("uploads/books", exist_ok=True)


# ==========================================================
# OPTIONAL AUTHENTICATED USER
# ==========================================================

def get_optional_user(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Return the currently authenticated user when a valid
    Authorization Bearer token is supplied.

    Anonymous requests are also allowed and return None.
    """

    from jose import JWTError, jwt
    from app.config.settings import settings

    auth_header = request.headers.get("Authorization")

    if not auth_header:
        return None

    if not auth_header.startswith("Bearer "):
        return None

    token = auth_header[len("Bearer "):]

    try:

        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )

        user_id = payload.get("user_id")

        if user_id is None:
            return None

        user = (
            db.query(User)
            .filter(User.id == int(user_id))
            .first()
        )

        return user

    except (JWTError, ValueError, TypeError):

        return None

    except Exception:

        return None


# ==========================================================
# BOOK SQL BUILDER
# ==========================================================

def get_base_books_sql_parts(
    user_id: Optional[int] = None
) -> Tuple[str, str, str, dict]:

    """
    Build the common SQL fragments used by the books APIs.

    Returns:

        select_cols
        from_tables
        group_by_cols
        params
    """

    select_cols = """
        b.id,
        b.title,
        b.author,
        b.category_id,
        b.publisher,
        b.isbn,
        b.language,
        b.pages,
        b.price,
        b.stock,
        b.description,
        b.image,
        b.rating AS db_rating,
        b.created_at,
        b.updated_at,
        c.name AS category_name,
        COALESCE(AVG(r.rating), 0) AS avg_rating,
        COUNT(r.id) AS review_count
    """

    extra_select = ""

    user_joins = ""

    params: dict = {}

    if user_id is not None:

        extra_select = """,
            CASE
                WHEN w.id IS NOT NULL THEN 1
                ELSE 0
            END AS in_wishlist,

            CASE
                WHEN ci.id IS NOT NULL THEN 1
                ELSE 0
            END AS in_cart
        """

        user_joins = """
            LEFT JOIN wishlists w
                ON w.book_id = b.id
                AND w.user_id = :uid

            LEFT JOIN carts ct
                ON ct.user_id = :uid

            LEFT JOIN cart_items ci
                ON ci.cart_id = ct.id
                AND ci.book_id = b.id
        """

        params["uid"] = user_id

    group_by_cols = (
        "b.id, "
        "b.title, "
        "b.author, "
        "b.category_id, "
        "b.publisher, "
        "b.isbn, "
        "b.language, "
        "b.pages, "
        "b.price, "
        "b.stock, "
        "b.description, "
        "b.image, "
        "b.rating, "
        "b.created_at, "
        "b.updated_at, "
        "c.name"
    )

    if user_id is not None:

        group_by_cols += ", w.id, ci.id"

    from_tables = f"""
        FROM books b

        LEFT JOIN categories c
            ON c.id = b.category_id

        LEFT JOIN reviews r
            ON r.book_id = b.id

        {user_joins}
    """

    select_cols += extra_select

    return (
        select_cols,
        from_tables,
        group_by_cols,
        params
    )


# ==========================================================
# FORMAT DATETIME
# ==========================================================

def _format_datetime(value):

    if value is None:
        return None

    if hasattr(value, "isoformat"):
        return value.isoformat()

    return str(value)


# ==========================================================
# FORMAT BOOK RESPONSE
# ==========================================================

def format_book_row(row: dict) -> dict:

    return {

        "id": row["id"],

        "title": row["title"],

        "author": row["author"],

        "category_id": row["category_id"],

        "publisher": row["publisher"],

        "isbn": row["isbn"],

        "language": row["language"],

        "pages": row["pages"],

        "price": row["price"],

        "stock": row["stock"],

        "description": row["description"],

        "image": row["image"],

        "rating": float(
            row.get(
                "avg_rating",
                row.get("db_rating", 0)
            )
            or 0
        ),

        "review_count": int(
            row.get("review_count", 0)
            or 0
        ),

        "category_name": row.get("category_name"),

        "created_at": _format_datetime(
            row.get("created_at")
        ),

        "updated_at": _format_datetime(
            row.get("updated_at")
        ),

        "in_wishlist": bool(
            row.get("in_wishlist", False)
        ),

        "in_cart": bool(
            row.get("in_cart", False)
        ),

    }


# ==========================================================
# GET BOOKS
# ==========================================================

@router.get("", response_model=ApiResponse)
def get_books(
    db: Session = Depends(get_db),
    page: int = 1,
    limit: int = 10,
    search: Optional[str] = None,
    category_id: Optional[int] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    sort_by: str = "newest",
    user: Optional[User] = Depends(get_optional_user),
):

    """
    Get books with filtering, sorting and pagination.

    Authenticated users additionally receive:

    in_wishlist
    in_cart
    """

    # ------------------------------------------------------
    # Pagination validation
    # ------------------------------------------------------

    page = max(page, 1)

    limit = max(1, min(limit, 100))

    # ------------------------------------------------------
    # User
    # ------------------------------------------------------

    user_id = user.id if user else None

    (
        select_cols,
        from_tables,
        group_by,
        params
    ) = get_base_books_sql_parts(user_id)

    # ------------------------------------------------------
    # Filters
    # ------------------------------------------------------

    conditions: List[str] = []

    if search and search.strip():

        conditions.append(
            """
            (
                LOWER(b.title) LIKE LOWER(:search)
                OR
                LOWER(b.author) LIKE LOWER(:search)
            )
            """
        )

        params["search"] = f"%{search.strip()}%"

    if category_id is not None:

        conditions.append(
            "b.category_id = :cat_id"
        )

        params["cat_id"] = category_id

    if min_price is not None:

        conditions.append(
            "b.price >= :min_price"
        )

        params["min_price"] = min_price

    if max_price is not None:

        conditions.append(
            "b.price <= :max_price"
        )

        params["max_price"] = max_price

    where_clause = ""

    if conditions:

        where_clause = (
            " WHERE " +
            " AND ".join(conditions)
        )

    # ------------------------------------------------------
    # Sorting
    # ------------------------------------------------------

    order_clause = " ORDER BY b.created_at DESC"

    if sort_by == "price":

        order_clause = " ORDER BY b.price ASC"

    elif sort_by == "price_desc":

        order_clause = " ORDER BY b.price DESC"

    elif sort_by == "rating":

        order_clause = " ORDER BY avg_rating DESC"

    elif sort_by == "oldest":

        order_clause = " ORDER BY b.created_at ASC"

    elif sort_by == "title":

        order_clause = " ORDER BY b.title ASC"

    # ------------------------------------------------------
    # Count
    # ------------------------------------------------------

    count_sql = f"""
        SELECT COUNT(*)
        FROM books b
        {where_clause}
    """

    total = (
        db.execute(
            text(count_sql),
            params
        ).scalar()
        or 0
    )

    # ------------------------------------------------------
    # Pagination
    # ------------------------------------------------------

    query_params = dict(params)

    query_params["limit"] = limit

    query_params["offset"] = (
        page - 1
    ) * limit

    # ------------------------------------------------------
    # Books query
    # ------------------------------------------------------

    data_sql = f"""
        SELECT
            {select_cols}

        {from_tables}

        {where_clause}

        GROUP BY
            {group_by}

        {order_clause}

        LIMIT :limit
        OFFSET :offset
    """

    rows = (
        db.execute(
            text(data_sql),
            query_params
        )
        .mappings()
        .all()
    )

    items = [

        format_book_row(dict(row))

        for row in rows

    ]

    # ------------------------------------------------------
    # Response
    # ------------------------------------------------------

    return ApiResponse(

        success=True,

        message="Success",

        data={

            "items": items,

            "total": int(total),

            "page": page,

            "limit": limit

        }

    )


# ==========================================================
# GET SINGLE BOOK
# ==========================================================

@router.get("/{book_id}", response_model=ApiResponse)
def get_book_by_id(
    book_id: int,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_optional_user),
):

    """
    Get one book using its ID.
    """

    user_id = user.id if user else None

    (
        select_cols,
        from_tables,
        group_by,
        params
    ) = get_base_books_sql_parts(user_id)

    params["bid"] = book_id

    sql = f"""
        SELECT
            {select_cols}

        {from_tables}

        WHERE b.id = :bid

        GROUP BY
            {group_by}
    """

    row = (
        db.execute(
            text(sql),
            params
        )
        .mappings()
        .first()
    )

    if not row:

        raise HTTPException(

            status_code=status.HTTP_404_NOT_FOUND,

            detail="Book not found"

        )

    return ApiResponse(

        success=True,

        message="Success",

        data=format_book_row(
            dict(row)
        )

    )


# ==========================================================
# ADMIN - CREATE BOOK
# ==========================================================

@router.post(
    "",
    response_model=ApiResponse,
    dependencies=[Depends(get_admin_user)]
)
def create_book(
    title: str = Form(...),
    author: str = Form(...),
    category_id: int = Form(...),
    publisher: str = Form(...),
    isbn: str = Form(...),
    language: str = Form(...),
    pages: int = Form(...),
    price: float = Form(...),
    stock: int = Form(...),
    description: str = Form(...),
    image: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):

    book_data = BookCreate(

        title=title,

        author=author,

        category_id=category_id,

        publisher=publisher,

        isbn=isbn,

        language=language,

        pages=pages,

        price=price,

        stock=stock,

        description=description

    )

    db_book = Book(
        **book_data.model_dump()
    )

    db.add(db_book)

    db.commit()

    db.refresh(db_book)

    # ------------------------------------------------------
    # Image
    # ------------------------------------------------------

    if image and image.filename:

        img_ext = os.path.splitext(
            image.filename
        )[1]

        img_path = (
            f"uploads/books/"
            f"{db_book.id}{img_ext}"
        )

        with open(
            img_path,
            "wb"
        ) as buffer:

            shutil.copyfileobj(
                image.file,
                buffer
            )

        db.query(Book).filter(
            Book.id == db_book.id
        ).update({

            "image": img_path

        })

        db.commit()

    return ApiResponse(

        success=True,

        message="Book created",

        data={
            "id": db_book.id
        }

    )


# ==========================================================
# ADMIN - UPDATE BOOK
# ==========================================================

@router.put(
    "/{id}",
    response_model=ApiResponse,
    dependencies=[Depends(get_admin_user)]
)
def update_book(
    id: int,
    title: Optional[str] = Form(None),
    author: Optional[str] = Form(None),
    category_id: Optional[int] = Form(None),
    publisher: Optional[str] = Form(None),
    isbn: Optional[str] = Form(None),
    language: Optional[str] = Form(None),
    pages: Optional[int] = Form(None),
    price: Optional[float] = Form(None),
    stock: Optional[int] = Form(None),
    description: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):

    db_book = (
        db.query(Book)
        .filter(Book.id == id)
        .first()
    )

    if not db_book:

        raise HTTPException(

            status_code=status.HTTP_404_NOT_FOUND,

            detail="Book not found"

        )

    update_data = {}

    if title is not None:
        update_data["title"] = title

    if author is not None:
        update_data["author"] = author

    if category_id is not None:
        update_data["category_id"] = category_id

    if publisher is not None:
        update_data["publisher"] = publisher

    if isbn is not None:
        update_data["isbn"] = isbn

    if language is not None:
        update_data["language"] = language

    if pages is not None:
        update_data["pages"] = pages

    if price is not None:
        update_data["price"] = price

    if stock is not None:
        update_data["stock"] = stock

    if description is not None:
        update_data["description"] = description

    if update_data:

        db.query(Book).filter(
            Book.id == id
        ).update(update_data)

        db.commit()

    # ------------------------------------------------------
    # Image
    # ------------------------------------------------------

    if image and image.filename:

        img_ext = os.path.splitext(
            image.filename
        )[1]

        img_path = (
            f"uploads/books/"
            f"{id}{img_ext}"
        )

        with open(
            img_path,
            "wb"
        ) as buffer:

            shutil.copyfileobj(
                image.file,
                buffer
            )

        db.query(Book).filter(
            Book.id == id
        ).update({

            "image": img_path

        })

        db.commit()

    return ApiResponse(

        success=True,

        message="Book updated",

        data=None

    )


# ==========================================================
# ADMIN - DELETE BOOK
# ==========================================================

@router.delete(
    "/{id}",
    response_model=ApiResponse,
    dependencies=[Depends(get_admin_user)]
)
def delete_book(
    id: int,
    db: Session = Depends(get_db)
):

    db_book = (
        db.query(Book)
        .filter(Book.id == id)
        .first()
    )

    if not db_book:

        raise HTTPException(

            status_code=status.HTTP_404_NOT_FOUND,

            detail="Book not found"

        )

    db.delete(db_book)

    db.commit()

    return ApiResponse(

        success=True,

        message="Book deleted",

        data=None

    )


# ==========================================================
# ADMIN - UPLOAD BOOK IMAGE
# ==========================================================

@router.post(
    "/{id}/upload-image",
    response_model=ApiResponse,
    dependencies=[Depends(get_admin_user)]
)
def upload_image(
    id: int,
    image: UploadFile = File(...),
    db: Session = Depends(get_db)
):

    book = (
        db.query(Book)
        .filter(Book.id == id)
        .first()
    )

    if not book:

        raise HTTPException(

            status_code=status.HTTP_404_NOT_FOUND,

            detail="Book not found"

        )

    if not image.filename:

        raise HTTPException(

            status_code=status.HTTP_400_BAD_REQUEST,

            detail="Image file is required"

        )

    img_ext = os.path.splitext(
        image.filename
    )[1]

    path = (
        f"uploads/books/"
        f"{id}{img_ext}"
    )

    with open(
        path,
        "wb"
    ) as buffer:

        shutil.copyfileobj(
            image.file,
            buffer
        )

    db.query(Book).filter(
        Book.id == id
    ).update({

        "image": path

    })

    db.commit()

    return ApiResponse(

        success=True,

        message="Image uploaded",

        data={
            "image": path
        }

    )