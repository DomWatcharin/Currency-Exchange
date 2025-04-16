from pydantic import BaseModel
from datetime import date
from typing import List

class Prediction(BaseModel):
    date: date
    predicted_rate: float

class PredictionResponse(BaseModel):
    predictions: List[Prediction]
