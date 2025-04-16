from pydantic import BaseModel
from fastapi import Form

class BankBase(BaseModel):
    name: str
    code: str

class BankCreate(BankBase):
    @classmethod
    def as_form(
        cls,
        name: str = Form(...),
        code: str = Form(...),
    ):
        return cls(
            name=name,
            code=code,
        )

class BankUpdate(BankBase):
    @classmethod
    def as_form(
        cls,
        name: str = Form(None),
        code: str = Form(None),
    ):
        return cls(
            name=name,
            code=code,
        )

class BankResponse(BankBase):
    id: int

    class Config:
        from_attributes = True
