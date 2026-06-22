from fastapi import Request
from jose import jwt, JWTError
from datetime import datetime, timedelta
from app.core.config import settings


def get_seller_id_from_request(request: Request) -> str:
    """Извлекаем seller_id из JWT-токена."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise ValueError("Invalid authorization header")
    
    token = auth_header.replace("Bearer ", "")
    
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        seller_id = payload.get("sub")
        if not seller_id:
            raise ValueError("Invalid token")
        return seller_id
    except JWTError:
        raise ValueError("Invalid token")


def check_x_service_key(x_service_key: str) -> bool:
    """Проверяем X-Service-Key для межсервисных вызовов."""
    return x_service_key and x_service_key == settings.B2B_SERVICE_KEY


# ✅ ДОБАВЛЕНО: функция для создания JWT-токенов (для тестов)
def create_access_token(seller_id: str, expires_delta: timedelta = None) -> str:
    """
    Создаёт JWT-токен для продавца.
    Используется в тестах для генерации валидных токенов.
    """
    if expires_delta is None:
        expires_delta = timedelta(hours=1)
    
    expire = datetime.utcnow() + expires_delta
    to_encode = {
        "sub": str(seller_id),
        "exp": expire
    }
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    
    return encoded_jwt