from pydantic import BaseModel
from typing import Optional
from fastapi import Form

class UserBase(BaseModel):
    username: str
    name: str
    email: str
    role: str
    active: bool

class UserCreate(UserBase):
    password: str

    @classmethod
    def as_form(
        cls,
        username: str = Form(...),
        name: str = Form(...),
        email: str = Form(...),
        role: str = Form(...),
        active: bool = Form(...),
        password: str = Form(...),
    ):
        return cls(
            username=username,
            name=name,
            email=email,
            role=role,
            active=active,
            password=password,
        )

class UserUpdate(BaseModel):
    username: Optional[str]
    password: Optional[str]
    name: Optional[str]
    email: Optional[str]
    role: Optional[str]
    active: Optional[bool]

    @classmethod
    def as_form(
        cls,
        username: Optional[str] = Form(None),
        password: Optional[str] = Form(None),
        name: Optional[str] = Form(None),
        email: Optional[str] = Form(None),
        role: Optional[str] = Form(None),
        active: Optional[bool] = Form(None),
    ):
        return cls(
            username=username,
            password=password,
            name=name,
            email=email,
            role=role,
            active=active,
        )

class UserResponse(UserBase):
    id: int

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None