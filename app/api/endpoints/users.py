from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.core.security import require_role, get_password_hash, get_current_user
from app.db import get_db
from app.models import User
from app.schemas.user import UserCreate, UserUpdate, UserResponse

router = APIRouter()

@router.get("/", response_model=List[UserResponse], description="Retrieve a list of all users. Requires admin role.")
async def get_users(api_key: str = Depends(require_role("admin")), db: Session = Depends(get_db)):
    users = db.query(User).all()
    return users

@router.post("/", response_model=UserResponse, description="Create a new user. Requires admin role.")
async def create_user(user: UserCreate = Depends(UserCreate.as_form), api_key: str = Depends(require_role("admin")), db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    hashed_password = get_password_hash(user.password)
    new_user = User(username=user.username, hashed_password=hashed_password, name=user.name, email=user.email, role=user.role)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.put("/{user_id}", response_model=UserResponse, description="Update an existing user. Requires admin role.")
async def update_user(user_id: int, user: UserUpdate = Depends(UserUpdate.as_form), api_key: str = Depends(require_role("admin")), db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.password:
        user.password = get_password_hash(user.password)
    for key, value in user.dict(exclude_unset=True).items():
        setattr(db_user, key, value)
    db.commit()
    db.refresh(db_user)
    return db_user

@router.delete("/{user_id}", response_model=dict, description="Delete an existing user. Requires admin role.")
async def delete_user(user_id: int, api_key: str = Depends(require_role("admin")), db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(db_user)
    db.commit()
    return {"message": "User deleted successfully"}

@router.get("/me", response_model=UserResponse, description="Retrieve the current user's data.")
async def get_current_user_data(current_user: User = Depends(get_current_user)):
    return current_user
