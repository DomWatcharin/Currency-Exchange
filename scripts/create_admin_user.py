import secrets
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError, IntegrityError
from app.db import engine, Base, get_db
from app.models import User
from app.core.security import get_password_hash

# Generate a secure API key for the admin user
admin_api_key = secrets.token_urlsafe(32)

# Create the database tables
try:
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully.")
except OperationalError as e:
    print(f"Error creating database tables: {e}")

# Create an admin user
def create_admin_user():
    try:
        db = next(get_db())
        # Check if admin user already exists
        existing_user = db.query(User).filter(User.username == "admin").first()
        if existing_user:
            print("Admin user already exists.")
            return

        hashed_password = get_password_hash("password")
        admin_user = User(
            username="admin",
            hashed_password=hashed_password,
            name="Admin",
            email="watcharin.phoemphon@gmail.com",
            role="admin"
        )
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        print(f"Admin user created with username: {admin_user.username}")
    except OperationalError as e:
        print(f"Database connection error: {e}")
    except IntegrityError as e:
        print(f"Integrity error: {e}")
    except Exception as e:
        print(f"Error creating admin user: {e}")

if __name__ == "__main__":
    create_admin_user()
