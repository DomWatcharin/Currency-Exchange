from pydantic import BaseModel
from fastapi import Form

class CurrencyBase(BaseModel):
    code: str
    name: str

class CurrencyCreate(CurrencyBase):
    @classmethod
    def as_form(
        cls,
        code: str = Form(...),
        name: str = Form(...),
    ):
        return cls(
            code=code,
            name=name,
        )

class CurrencyUpdate(CurrencyBase):
    @classmethod
    def as_form(
        cls,
        code: str = Form(None),
        name: str = Form(None),
    ):
        return cls(
            code=code,
            name=name,
        )

class CurrencyResponse(CurrencyBase):
    id: int

    class Config:
        from_attributes = True
