from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, aliased
from sqlalchemy import select
from typing import List, Optional
from datetime import datetime, timedelta
from app.schemas.historical_rate import HistoricalRate
from app.core.security import get_current_user
from app.db import get_db, redis_client
from app.models import ExchangeRate, Bank, Currency
import json
from decimal import Decimal

router = APIRouter()

@router.get("/", response_model=List[HistoricalRate], description="Retrieve historical exchange rates for the last 30 days. Optionally filter by bank, base currency, and target currency.")
async def get_historical_rates(
    bank_id: Optional[int] = Query(None, description="Filter by bank ID"),
    base_currency_id: Optional[int] = Query(None, description="Filter by base currency ID"),
    target_currency_id: Optional[int] = Query(None, description="Filter by target currency ID"),
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    cache_key = f"historical_rates:{bank_id}:{base_currency_id}:{target_currency_id}"
    cached_data = redis_client.get(cache_key)
    if cached_data:
        return json.loads(cached_data)

    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=30)
    
    base_currency_alias = aliased(Currency, name="base_currency")
    target_currency_alias = aliased(Currency, name="target_currency")
    
    query = db.query(
        ExchangeRate.id,
        ExchangeRate.bank_id,
        Bank.name.label("bank_name"),
        ExchangeRate.base_currency_id,
        base_currency_alias.name.label("base_currency_name"),
        ExchangeRate.target_currency_id,
        target_currency_alias.name.label("target_currency_name"),
        ExchangeRate.selling_rate,
        ExchangeRate.buying_rate,
        ExchangeRate.date
        ).join(Bank, ExchangeRate.bank_id == Bank.id) \
            .join(base_currency_alias, ExchangeRate.base_currency_id == base_currency_alias.id) \
            .join(target_currency_alias, ExchangeRate.target_currency_id == target_currency_alias.id) \
            .filter(
            ExchangeRate.date >= start_date,
            ExchangeRate.date <= end_date
        )
    
    if bank_id is not None:
        query = query.filter(ExchangeRate.bank_id == bank_id)
    if base_currency_id is not None:
        query = query.filter(ExchangeRate.base_currency_id == base_currency_id)
    if target_currency_id is not None:
        query = query.filter(ExchangeRate.target_currency_id == target_currency_id)
    
    rates = query.all()
    
    if not rates:
        raise HTTPException(status_code=404, detail="No exchange rates found for the given criteria")
    
    # Convert Decimal and datetime.date objects to strings
    rates_serializable = [
        {
            **rate._asdict(),
            "selling_rate": str(rate.selling_rate),
            "buying_rate": str(rate.buying_rate),
            "date": rate.date.isoformat()
        }
        for rate in rates
    ]

    # Cache the response
    redis_client.setex(cache_key, timedelta(minutes=10), json.dumps(rates_serializable))

    return rates
