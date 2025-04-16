from pydantic import BaseModel
from datetime import date

class ExchangeRate(BaseModel):
    id: int
    bank_id: int
    bank_name: str
    base_currency_id: str
    base_currency_name: str
    target_currency_id: str
    target_currency_name: str
    selling_rate: float
    buying_rate: float
    date: date

    class Config:
        from_attributes = True
