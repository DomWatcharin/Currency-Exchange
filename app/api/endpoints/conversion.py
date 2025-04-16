from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, aliased
from sqlalchemy.sql import func
from datetime import timedelta
from app.schemas.conversion import ConversionRequest, ConversionResponse
from app.core.security import get_current_user
from app.db import get_db, redis_client
from app.models import ExchangeRate, Currency
import json
from decimal import Decimal, ROUND_HALF_UP

router = APIRouter()

@router.post("/", response_model=ConversionResponse, description="Convert an amount from one currency to another. Uses the latest exchange rates to perform the conversion.")
async def convert_currency(request: ConversionRequest = Depends(ConversionRequest.as_form), current_user: str = Depends(get_current_user), db: Session = Depends(get_db)):
    cache_key = f"conversion:{request.from_currency}:{request.to_currency}:{request.amount}"
    cached_data = redis_client.get(cache_key)
    if cached_data:
        return json.loads(cached_data)

    # Use different aliases for the base_currency and target_currency joins
    base_currency_alias = aliased(Currency, name="base_currency")
    target_currency_alias = aliased(Currency, name="target_currency")
    
    # Check for exchange rate from from_currency to to_currency
    avg_rate = db.query(func.avg(ExchangeRate.selling_rate)).join(
        base_currency_alias, ExchangeRate.base_currency_id == base_currency_alias.id
    ).filter(
        base_currency_alias.code == request.from_currency
    ).join(
        target_currency_alias, ExchangeRate.target_currency_id == target_currency_alias.id
    ).filter(
        target_currency_alias.code == request.to_currency
    ).scalar()
    
    if avg_rate is None:
        # Check for exchange rate from to_currency to from_currency
        avg_rate = db.query(func.avg(ExchangeRate.buying_rate)).join(
            base_currency_alias, ExchangeRate.base_currency_id == base_currency_alias.id
        ).filter(
            base_currency_alias.code == request.to_currency
        ).join(
            target_currency_alias, ExchangeRate.target_currency_id == target_currency_alias.id
        ).filter(
            target_currency_alias.code == request.from_currency
        ).scalar()
        
        if avg_rate is None:
            raise HTTPException(status_code=404, detail="Exchange rate not found")
        
        # Perform conversion using the inverse rate
        converted_amount = request.amount / float(avg_rate)
    else:
        # Perform conversion using the direct rate
        converted_amount = request.amount * float(avg_rate)
    
    # Round the converted amount to 4 digits
    converted_amount = Decimal(converted_amount).quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)
    
    response = ConversionResponse(
        amount=request.amount,
        from_currency=request.from_currency,
        to_currency=request.to_currency,
        converted_amount=converted_amount,
    )

    # Convert Decimal objects to strings
    response_serializable = response.dict()
    response_serializable['converted_amount'] = str(response_serializable['converted_amount'])

    # Cache the response
    redis_client.setex(cache_key, timedelta(minutes=10), json.dumps(response_serializable))

    return response
