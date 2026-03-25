"""
Phase 4: Database and API MVP
This module handles SQLite database setup using SQLAlchemy and exposes endpoints using FastAPI.
"""

from contextlib import asynccontextmanager
from typing import List

import uvicorn
from fastapi import FastAPI, APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.orm import declarative_base

# ==========================================
# 1. DATABASE SETUP (SQLAlchemy)
# ==========================================

SQLALCHEMY_DATABASE_URL = "sqlite:///./stockbot_mvp.db"

# connect_args={"check_same_thread": False} is needed for SQLite in FastAPI
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Dependency to get a DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ==========================================
# 2. THE SCHEMA (SQLAlchemy Models)
# ==========================================

class PortfolioItem(Base):
    __tablename__ = "portfolio_items"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, index=True)
    buy_price = Column(Float)
    quantity = Column(Integer)
    buy_date = Column(String)  # Using String for simplicity in MVP, could use DateTime
    strategy_used = Column(String)


# ==========================================
# 3. PYDANTIC SCHEMAS (V2 Syntax)
# ==========================================

class TradeCreate(BaseModel):
    ticker: str
    buy_price: float
    quantity: int
    buy_date: str
    strategy_used: str

class TradeResponse(TradeCreate):
    id: int
    
    # Pydantic V2 syntax for ORM mode
    model_config = ConfigDict(from_attributes=True)


# ==========================================
# 4. APIROUTER (used by main.py via include_router)
# ==========================================

# All trade endpoints live on this router so main.py can include them
# into its Swagger UI with a single include_router() call.
router = APIRouter()

@router.post("/trades/", response_model=TradeResponse)
def create_trade(trade: TradeCreate, db: Session = Depends(get_db)):
    db_item = PortfolioItem(**trade.model_dump())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@router.get("/trades/", response_model=List[TradeResponse])
def get_trades(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    trades = db.query(PortfolioItem).offset(skip).limit(limit).all()
    return trades

@router.delete("/trades/{trade_id}")
def delete_trade(trade_id: int, db: Session = Depends(get_db)):
    db_item = db.query(PortfolioItem).filter(PortfolioItem.id == trade_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Trade not found")
    db.delete(db_item)
    db.commit()
    return {"message": f"Trade {trade_id} deleted successfully"}


# ==========================================
# 5. STANDALONE APP (for direct runs only)
# ==========================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(title="StockBot MVP API", lifespan=lifespan)
app.include_router(router)


if __name__ == "__main__":
    # Start the API server
    uvicorn.run("db_api:app", host="0.0.0.0", port=8000, reload=False)
