from fastapi import Depends, HTTPException, Request
from jose import JWTError, jwt
from uuid import UUID
import os

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"

async def get_current_seller_id(request: Request) -> UUID:
    auth_header = request.headers.get("Authorization")
    
    if not auth_header:
        raise HTTPException(
            status_code=401,
            headers={"WWW-Authenticate": "Bearer"},
            detail={"code": "UNAUTHORIZED", "message": "Missing Authorization header"}
        )
    
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            headers={"WWW-Authenticate": "Bearer"},
            detail={"code": "UNAUTHORIZED", "message": "Invalid authorization scheme"}
        )
    
    token = auth_header.split(" ")[1]
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        seller_id_str = payload.get("sub")
        
        if not seller_id_str:
            raise HTTPException(
                status_code=401,
                detail={"code": "UNAUTHORIZED", "message": "Token missing 'sub' claim"}
            )
        
        return UUID(seller_id_str)
        
    except JWTError:
        raise HTTPException(
            status_code=401,
            detail={"code": "UNAUTHORIZED", "message": "Invalid or expired token"}
        )
    except ValueError:
        raise HTTPException(
            status_code=401,
            detail={"code": "UNAUTHORIZED", "message": "Invalid seller_id format in token"}
        )