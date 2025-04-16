from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from jose import JWTError, jwt
from app.core.config import settings
from app.db import get_db
from app.models import User
from app.core.security import get_current_user

SECRET_KEY = settings.secret_key
ALGORITHM = "HS256"

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in ["/", "/docs", "/redoc", "/openapi.json", "/token"]:
            return await call_next(request)

        try:
            token = request.headers.get("Authorization").split(" ")[1]
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            username: str = payload.get("sub")
            if username is None:
                raise HTTPException(status_code=401, detail="Invalid token")
            
            db = next(get_db())
            user = db.query(User).filter(User.username == username).first()
            if user is None:
                raise HTTPException(status_code=401, detail="Invalid token")
            
            request.state.user = user
            request.state.jwt_payload = payload
        except JWTError:
            return JSONResponse(status_code=401, content={"detail": "Invalid token"})
        except Exception as e:
            return JSONResponse(status_code=401, content={"detail": str(e)})

        response = await call_next(request)
        return response
