from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field, model_validator


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
    # Provide EITHER shares OR amount (USD). With amount, fractional shares
    # are derived from the execution price.
    shares: Optional[float] = Field(default=None, gt=0)
    amount: Optional[float] = Field(default=None, gt=0)
    # If omitted, price is looked up: historical close for backdated trades,
    # otherwise the latest quote.
    price: Optional[float] = Field(default=None, gt=0)
    trade_date: Optional[date] = None

    @model_validator(mode="after")
    def shares_or_amount(self):
        if (self.shares is None) == (self.amount is None):
            raise ValueError("Provide exactly one of 'shares' or 'amount'")
        return self


class DepositCreate(BaseModel):
    amount: float = Field(gt=0)
    flow_date: Optional[date] = None


class TransactionOut(BaseModel):
    id: int
    symbol: str
    side: str
    shares: float
    price: float
    trade_date: date

    class Config:
        from_attributes = True
