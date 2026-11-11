from app.middlewares.auth import register_jwt_callbacks
from app.middlewares.error_handlers import register_error_handlers
from app.middlewares.request_hooks import register_request_hooks

__all__ = ["register_error_handlers", "register_jwt_callbacks", "register_request_hooks"]
