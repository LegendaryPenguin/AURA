from server.api.middleware.cors import register_cors_middleware
from server.api.middleware.error_handler import register_error_handler_middleware

__all__ = ["register_cors_middleware", "register_error_handler_middleware"]
