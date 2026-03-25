"""
Phase 2: Strategy Engine

This module implements two quantitative trading strategies for the Nifty 50 StockBot:

    - Strategy A: Golden Cross — based on 50-day vs 200-day SMA crossover.
    - Strategy B: Nifty Alpha / Momentum — based on 6-month (126-day) price momentum.

Input contract:
    historical_data (pd.DataFrame): Index = Dates, Columns = ticker symbols, Values = daily Close prices.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Union


def golden_cross_strategy(historical_data: pd.DataFrame) -> List[str]:
    """
    Strategy A: Golden Cross.

    Flags a stock as a "Buy" if its current 50-day SMA is strictly greater than
    its current 200-day SMA. Stocks with insufficient data for the 200-day SMA
    are silently dropped.

    Args:
        historical_data (pd.DataFrame): DataFrame of daily Close prices.
            Index = DatetimeIndex, columns = ticker symbols.

    Returns:
        List[str]: Tickers that currently satisfy the Golden Cross "Buy" condition.
    """
    # Vectorized rolling SMAs across all tickers simultaneously
    sma_50 = historical_data.rolling(window=50).mean()
    sma_200 = historical_data.rolling(window=200).mean()

    # Grab the most recent row for each SMA (the current values)
    latest_sma_50 = sma_50.iloc[-1]
    latest_sma_200 = sma_200.iloc[-1]

    # Drop any tickers that couldn't form a 200-day SMA (NaN values)
    valid = latest_sma_200.dropna().index

    # Apply the Golden Cross condition vectorized
    buy_signal = latest_sma_50[valid] > latest_sma_200[valid]

    return buy_signal[buy_signal].index.tolist()


def alpha_strategy(historical_data: pd.DataFrame, top_n: int = 10) -> List[str]:
    """
    Strategy B: Nifty Alpha / Momentum.

    Calculates the 6-month (126 trading days) price momentum for each ticker,
    ranks stocks in descending order of momentum, and returns the top N.

    Momentum formula: (Current Price - Price 126 days ago) / Price 126 days ago

    Args:
        historical_data (pd.DataFrame): DataFrame of daily Close prices.
            Index = DatetimeIndex, columns = ticker symbols.
        top_n (int): Number of top momentum stocks to return (default: 10).

    Returns:
        List[str]: Top-N tickers ranked by descending 6-month momentum.
    """
    LOOKBACK = 126  # ~6 months of trading days

    # Vectorized momentum calculation across all tickers
    current_prices = historical_data.iloc[-1]
    past_prices = historical_data.iloc[-LOOKBACK - 1] if len(historical_data) > LOOKBACK else None

    if past_prices is None:
        raise ValueError(
            f"Insufficient data: need at least {LOOKBACK + 1} rows to compute momentum, "
            f"got {len(historical_data)}."
        )

    momentum = (current_prices - past_prices) / past_prices

    # Drop tickers with NaN momentum (not enough history)
    momentum = momentum.dropna()

    # Rank descending and return top N tickers
    top_tickers = momentum.nlargest(top_n)
    return top_tickers.index.tolist()


def run_strategy(
    historical_data: pd.DataFrame,
    strategy: str = "golden_cross",
) -> List[str]:
    """
    Controller function — dispatches to the appropriate strategy.

    Args:
        historical_data (pd.DataFrame): DataFrame of daily Close prices.
            Index = DatetimeIndex, columns = ticker symbols.
        strategy (str): Strategy name — either "golden_cross" or "alpha".

    Returns:
        List[str]: Filtered list of "Buy" tickers as determined by the chosen strategy.

    Raises:
        ValueError: If an unsupported strategy name is provided.
    """
    strategy = strategy.strip().lower()

    if strategy == "golden_cross":
        return golden_cross_strategy(historical_data)
    elif strategy == "alpha":
        return alpha_strategy(historical_data)
    else:
        raise ValueError(
            f"Unsupported strategy: '{strategy}'. "
            f"Valid options are: 'golden_cross', 'alpha'."
        )


if __name__ == "__main__":
    import numpy as np

    # --- Generate dummy price data ---
    np.random.seed(42)
    start_date = pd.Timestamp.today().normalize() - pd.offsets.BDay(250)
    dates = pd.date_range(start=start_date, periods=250, freq="B")
    tickers = ["RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "SBIN.NS"]

    # Simulate realistic trending price paths using cumulative random walks
    price_data = pd.DataFrame(
        100 + np.cumsum(np.random.randn(250, 5) * 1.5, axis=0),
        index=dates,
        columns=tickers,
    )

    print("=== Dummy Historical Data (last 5 rows) ===")
    print(price_data.tail(), "\n")

    # --- Test Golden Cross Strategy ---
    print("=== Testing Strategy: Golden Cross ===")
    gc_result = run_strategy(price_data, strategy="golden_cross")
    print(f"Golden Cross 'Buy' tickers: {gc_result}\n")

    # --- Test Alpha / Momentum Strategy ---
    print("=== Testing Strategy: Alpha (Momentum) ===")
    alpha_result = run_strategy(price_data, strategy="alpha")
    print(f"Top Momentum tickers: {alpha_result}\n")

    # --- Test ValueError for bad strategy ---
    print("=== Testing Invalid Strategy ===")
    try:
        run_strategy(price_data, strategy="unknown_strategy")
    except ValueError as e:
        print(f"Caught expected error: {e}")
