from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.db import get_db, redis_client
from app.schemas.prediction import PredictionResponse
from app.models import ExchangeRate
from sklearn.linear_model import LinearRegression
import numpy as np
import json

router = APIRouter()

@router.get("/", response_model=PredictionResponse, description="Retrieve exchange rate predictions for the next 7 days. Uses historical exchange rate data to predict future rates.")
def get_predictions(db: Session = Depends(get_db)):
    cache_key = "predictions"
    cached_data = redis_client.get(cache_key)
    if cached_data:
        return json.loads(cached_data)

    # Fetch exchange rate data
    exchange_rates = db.query(ExchangeRate).order_by(ExchangeRate.date.desc()).limit(30).all()
    if not exchange_rates:
        raise HTTPException(status_code=404, detail="No exchange rate data found")

    # Prepare data for training
    dates = np.array([rate.date.toordinal() for rate in exchange_rates]).reshape(-1, 1)
    rates = np.array([rate.selling_rate for rate in exchange_rates])

    # Train the model
    model = LinearRegression()
    model.fit(dates, rates)

    # Predict for the next 7 days
    future_dates = np.array([datetime.now().date().toordinal() + i for i in range(1, 8)]).reshape(-1, 1)
    predictions = model.predict(future_dates)

    # Prepare response
    prediction_response = PredictionResponse(
        predictions=[
            {"date": datetime.fromordinal(int(date)).date().isoformat(), "predicted_rate": float(rate)}
            for date, rate in zip(future_dates.flatten(), predictions.flatten())
        ]
    )

    # Convert datetime.date objects to strings before caching
    prediction_response_serializable = prediction_response.dict()
    for prediction in prediction_response_serializable["predictions"]:
        prediction["date"] = str(prediction["date"])

    # Cache the response
    redis_client.setex(cache_key, timedelta(minutes=10), json.dumps(prediction_response_serializable))

    return prediction_response
