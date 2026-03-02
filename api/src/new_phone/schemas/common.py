from pydantic import BaseModel


class ErrorDetail(BaseModel):
    """RFC 7807 Problem Details for HTTP APIs."""

    type: str = "about:blank"
    title: str
    status: int
    detail: str
    instance: str | None = None


class PaginatedResponse(BaseModel):
    items: list
    total: int
    page: int = 1
    per_page: int = 50
