import os
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.database.session import Base, engine, SessionLocal
from app.models.domain import User, Category
from app.utils.security import get_password_hash
from app.config.settings import settings

# Import all routers
from app.auth.router import router as auth_router
from app.books.router import router as books_router
from app.categories.router import router as categories_router
from app.cart.router import router as cart_router
from app.wishlist.router import router as wishlist_router
from app.orders.router import router as orders_router
from app.reviews.router import router as reviews_router
from app.users.router import router as users_router, customer_router
from app.contact.router import router as contact_router
from app.admin.router import router as admin_router
from app.address.router import router as address_router
from app.notification.router import router as notification_router


# Create Tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.PROJECT_NAME, description="Production Bookstore API", version="1.0.0")

# CORS setup for Angular Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure the upload directories exist before mounting to avoid startup crashes
os.makedirs("static/uploads/users", exist_ok=True)
os.makedirs("uploads/books", exist_ok=True)
# Mount the /static route to serve images correctly based on the admin router path
app.mount("/static", StaticFiles(directory="static"), name="static")
# Mount /uploads to serve uploaded book images
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"success": False, "message": str(exc)})

# Register routers
app.include_router(auth_router)
app.include_router(books_router)
app.include_router(categories_router)
app.include_router(cart_router)
app.include_router(wishlist_router)
app.include_router(orders_router)
app.include_router(reviews_router)
app.include_router(users_router)
app.include_router(customer_router)
app.include_router(contact_router)
app.include_router(admin_router)
app.include_router(address_router)
app.include_router(notification_router)

@app.on_event("startup")
def seed_data():
    db = SessionLocal()
    try:
        # Seed Admin profile
        if not db.query(User).filter(User.email == settings.ADMIN_EMAIL).first():
            db.add(User(
                full_name="Allem Suchitra", 
                email=settings.ADMIN_EMAIL, 
                password=get_password_hash(settings.ADMIN_PASSWORD), 
                is_verified=True, 
               role="admin"
            ))
            
        # Seed Categories
        for cat in ["Fiction", "Sci-Fi", "Mystery", "Biography"]:
            if not db.query(Category).filter(Category.name == cat).first():
                db.add(Category(name=cat, description=f"{cat} books"))
        db.commit()
    finally:
        db.close()
