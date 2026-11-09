import logging
import time
import uuid
from logging.handlers import RotatingFileHandler
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.config.settings import get_settings

settings = get_settings()


def setup_logging() -> None:
    """Configure rotating file loggers and console handlers."""
    settings.LOGS_DIR.mkdir(parents=True, exist_ok=True)
    
    app_log_path = settings.LOGS_DIR / "app.log"
    error_log_path = settings.LOGS_DIR / "error.log"

    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s] [%(filename)s:%(lineno)d] - %(message)s"
    )

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))

    # Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))
    root_logger.addHandler(console_handler)

    # App File Handler (all messages >= INFO)
    app_handler = RotatingFileHandler(
        str(app_log_path), maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    app_handler.setFormatter(formatter)
    app_handler.setLevel(logging.INFO)
    root_logger.addHandler(app_handler)

    # Error File Handler (only ERROR and CRITICAL)
    error_handler = RotatingFileHandler(
        str(error_log_path), maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    error_handler.setFormatter(formatter)
    error_handler.setLevel(logging.ERROR)
    root_logger.addHandler(error_handler)


logger = logging.getLogger("rag.middleware.logger")


class RequestLoggerMiddleware(BaseHTTPMiddleware):
    """Logs incoming HTTP requests, assigns X-Request-ID, and records latency."""

    async def dispatch(self, request: Request, call_next) -> Response:
        req_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = req_id

        start_time = time.perf_counter()
        client_ip = request.client.host if request.client else "unknown"

        logger.info(
            f"--> [{req_id}] {request.method} {request.url.path} from {client_ip}"
        )

        try:
            response = await call_next(request)
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            response.headers["X-Request-ID"] = req_id
            response.headers["X-Process-Time-Ms"] = f"{duration_ms:.2f}"

            logger.info(
                f"<-- [{req_id}] {request.method} {request.url.path} "
                f"Status: {response.status_code} in {duration_ms:.2f}ms"
            )
            return response
        except Exception as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            logger.error(
                f"<-- [{req_id}] {request.method} {request.url.path} Failed in {duration_ms:.2f}ms: {exc}"
            )
            raise exc
