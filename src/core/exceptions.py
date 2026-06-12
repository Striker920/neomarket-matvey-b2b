from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

class AppError(Exception):
    def __init__(self, code: str, message: str, status_code: int):
        self.code = code
        self.message = message
        self.status_code = status_code

async def app_exception_handler(request: Request, exc: AppError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.code, "message": exc.message}
    )

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    msg = errors[0]["msg"] if errors else "Ошибка валидации данных"
    return JSONResponse(
        status_code=400,
        content={"code": "VALIDATION_ERROR", "message": msg}
    )

async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    code_map = {
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        409: "CONFLICT",
        422: "UNPROCESSABLE_ENTITY",
        500: "INTERNAL_ERROR",
        503: "SERVICE_UNAVAILABLE"
    }
    code = code_map.get(exc.status_code, "HTTP_ERROR")
    
    # Защита от утечки внутренних деталей: не используем сырой str(e)
    if exc.status_code == 401:
        message = "Требуется авторизация (Bearer токен)"
    elif exc.status_code == 403:
        message = "Доступ запрещен"
    elif exc.status_code == 404:
        message = "Ресурс не найден"
    elif exc.status_code == 409:
        message = "Конфликт данных (например, артикул уже существует)"
    elif isinstance(exc.detail, str):
        message = exc.detail
    else:
        message = "Произошла ошибка"

    return JSONResponse(
        status_code=exc.status_code,
        content={"code": code, "message": message}
    )

async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"code": "INTERNAL_ERROR", "message": "Внутренняя ошибка сервера"}
    )