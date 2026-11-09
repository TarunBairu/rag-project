import time
from collections import defaultdict
from typing import Dict, List
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.config.settings import get_settings

settings = get_settings()


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """Sliding-window IP-based rate limiter middleware."""

    def __init__(self, app, max_requests: int = 60, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.clients: Dict[str, List[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        # Allow internal health checks to bypass rate limit
        if request.url.path.startswith("/health"):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        window_start = now - self.window_seconds

        # Prune older timestamps
        self.clients[client_ip] = [ts for ts in self.clients[client_ip] if ts > window_start]

        if len(self.clients[client_ip]) >= self.max_requests:
            retry_after = int(self.clients[client_ip][0] + self.window_seconds - now)
            req_id = getattr(request.state, "request_id", "unknown")
            return JSONResponse(
                status_code=429,
                content={
                    "success": False,
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": f"Rate limit exceeded. Maximum {self.max_requests} requests per {self.window_seconds}s.",
                        "detail": f"Try again in {retry_after} seconds.",
                    },
                    "request_id": req_id,
                },
                headers={
                    "Retry-After": str(max(1, retry_after)),
                    "X-RateLimit-Limit": str(self.max_requests),
                    "X-RateLimit-Remaining": "0",
                },
            )

        self.clients[client_ip].append(now)
        response = await call_next(request)
        remaining = self.max_requests - len(self.clients[client_ip])
        response.headers["X-RateLimit-Limit"] = str(self.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(max(0, remaining))
        return response
