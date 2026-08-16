import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Online Book Store API"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./bookstore.db")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "secret")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60))

    # Refresh token configuration
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 7))

    SMTP_SERVER: str = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", 587))
    SMTP_USERNAME: str = os.getenv("SMTP_USERNAME", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    ADMIN_EMAIL: str = os.getenv("ADMIN_EMAIL", "admin@bookstore.com")
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "Admin@123")

    STORE_NAME: str = os.getenv("STORE_NAME", "Ebook")
    STORE_EMAIL: str = os.getenv("STORE_EMAIL", "admin@bookstore.com")

    @property
    def CASHFREE_APP_ID(self) -> str:
        return self.CASHFREE_CLIENT_ID

    @property
    def CASHFREE_SECRET_KEY(self) -> str:
        return self.CASHFREE_CLIENT_SECRET

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()