from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


class PortfolioCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    starting_cash: float = Field(gt=0)


class PortfolioOut(BaseModel):
    id: int
    name: str
    starting_cash: float
    created_at: datetime

    class Config:
        from_attributes = True


class TransactionCreate(BaseModel):
    symbol: str = Field(min_length=1, max_length=12)
    side: str = Field(pattern="^(BUY|SELL)$")
    shares: float = Field(gt=0)
    # If omitted, the current market price is used
    price: Optional[float] = Field(default=None, gt=0)
    trade_date: Optional[date] = None


class TransactionOut(BaseModel):
    id: int
    symbol: str
    side: str
    shares: float
    price: float
    trade_date: date

    class Config:
        from_attributes = True
