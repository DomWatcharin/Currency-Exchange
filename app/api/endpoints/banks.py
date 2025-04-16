from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import timedelta 
from app.core.security import require_admin
from app.db import get_db, redis_client
from app.models import Bank, User 
from app.schemas.bank import BankCreate, BankUpdate, BankResponse
import json

router = APIRouter()

@router.get("/", response_model=List[BankResponse], description="Retrieve a list of all supported banks from the database. If the data is cached, it will be retrieved from the cache instead.")
async def get_banks(db: Session = Depends(get_db)):
    cache_key = "banks"
    cached_data = redis_client.get(cache_key)
    if cached_data:
        return json.loads(cached_data)

    banks = db.query(Bank).all()

    # Convert InstanceState objects to dictionaries
    banks_serializable = [bank.__dict__ for bank in banks]
    for bank in banks_serializable:
        bank.pop('_sa_instance_state', None)

    # Cache the response
    redis_client.setex(cache_key, timedelta(minutes=10), json.dumps(banks_serializable))

    return banks

@router.post("/", response_model=BankResponse, description="Create a new bank in the database. Requires admin privileges.")
async def create_bank(bank: BankCreate = Depends(BankCreate.as_form), db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    db_bank = db.query(Bank).filter(Bank.code == bank.code).first()
    if db_bank:
        raise HTTPException(status_code=400, detail="Bank code already registered")
    new_bank = Bank(name=bank.name, code=bank.code)
    db.add(new_bank)
    db.commit()
    db.refresh(new_bank)
    return new_bank

@router.put("/{bank_id}", response_model=BankResponse, description="Update an existing bank in the database. Requires admin privileges.")
async def update_bank(bank_id: int, bank: BankUpdate = Depends(BankUpdate.as_form), db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    db_bank = db.query(Bank).filter(Bank.id == bank_id).first()
    if not db_bank:
        raise HTTPException(status_code=404, detail="Bank not found")
    for key, value in bank.dict(exclude_unset=True).items():
        setattr(db_bank, key, value)
    db.commit()
    db.refresh(db_bank)
    return db_bank

@router.delete("/{bank_id}", description="Delete an existing bank from the database. Requires admin privileges.")
async def delete_bank(bank_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    db_bank = db.query(Bank).filter(Bank.id == bank_id).first()
    if not db_bank:
        raise HTTPException(status_code=404, detail="Bank not found")
    db.delete(db_bank)
    db.commit()
    return {"message": "Bank deleted"}
