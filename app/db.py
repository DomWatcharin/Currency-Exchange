from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings
import redis

# Define the Base object
Base = declarative_base()

# PostgreSQL connection
DATABASE_URL = f"postgresql://{settings.postgres_user}:{settings.postgres_password}@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
engine = create_engine(
    DATABASE_URL,
    pool_size=50,  # Increase the pool size
    max_overflow=20,  # Increase the max overflow
    pool_timeout=30,  # Increase the pool timeout
    pool_recycle=1800  # Recycle connections after 30 minutes
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Redis connection
redis_client = redis.Redis(
    host=settings.redis_host,
    port=settings.redis_port,
    db=0,
    decode_responses=True
)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
