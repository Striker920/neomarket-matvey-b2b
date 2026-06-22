import os

class Settings:
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "test-secret-key")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    B2B_SERVICE_KEY: str = os.getenv("B2B_SERVICE_KEY", "moderation-service-secret-key")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./test.db")

settings = Settings()