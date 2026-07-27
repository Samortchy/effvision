import uuid
import time
import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = structlog.get_logger()

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        structlog.contextvars.bind_contextvars(request_id=request_id)
        start = time.perf_counter()

        logger.info("rqquest started", method = request.method, url = request.url.path)

        try:
            response = await call_next(request)
        except Exception:
            logger.error("request failed", method = request.method, url = request.url.path)
            raise

        duration = round((time.perf_counter() - start) * 1000, 2)
        logger.info("request completed", 
                    method = request.method,
                    url = request.url.path, 
                    status_code = response.status_code, 
                    duration_ms = duration)

        response.headers["X-Request-ID"] = request_id

        return response