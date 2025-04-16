from pydantic import BaseModel
from datetime import date

class HistoricalRate(BaseModel):
    id: int
    bank_id: int
    bank_name: str  
    base_currency_id: int
    base_currency_name: str  
    target_currency_id: int
    target_currency_name: str 
    selling_rate: float
    buying_rate: float
    date: date

    class Config:
        from_attributes = True
