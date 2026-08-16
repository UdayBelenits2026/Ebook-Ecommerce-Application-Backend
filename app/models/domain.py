from sqlalchemy import Column, Integer, String, Float, Boolean, Text, ForeignKey, DateTime, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime, timezone
import enum
from app.database.session import Base
from sqlalchemy import Column, Date, Integer
from datetime import datetime


def utcnow(): return datetime.now(timezone.utc)

class OrderStatus(str, enum.Enum):
    PENDING, PROCESSING, SHIPPED, DELIVERED, CANCELLED = "PENDING", "PROCESSING", "SHIPPED", "DELIVERED", "CANCELLED"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    phone = Column(String(20))
    password = Column(String(255), nullable=False)
    is_verified = Column(Boolean, default=False)
    role = Column(String, default="customer")
    profile_image = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    @property
    def is_admin(self):
        return self.role == "admin"

class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text)
    image = Column(String(255))

    books = relationship("Book", back_populates="category")

class Book(Base):
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), index=True, nullable=False)
    author = Column(String(255), index=True, nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"))
    publisher = Column(String(255), index=True)
    isbn = Column(String(20), unique=True, index=True)
    language = Column(String(50))
    pages = Column(Integer)
    price = Column(Float, nullable=False)
    stock = Column(Integer, default=0)
    description = Column(Text)
    image = Column(String(255))
    rating = Column(Float, default=0.0)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    category = relationship("Category", back_populates="books")
    reviews = relationship("Review", back_populates="book")

class Cart(Base):
    __tablename__ = "carts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    created_at = Column(DateTime, default=utcnow)

    items = relationship("CartItem", back_populates="cart", cascade="all, delete-orphan")

class CartItem(Base):
    __tablename__ = "cart_items"

    id = Column(Integer, primary_key=True, index=True)
    cart_id = Column(Integer, ForeignKey("carts.id"))
    book_id = Column(Integer, ForeignKey("books.id"))
    quantity = Column(Integer, default=1)

    cart = relationship("Cart", back_populates="items")
    book = relationship("Book")

class Wishlist(Base):
    __tablename__ = "wishlists"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    book_id = Column(Integer, ForeignKey("books.id"))

    book = relationship("Book")

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

    total_amount = Column(
        Float,
        nullable=False
    )

    payment_method = Column(
        String(50),
        nullable=False
    )

    order_status = Column(
        Enum(OrderStatus),
        default=OrderStatus.PENDING
    )

    address_id = Column(
        Integer,
        ForeignKey("addresses.id"),
        nullable=False
    )

    shipping_address = Column(
        Text,
        nullable=False
    )

    created_at = Column(
        DateTime,
        default=utcnow
    )
    tracking_number = Column(String)
    courier_name = Column(String)
    estimated_delivery = Column(Date)
    # Relationships
    address = relationship("Address")

    items = relationship(
        "OrderItem",
        back_populates="order",
        cascade="all, delete-orphan"
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)

    order_id = Column(
        Integer,
        ForeignKey("orders.id"),
        nullable=False
    )

    book_id = Column(
        Integer,
        ForeignKey("books.id"),
        nullable=False
    )

    quantity = Column(
        Integer,
        nullable=False
    )

    price = Column(
        Float,
        nullable=False
    )

    order = relationship(
        "Order",
        back_populates="items"
    )

    book = relationship("Book")
class OTPVerification(Base):
    __tablename__ = "otp_verifications"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(100), index=True)
    otp = Column(String(6))
    expiry_time = Column(DateTime)

class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    book_id = Column(Integer, ForeignKey("books.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    rating = Column(Float, nullable=False)
    review = Column(Text, nullable=False)
    created_at = Column(DateTime, default=utcnow)

    book = relationship("Book", back_populates="reviews")
    user = relationship("User")

class ContactMessage(Base):
    __tablename__ = "contact_messages"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), nullable=False)
    subject = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utcnow)
class Address(Base):
    __tablename__ = "addresses"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

    full_name = Column(
        String(100),
        nullable=False
    )

    mobile = Column(
        String(15),
        nullable=False
    )

    house_no = Column(
        String(100),
        nullable=False
    )

    street = Column(
        String(150),
        nullable=True
    )

    area = Column(
        String(100),
        nullable=False
    )

    village_city = Column(
        String(100),
        nullable=False
    )

    district = Column(
        String(100),
        nullable=False
    )

    state = Column(
        String(100),
        nullable=False
    )

    pincode = Column(
        String(10),
        nullable=False
    )

    landmark = Column(
        String(150),
        nullable=True
    )

    is_default = Column(
        Boolean,
        default=False
    )

    created_at = Column(
        DateTime,
        default=utcnow
    )

    updated_at = Column(
        DateTime,
        default=utcnow,
        onupdate=utcnow
    )

    user = relationship("User")


class PaymentTransaction(Base):
    __tablename__ = "payment_transactions"

    id = Column(Integer, primary_key=True, index=True)
    cashfree_order_id = Column(String(100), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    address_id = Column(Integer, ForeignKey("addresses.id"), nullable=False)
    amount = Column(Float, nullable=False)
    payment_session_id = Column(String(255), nullable=True)
    status = Column(String(50), default="PENDING")
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    user = relationship("User")
    address = relationship("Address")
    order = relationship("Order")
class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)

    # Customer who owns this notification
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Notification title
    title = Column(String(255), nullable=False)

    # Notification message
    message = Column(Text, nullable=False)

    # order / offer / announcement / new_arrival
    type = Column(String(50), nullable=False)

    # Read status
    is_read = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", backref="notifications")