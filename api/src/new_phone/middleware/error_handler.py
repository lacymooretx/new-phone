import structlog
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

logger = structlog.get_logger()


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """RFC 7807 Problem Details error response."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "type": "about:blank",
            "title": _status_phrase(exc.status_code),
            "status": exc.status_code,
            "detail": exc.detail,
            "instance": str(request.url.path),
        },
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all for unhandled exceptions."""
    logger.exception("unhandled_exception", path=request.url.path, error=str(exc))
    return JSONResponse(
        status_code=500,
        content={
            "type": "about:blank",
            "title": "Internal Server Error",
            "status": 500,
            "detail": "An unexpected error occurred",
            "instance": str(request.url.path),
        },
    )


def _status_phrase(code: int) -> str:
    phrases = {
        400: "Bad Request",
        401: "Unauthorized",
        403: "Forbidden",
        404: "Not Found",
        409: "Conflict",
        422: "Unprocessable Entity",
        429: "Too Many Requests",
        500: "Internal Server Error",
    }
    return phrases.get(code, "Error")
