from fastapi import Request, HTTPException, Depends
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from datetime import datetime, timedelta
import redis
import os
from app.core.security import get_current_user, oauth2_scheme
from app.db import get_db

class RateLimiterMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_requests: int, window: timedelta):
        super().__init__(app)
        self.max_requests = max_requests
        self.window = window
        self.redis_client = redis.Redis(
            host=os.getenv("REDIS_HOST", "redis"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            db=0,
            decode_responses=True
        )

    async def dispatch(self, request: Request, call_next):
        if request.url.path in ["/", "/docs", "/redoc", "/openapi.json", "/token"]:
            return await call_next(request)

        try:
            # Extract the token from the Authorization header
            token = await oauth2_scheme(request)
            db = next(get_db())
            current_user = await get_current_user(token, db)
        except HTTPException:
            return await call_next(request)

        user_id = current_user.id
        endpoint = request.url.path
        key = f"rate_limit:{user_id}:{endpoint}"
        current_time = datetime.utcnow()

        # Get the current request count and the first request timestamp
        request_count = self.redis_client.get(key)
        first_request_time = self.redis_client.get(f"{key}:first_request_time")

        if request_count is None:
            # Initialize the request count and the first request timestamp
            self.redis_client.set(key, 1, ex=self.window)
            self.redis_client.set(f"{key}:first_request_time", current_time.isoformat(), ex=self.window)
        else:
            request_count = int(request_count)
            first_request_time = datetime.fromisoformat(first_request_time)

            if current_time - first_request_time < self.window:
                if request_count >= self.max_requests:
                    retry_after = (first_request_time + self.window - current_time).total_seconds()
                    return JSONResponse(
                        status_code=429,
                        content={"detail": "Rate limit exceeded. Try again later."},
                        headers={"Retry-After": str(int(retry_after))}
                    )
                else:
                    self.redis_client.incr(key)
            else:
                # Reset the request count and the first request timestamp
                self.redis_client.set(key, 1, ex=self.window)
                self.redis_client.set(f"{key}:first_request_time", current_time.isoformat(), ex=self.window)

        response = await call_next(request)
        return response
