from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import timedelta
from app.core.security import require_admin
from app.db import get_db, redis_client
from app.models import Currency, User
from app.schemas.currency import CurrencyCreate, CurrencyUpdate, CurrencyResponse
import json

router = APIRouter()

@router.get("/", response_model=List[CurrencyResponse], description="Retrieve a list of all supported currencies.")
async def get_currencies(db: Session = Depends(get_db)):
    cache_key = "currencies"
    cached_data = redis_client.get(cache_key)
    if cached_data:
        return json.loads(cached_data)

    currencies = db.query(Currency).all()

    # Convert InstanceState objects to dictionaries
    currencies_serializable = [currency.__dict__ for currency in currencies]
    for currency in currencies_serializable:
        currency.pop('_sa_instance_state', None)

    # Cache the response
    redis_client.setex(cache_key, timedelta(minutes=10), json.dumps(currencies_serializable))

    return currencies

@router.post("/", response_model=CurrencyResponse, description="Create a new currency. Requires admin role.")
async def create_currency(currency: CurrencyCreate = Depends(CurrencyCreate.as_form), db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    db_currency = db.query(Currency).filter(Currency.code == currency.code).first()
    if db_currency:
        raise HTTPException(status_code=400, detail="Currency code already registered")
    new_currency = Currency(code=currency.code, name=currency.name)
    db.add(new_currency)
    db.commit()
    db.refresh(new_currency)
    return new_currency

@router.put("/{currency_id}", response_model=CurrencyResponse, description="Update an existing currency. Requires admin role.")
async def update_currency(currency_id: int, currency: CurrencyUpdate = Depends(CurrencyUpdate.as_form), db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    db_currency = db.query(Currency).filter(Currency.id == currency_id).first()
    if not db_currency:
        raise HTTPException(status_code=404, detail="Currency not found")
    for key, value in currency.dict(exclude_unset=True).items():
        setattr(db_currency, key, value)
    db.commit()
    db.refresh(db_currency)
    return db_currency

@router.delete("/{currency_id}", description="Delete an existing currency. Requires admin role.")
async def delete_currency(currency_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    db_currency = db.query(Currency).filter(Currency.id == currency_id).first()
    if not db_currency:
        raise HTTPException(status_code=404, detail="Currency not found")
    db.delete(db_currency)
    db.commit()
    return {"message": "Currency deleted"}
