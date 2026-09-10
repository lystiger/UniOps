from typing import Any

from fastapi import HTTPException


class ApiError(HTTPException):
    """Structured API error carrying a machine-readable code and parameters.

    detail remains the English string for backwards compatibility with existing
    tests, API consumers, and server loggers.
    """

    def __init__(
        self,
        status_code: int,
        detail: str,
        code: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ):
        super().__init__(status_code=status_code, detail=detail, headers=headers)
        self.code = code
        self.params = params or {}
