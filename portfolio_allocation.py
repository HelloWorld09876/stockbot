"""
Phase 3: Portfolio Allocation

This module is responsible for determining optimal capital allocation weights
for a filtered list of Nifty 50 "Buy" stocks.

Two allocation modes are supported:
    1. Max Sharpe Ratio (via PyPortfolioOpt) — used when len(buy_list) >= 3 and data is valid.
    2. Equal Weighting fallback — used when PyPortfolioOpt fails or the buy_list is too small.

Input contract:
    buy_list        (List[str])     : Tickers that passed the strategy filter (e.g., ['RELIANCE.NS', 'TCS.NS']).
    historical_data (pd.DataFrame)  : Full daily Close prices. Index = DatetimeIndex, columns = tickers.
"""

import logging
from typing import List, Dict

import pandas as pd
from pypfopt import expected_returns, risk_models, EfficientFrontier
from pypfopt.exceptions import OptimizationError

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def _equal_weight(buy_list: List[str]) -> Dict[str, float]:
    """
    Compute equal-weight allocation for the given tickers.

    Args:
        buy_list (List[str]): List of ticker symbols to allocate equally.

    Returns:
        Dict[str, float]: Equal allocation dictionary summing to 1.0.
    """
    weight = round(1.0 / len(buy_list), 6)
    return {ticker: weight for ticker in buy_list}


def calculate_allocation(
    buy_list: List[str],
    historical_data: pd.DataFrame,
) -> Dict[str, float]:
    """
    Calculate optimal portfolio weights for the given buy list.

    Attempts Max Sharpe Ratio optimisation via PyPortfolioOpt.
    Automatically falls back to Equal Weighting if:
        - ``len(buy_list) < 3`` (too few stocks for a meaningful frontier), or
        - PyPortfolioOpt raises any exception (singular covariance matrix, etc.).

    Args:
        buy_list (List[str]): Tickers that passed the strategy filter.
        historical_data (pd.DataFrame): Full daily Close prices with tickers as columns.

    Returns:
        Dict[str, float]: Allocation weights {ticker: weight} summing to ~1.0.
    """
    if not buy_list:
        logging.warning("buy_list is empty — returning empty allocation.")
        return {}

    # Step 1 — filter historical_data to only the buy_list tickers
    available = [t for t in buy_list if t in historical_data.columns]
    missing = set(buy_list) - set(available)
    if missing:
        logging.warning(f"Tickers not found in historical_data and will be skipped: {missing}")

    if not available:
        logging.error("None of the buy_list tickers are in historical_data.")
        return {}

    prices = historical_data[available].dropna(how="all")

    # Step 2b — Date-alignment guard: drop tickers with fewer than 200 rows of data.
    # A stock with only 3 months of history will skew means and covariance estimates.
    MIN_ROWS = 200
    sufficient = [col for col in prices.columns if prices[col].count() >= MIN_ROWS]
    culled = set(prices.columns) - set(sufficient)
    if culled:
        logging.warning(
            f"Dropped tickers with insufficient history (< {MIN_ROWS} rows): {culled}. "
            f"Equal Weighting will be used if fewer than 3 tickers remain."
        )
    available = sufficient
    prices = prices[available]

    if not available:
        logging.error("No tickers have sufficient history for portfolio optimisation.")
        return {}
    if len(available) < 3:
        logging.warning(
            f"Only {len(available)} stock(s) in buy_list — skipping Max Sharpe, using Equal Weighting."
        )
        return _equal_weight(available)

    # Step 3 — attempt Max Sharpe via PyPortfolioOpt
    try:
        mu = expected_returns.mean_historical_return(prices)
        S = risk_models.sample_cov(prices)

        ef = EfficientFrontier(mu, S)
        ef.max_sharpe()

        # Clean tiny weights (< 1%) to zero; renormalise the remainder
        cleaned_weights: Dict[str, float] = ef.clean_weights(cutoff=0.01, rounding=6)

        # Sanity check: if all weights were zeroed out, fall through to equal weight
        total = sum(cleaned_weights.values())
        if total == 0:
            raise ValueError("All cleaned weights were zeroed out — falling back.")

        logging.info("Max Sharpe allocation computed successfully.")

        # Sanitize: replace any NaN or Inf weights with 0 to prevent Pydantic failures
        import math
        safe_weights = {
            k: (v if math.isfinite(v) else 0.0)
            for k, v in cleaned_weights.items()
        }
        return {k: v for k, v in safe_weights.items() if v > 0}

    except (OptimizationError, ValueError, Exception) as exc:
        logging.warning(
            f"PyPortfolioOpt optimisation failed ({type(exc).__name__}: {exc}). "
            f"Falling back to Equal Weighting."
        )
        return _equal_weight(available)


if __name__ == "__main__":
    import numpy as np

    np.random.seed(7)
    start_date = pd.Timestamp.today().normalize() - pd.offsets.BDay(252)
    dates = pd.date_range(start=start_date, periods=252, freq="B")

    ALL_TICKERS = ["RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS"]
    # Give each ticker a distinct mean return so the optimizer spreads weight across multiple stocks
    returns = np.column_stack([
        np.random.randn(252) * 0.8 + 0.05,   # RELIANCE — moderate drift
        np.random.randn(252) * 1.5 + 0.02,   # TCS      — higher vol, low drift
        np.random.randn(252) * 1.0 + 0.08,   # INFY     — high drift
        np.random.randn(252) * 0.6 + 0.03,   # HDFCBANK — low vol
    ])
    price_data = pd.DataFrame(
        100 + np.cumsum(returns, axis=0),
        index=dates,
        columns=ALL_TICKERS,
    )

    # --- Test 1: Max Sharpe with 4 stocks ---
    print("=== Test 1: Max Sharpe Ratio (4 stocks) ===")
    buy_list_4 = ALL_TICKERS
    weights_sharpe = calculate_allocation(buy_list_4, price_data)
    print(f"Allocated tickers : {list(weights_sharpe.keys())}")
    print(f"Weights           : {weights_sharpe}")
    print(f"Sum of weights    : {sum(weights_sharpe.values()):.6f}\n")

    # --- Test 2: Equal Weighting fallback (only 1 stock) ---
    print("=== Test 2: Equal Weighting Fallback (1 stock) ===")
    buy_list_1 = ["TCS.NS"]
    weights_eq = calculate_allocation(buy_list_1, price_data)
    print(f"Allocated tickers : {list(weights_eq.keys())}")
    print(f"Weights           : {weights_eq}")
    print(f"Sum of weights    : {sum(weights_eq.values()):.6f}\n")

    # --- Test 3: Equal Weighting fallback (ticker missing from historical_data) ---
    print("=== Test 3: Equal Weighting Fallback (missing ticker) ===")
    buy_list_bad = ["RELIANCE.NS", "UNKNOWN.NS"]
    weights_partial = calculate_allocation(buy_list_bad, price_data)
    print(f"Allocated tickers : {list(weights_partial.keys())}")
    print(f"Weights           : {weights_partial}")
    print(f"Sum of weights    : {sum(weights_partial.values()):.6f}")
