from pydantic import BaseModel
from fastapi import Form

class ConversionRequest(BaseModel):
    amount: float
    from_currency: str
    to_currency: str

    @classmethod
    def as_form(
        cls,
        amount: float = Form(...),
        from_currency: str = Form(...),
        to_currency: str = Form(...),
    ):
        return cls(
            amount=amount,
            from_currency=from_currency,
            to_currency=to_currency,
        )

class ConversionResponse(BaseModel):
    amount: float
    from_currency: str
    to_currency: str
    converted_amount: float

    class Config:
        from_attributes = True
