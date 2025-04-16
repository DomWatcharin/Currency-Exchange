from pydantic_settings import BaseSettings
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    """
    Settings class to load environment variables using Pydantic BaseSettings.
    """
    postgres_user: str
    postgres_password: str
    postgres_db: str
    postgres_host: str = os.getenv('POSTGRES_HOST', 'db')
    postgres_port: int
    redis_host: str
    redis_port: int
    api_port: int
    admin_api_key: str
    user_api_key: str
    airflow_fernet_key: str
    airflow_port: int
    streamlit_port: int
    secret_key: str 
    email: str
    sender_email: str
    receiver_email: str

    class Config:
        env_file = f".env.{os.getenv('ENV', 'development')}"
        extra = "allow"

settings = Settings()

# Access the loaded settings
current_env = os.getenv('ENV', 'development')
logger.info(f"Current environment: {current_env}")

# Check database connection
def check_db_connection(host):
    try:
        import psycopg2
        conn = psycopg2.connect(
            dbname=settings.postgres_db,
            user=settings.postgres_user,
            password=settings.postgres_password,
            host=host,
            port=settings.postgres_port
        )
        conn.close()
        logger.info(f"Connected to database at {host}")
        return True
    except Exception as e:
        logger.warning(f"Failed to connect to database at {host}: {e}")
        return False

if not check_db_connection(settings.postgres_host):
    settings.postgres_host = 'localhost'
    check_db_connection(settings.postgres_host)
