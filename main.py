"""
Phase 5: StockBot Orchestrator

This module serves as the master entry point for the StockBot MVP. It ties together
Data Ingestion, Strategy Engine, Portfolio Allocation, and Database APIs into a
single unified FastAPI application.
"""

import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

# Import our individual phases
from data_ingestion import fetch_historical_data, NIFTY_50_TICKERS
from strategy_engine import run_strategy
from portfolio_allocation import calculate_allocation

# Import the Database API module — single source of truth for DB engine/session/models
from db_api import router as db_router, get_db, Base, engine, PortfolioItem, SessionLocal


logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure our database tables are created on startup
    logging.info("Starting up StockBot Orchestrator; ensuring DB tables exist...")
    Base.metadata.create_all(bind=engine)
    yield
    logging.info("Shutting down StockBot Orchestrator.")


# Initialize the Master FastAPI App
app = FastAPI(
    title="StockBot MVP Orchestrator",
    description="Master API tying together data Fetching, Strategies, Allocation, and DB.",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Mount DB router at /db prefix — routes accessible at /db/trades/, /db/trades/{id} etc.
app.include_router(db_router, prefix="/db", tags=["Database"])


@app.get("/run-bot")
def run_bot(strategy: str = "golden_cross", db: Session = Depends(get_db)):
    """
    Main orchestration endpoint to run the StockBot pipeline.
    
    Pipeline Steps:
        A. Fetch historical data for Nifty 50.
        B. Run the chosen strategy to filter the `buy_list`.
        C. Calculate optimal portfolio allocations using Max Sharpe / Equal Weight.
        D. Fetch current portfolio status from the database.
    """
    try:
        # Validate strategy parameter early
        strategy = strategy.strip().lower()
        if strategy not in ["golden_cross", "alpha"]:
             raise ValueError(f"Unknown strategy: '{strategy}'. Use 'golden_cross' or 'alpha'.")

        logging.info("--- Step A: Fetching historical market data ---")
        historical_data = fetch_historical_data(NIFTY_50_TICKERS, period="1y")
        
        if historical_data.empty:
            raise RuntimeError("Historical data fetch returned empty DataFrame. Network or source failure.")

        logging.info(f"--- Step B: Running Strategy -> {strategy} ---")
        buy_list = run_strategy(historical_data, strategy=strategy)

        # ── Guard: strategy returned zero stocks ──────────────────────────────
        if not buy_list:
            logging.warning(f"Strategy '{strategy}' produced 0 buy signals. "
                            "Returning early with empty allocation.")
            return {
                "status": "no_signals",
                "strategy_used": strategy,
                "message": "No stocks passed the strategy filter today. No trades recommended.",
                "filtered_buy_list": [],
                "recommended_allocation": {},
                "current_portfolio_status": []
            }

        logging.info(f"--- Step C: Calculating Portfolio Allocations ---")
        allocations = calculate_allocation(buy_list, historical_data)

        # ── Guard: sanitize allocation values for NaN/Inf before Pydantic sees them ──
        import math
        allocations = {
            k: (v if math.isfinite(v) else 0.0)
            for k, v in allocations.items()
        }

        logging.info("--- Step D: Fetching current portfolio status from DB ---")
        # Querying the database to fetch manual trades/portfolio status
        db_trades = db.query(PortfolioItem).all()
        
        # Convert DB objects to a list of dicts for the JSON response
        current_portfolio_status = [
            {
                "id": t.id,
                "ticker": t.ticker,
                "buy_price": t.buy_price,
                "quantity": t.quantity,
                "buy_date": t.buy_date,
                "strategy_used": t.strategy_used
            } for t in db_trades
        ]

        # Construct and return the final clean JSON summary
        return {
            "status": "success",
            "strategy_used": strategy,
            "filtered_buy_list": buy_list,
            "recommended_allocation": allocations,
            "current_portfolio_status": current_portfolio_status
        }

    except ValueError as ve:
        # Expected value errors (like invalid strategy) — standard 400 Bad Request
        logging.error(f"Value Error during execution: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
        
    except Exception as e:
        # Unexpected errors (like pandas/PyPortfolioOpt failures) — 500 Internal Error
        logging.error(f"Bot execution failed: {type(e).__name__}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Bot orchestration failed during execution: {type(e).__name__} - {str(e)}"
        )


if __name__ == "__main__":
    # Start the orchestrator API instantly
    logging.info("Starting Master StockBot Orchestrator on port 8000...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
