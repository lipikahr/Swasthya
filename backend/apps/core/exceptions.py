"""One error shape for the whole API, so the frontend and agent can rely on it.

    {
      "error": {
        "code": "validation_error",
        "message": "Human readable summary",
        "details": {"field": ["problem", ...]}   # only when there are field errors
      }
    }
"""
import logging

from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


def _first_validation_message(details) -> str:
    if isinstance(details, list) and details:
        return str(details[0])
    if isinstance(details, dict):
        for key, value in details.items():
            if isinstance(value, (list, dict)):
                nested = _first_validation_message(value)
                if nested:
                    return nested
            elif value:
                return str(value)
    if details:
        return str(details)
    return "The submitted data is not valid."


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return None  # unhandled errors become a normal 500, never leaking details

    if isinstance(exc, ValidationError):
        code = "validation_error"
        details = response.data
        message = _first_validation_message(details)
        view = getattr(context.get("view"), "__class__", type("x", (), {}))
        logger.info(
            "validation_error view=%s status=%s fields=%s",
            getattr(view, "__name__", ""),
            response.status_code,
            sorted(details.keys()) if isinstance(details, dict) else "list",
        )
    else:
        code = getattr(exc, "default_code", "error")
        detail = response.data.get("detail") if isinstance(response.data, dict) else None
        message = str(detail) if detail is not None else "Request failed."
        details = None

    if response.status_code == status.HTTP_401_UNAUTHORIZED:
        code = "not_authenticated"

    body = {"code": str(code), "message": message}
    if details is not None:
        body["details"] = details
    response.data = {"error": body}
    return response
