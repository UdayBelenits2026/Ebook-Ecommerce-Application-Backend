from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.database.session import get_db
from app.models.domain import Review, User, Book
from app.schemas.review import ReviewCreate
from app.schemas.response import ApiResponse
from app.dependencies.auth import get_current_user


router = APIRouter(
    prefix="/reviews",
    tags=["Reviews"]
)


# ============================================================
# ADD REVIEW
# ============================================================

@router.post("", response_model=ApiResponse)
def add_review(
    review: ReviewCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Add a review and dynamically update the book's average rating.
    """

    # --------------------------------------------------------
    # Check if book exists
    # --------------------------------------------------------

    book = db.query(Book).filter_by(
        id=review.book_id
    ).first()

    if not book:
        return ApiResponse(
            success=False,
            message="Book not found"
        )

    # --------------------------------------------------------
    # Check if user already reviewed this book
    # --------------------------------------------------------

    existing = (
        db.query(Review)
        .filter_by(
            book_id=review.book_id,
            user_id=user.id
        )
        .first()
    )

    if existing:
        return ApiResponse(
            success=False,
            message="You have already reviewed this book"
        )

    # --------------------------------------------------------
    # Add review
    # --------------------------------------------------------

    new_review = Review(
        **review.model_dump(),
        user_id=user.id
    )

    db.add(new_review)

    db.flush()

    # --------------------------------------------------------
    # Recalculate average rating
    # --------------------------------------------------------

    result = db.execute(
        text("""
            SELECT COALESCE(AVG(rating), 0)
            FROM reviews
            WHERE book_id = :bid
        """),
        {
            "bid": review.book_id
        }
    ).scalar()

    # --------------------------------------------------------
    # Update book rating
    # --------------------------------------------------------

    db.query(Book).filter(
        Book.id == review.book_id
    ).update({
        "rating": float(result or 0)
    })

    db.commit()

    return ApiResponse(
        success=True,
        message="Review added"
    )


# ============================================================
# GET REVIEWS FOR BOOK
# ============================================================

@router.get("/{book_id}", response_model=ApiResponse)
def get_reviews(
    book_id: int,
    db: Session = Depends(get_db)
):
    """
    Get all reviews for a book,
    including user's full_name and profile_image.
    """

    # --------------------------------------------------------
    # Check book exists
    # --------------------------------------------------------

    book = (
        db.query(Book)
        .filter(Book.id == book_id)
        .first()
    )

    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found"
        )

    # --------------------------------------------------------
    # Get reviews
    # --------------------------------------------------------

    sql = text("""
        SELECT
            r.id,
            r.book_id,
            r.user_id,
            r.rating,
            r.review,
            r.created_at,
            u.full_name,
            u.profile_image
        FROM reviews r
        JOIN users u
            ON u.id = r.user_id
        WHERE r.book_id = :bid
        ORDER BY r.created_at DESC
    """)

    rows = db.execute(
        sql,
        {
            "bid": book_id
        }
    ).mappings().all()

    items = [
        dict(row)
        for row in rows
    ]

    # --------------------------------------------------------
    # Convert created_at safely to string
    # --------------------------------------------------------

    for item in items:

        created_at = item.get("created_at")

        if created_at is None:
            item["created_at"] = None

        elif hasattr(created_at, "isoformat"):
            # datetime/date object
            item["created_at"] = created_at.isoformat()

        else:
            # Already a string or another value
            item["created_at"] = str(created_at)

    # --------------------------------------------------------
    # Return response
    # --------------------------------------------------------

    return ApiResponse(
        success=True,
        message="Success",
        data=items
    )


# ============================================================
# GET REVIEW SUMMARY
# ============================================================

@router.get("/{book_id}/summary", response_model=ApiResponse)
def get_review_summary(
    book_id: int,
    db: Session = Depends(get_db)
):
    """
    Get review summary for a book:
    - average rating
    - total review count
    - rating distribution
    """

    # --------------------------------------------------------
    # Check book exists
    # --------------------------------------------------------

    book = (
        db.query(Book)
        .filter(Book.id == book_id)
        .first()
    )

    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found"
        )

    # --------------------------------------------------------
    # Average rating
    # --------------------------------------------------------

    avg_result = db.execute(
        text("""
            SELECT COALESCE(AVG(rating), 0)
            FROM reviews
            WHERE book_id = :bid
        """),
        {
            "bid": book_id
        }
    ).scalar()

    # --------------------------------------------------------
    # Review count
    # --------------------------------------------------------

    count_result = db.execute(
        text("""
            SELECT COUNT(*)
            FROM reviews
            WHERE book_id = :bid
        """),
        {
            "bid": book_id
        }
    ).scalar()

    # --------------------------------------------------------
    # Rating distribution
    # --------------------------------------------------------

    dist_rows = db.execute(
        text("""
            SELECT
                rating,
                COUNT(*) AS cnt
            FROM reviews
            WHERE book_id = :bid
            GROUP BY rating
            ORDER BY rating DESC
        """),
        {
            "bid": book_id
        }
    ).mappings().all()

    distribution = {
        "5": 0,
        "4": 0,
        "3": 0,
        "2": 0,
        "1": 0
    }

    for row in dist_rows:

        rating = int(row["rating"])

        if rating in [1, 2, 3, 4, 5]:

            distribution[str(rating)] = int(
                row["cnt"]
            )

    # --------------------------------------------------------
    # Return summary
    # --------------------------------------------------------

    return ApiResponse(
        success=True,
        message="Success",
        data={
            "average_rating": round(
                float(avg_result or 0),
                1
            ),

            "review_count": int(
                count_result or 0
            ),

            "rating_distribution": distribution
        }
    )