import uuid
import time
import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = structlog.get_logger()

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Clear first: contextvars survive on the task that serves the request,
        # so without this a later request can inherit an earlier one's
        # request_id and the logs stitch two requests into one trace.
        structlog.contextvars.clear_contextvars()

        request_id = str(uuid.uuid4())
        structlog.contextvars.bind_contextvars(request_id=request_id)
        start = time.perf_counter()

        logger.info("request started", method = request.method, url = request.url.path)

        try:
            response = await call_next(request)

            duration = round((time.perf_counter() - start) * 1000, 2)
            logger.info("request completed",
                        method = request.method,
                        url = request.url.path,
                        status_code = response.status_code,
                        duration_ms = duration)

            response.headers["X-Request-ID"] = request_id
            return response
        except Exception:
            logger.error("request failed", method = request.method, url = request.url.path)
            raise
        finally:
            # Unbind last, after both log lines have been emitted inside the
            # bound scope, and on the error path too so the id cannot leak into
            # whatever this task handles next.
            structlog.contextvars.unbind_contextvars("request_id")