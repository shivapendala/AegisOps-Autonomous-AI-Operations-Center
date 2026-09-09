"""
Custom Exception Classes and Global Error Handlers for FastAPI.
Provides standardized, structured JSON error responses.
"""

from typing import Any, Dict, Optional
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse


class AegisOpsException(Exception):
    """Base application domain exception."""

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class ResourceNotFoundError(AegisOpsException):
    def __init__(self, resource: str, resource_id: str):
        super().__init__(
            message=f"{resource} with ID '{resource_id}' was not found.",
            status_code=status.HTTP_404_NOT_FOUND,
        )


class LLMServiceError(AegisOpsException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"AI Operations Engine Error: {message}",
            status_code=status.HTTP_502_BAD_GATEWAY,
            details=details,
        )


def register_exception_handlers(app: FastAPI) -> None:
    """Registers domain exception handlers on the FastAPI application instance."""

    @app.exception_handler(AegisOpsException)
    async def handle_domain_exception(request: Request, exc: AegisOpsException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": {
                    "type": exc.__class__.__name__,
                    "message": exc.message,
                    "details": exc.details,
                    "path": request.url.path,
                },
            },
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_exception(request: Request, exc: Exception):
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "error": {
                    "type": "InternalServerError",
                    "message": "An unexpected error occurred in the operations processing pipeline.",
                    "details": str(exc),
                    "path": request.url.path,
                },
            },
        )
