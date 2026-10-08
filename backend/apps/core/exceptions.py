"""One error shape for the whole API, so the frontend and agent can rely on it.

    {
      "error": {
        "code": "validation_error",
        "message": "Human readable summary",
        "details": {"field": ["problem", ...]}   # only when there are field errors
      }
    }
"""
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.views import exception_handler


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return None  # unhandled errors become a normal 500, never leaking details

    if isinstance(exc, ValidationError):
        code, message = "validation_error", "The submitted data is not valid."
        details = response.data
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
