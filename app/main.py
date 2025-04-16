from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from app.api.endpoints import exchange_rates, banks, currencies, conversion, historical_rates, users, predictions  # Import predictions endpoint
from app.middleware.rate_limiter import RateLimiterMiddleware
from app.middleware.auth_middleware import AuthMiddleware  # Import AuthMiddleware
from app.core.config import settings
from app.core.security import authenticate_user, create_access_token, get_current_user, ACCESS_TOKEN_EXPIRE_MINUTES
from app.schemas.user import Token  # Import Token schema
from app.db import get_db
import os
import logging
from fastapi.middleware.cors import CORSMiddleware

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Currency Exchange API",
    description="API documentation for Currency Exchange API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add rate limiting middleware
app.add_middleware(RateLimiterMiddleware, max_requests=100, window=timedelta(hours=1))

# Add authentication middleware
app.add_middleware(AuthMiddleware)

# Include routers for different endpoints
app.include_router(exchange_rates.router, prefix="/exchange-rates", tags=["exchange-rates"], dependencies=[Depends(get_current_user)])
app.include_router(banks.router, prefix="/banks", tags=["banks"], dependencies=[Depends(get_current_user)])
app.include_router(currencies.router, prefix="/currencies", tags=["currencies"], dependencies=[Depends(get_current_user)])
app.include_router(conversion.router, prefix="/conversion", tags=["conversion"], dependencies=[Depends(get_current_user)]) 
app.include_router(historical_rates.router, prefix="/historical-rates", tags=["historical-rates"], dependencies=[Depends(get_current_user)])
app.include_router(users.router, prefix="/users", tags=["users"], dependencies=[Depends(get_current_user)])
app.include_router(predictions.router, prefix="/predictions", tags=["predictions"]) 

# Public route (No API key required)
@app.get("/", include_in_schema=False)
def read_root():
    return {"message": "Welcome to FastAPI!"}

@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}
