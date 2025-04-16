from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, aliased
from sqlalchemy import desc, func
from typing import List
from datetime import timedelta
from app.schemas.exchange_rate import ExchangeRate
from app.core.security import get_current_user
from app.db import get_db, redis_client
from app.models import ExchangeRate as ExchangeRateModel, Bank, Currency
import json
from decimal import Decimal

router = APIRouter()

@router.get("/", response_model=List[ExchangeRate], description="Retrieve the latest exchange rates. Includes the latest selling and buying rates for each currency pair.")
async def get_exchange_rates(current_user: str = Depends(get_current_user), db: Session = Depends(get_db)):
    cache_key = "exchange_rates"
    cached_data = redis_client.get(cache_key)
    if cached_data:
        return json.loads(cached_data)

    try:
        subquery = db.query(
            ExchangeRateModel.base_currency_id,
            ExchangeRateModel.target_currency_id,
            func.max(ExchangeRateModel.date).label("latest_date")
        ).group_by(
            ExchangeRateModel.base_currency_id,
            ExchangeRateModel.target_currency_id
        ).subquery()

        base_currency_alias = aliased(Currency, name="base_currency")
        target_currency_alias = aliased(Currency, name="target_currency")

        exchange_rates = db.query(
            ExchangeRateModel.id,
            ExchangeRateModel.bank_id,
            Bank.name.label("bank_name"),
            ExchangeRateModel.base_currency_id,
            base_currency_alias.name.label("base_currency_name"),
            ExchangeRateModel.target_currency_id,
            target_currency_alias.name.label("target_currency_name"),
            ExchangeRateModel.selling_rate,
            ExchangeRateModel.buying_rate,
            ExchangeRateModel.date
        ).join(
            subquery,
            (ExchangeRateModel.base_currency_id == subquery.c.base_currency_id) &
            (ExchangeRateModel.target_currency_id == subquery.c.target_currency_id) &
            (ExchangeRateModel.date == subquery.c.latest_date)
        ).join(
            Bank, ExchangeRateModel.bank_id == Bank.id
        ).join(
            base_currency_alias, ExchangeRateModel.base_currency_id == base_currency_alias.id
        ).join(
            target_currency_alias, ExchangeRateModel.target_currency_id == target_currency_alias.id
        ).all()

        response = []
        for rate in exchange_rates:
            response.append(ExchangeRate(
                id=rate.id,
                bank_id=rate.bank_id,
                bank_name=rate.bank_name,
                base_currency_id=str(rate.base_currency_id),
                base_currency_name=rate.base_currency_name,
                target_currency_id=str(rate.target_currency_id),
                target_currency_name=rate.target_currency_name,
                selling_rate=str(rate.selling_rate),
                buying_rate=str(rate.buying_rate),
                date=rate.date.isoformat()
            ))

        # Convert each object in the list to a dictionary and ensure date serialization
        response_serializable = [
            {**r.dict(), "date": r.date.isoformat()} for r in response
        ]

        # Cache the response
        redis_client.setex(cache_key, timedelta(minutes=10), json.dumps(response_serializable))

        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
