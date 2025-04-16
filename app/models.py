from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, DECIMAL, Date, TIMESTAMP, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    role = Column(String(10), nullable=False)
    active = Column(Boolean, default=True)  
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

class Bank(Base):
    __tablename__ = "banks"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    code = Column(String(10), unique=True, nullable=False)
    exchange_rates = relationship("ExchangeRate", back_populates="bank")  

class Currency(Base):
    __tablename__ = "currencies"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(3), unique=True, nullable=False)
    name = Column(String(50), nullable=False)

class ExchangeRate(Base):
    __tablename__ = "exchange_rates"

    id = Column(Integer, primary_key=True, index=True)
    bank_id = Column(Integer, ForeignKey("banks.id"))
    base_currency_id = Column(Integer, ForeignKey("currencies.id"))
    target_currency_id = Column(Integer, ForeignKey("currencies.id"))
    selling_rate = Column(DECIMAL(10, 6), nullable=False)
    buying_rate = Column(DECIMAL(10, 6), nullable=False)
    date = Column(Date, nullable=False)  
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    bank = relationship("Bank", back_populates="exchange_rates")
    base_currency = relationship("Currency", foreign_keys=[base_currency_id])
    target_currency = relationship("Currency", foreign_keys=[target_currency_id])
