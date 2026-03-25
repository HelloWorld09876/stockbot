"""
Phase 1: Data Ingestion & Normalization

This module is directly responsible for fetching historical and real-time
data for the Nifty 50 stock universe using yfinance and nsepython.
"""

import logging
import pandas as pd
import yfinance as yf
from typing import List, Dict, Optional

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# The Nifty 50 Universe formatted for yfinance
NIFTY_50_TICKERS = [
    "ADANIENT.NS", "ADANIPORTS.NS", "APOLLOHOSP.NS", "ASIANPAINT.NS", "AXISBANK.NS",
    "BAJAJ-AUTO.NS", "BAJFINANCE.NS", "BAJAJFINSV.NS", "BEL.NS", "BHARTIARTL.NS",
    "BPCL.NS", "BRITANNIA.NS", "CIPLA.NS", "COALINDIA.NS", "DIVISLAB.NS",
    "DRREDDY.NS", "EICHERMOT.NS", "GRASIM.NS", "HCLTECH.NS", "HDFCBANK.NS",
    "HDFCLIFE.NS", "HEROMOTOCO.NS", "HINDALCO.NS", "HINDUNILVR.NS", "ICICIBANK.NS",
    "INDUSINDBK.NS", "INFY.NS", "ITC.NS", "JSWSTEEL.NS", "KOTAKBANK.NS",
    "LT.NS", "LTIM.NS", "M&M.NS", "MARUTI.NS", "NESTLEIND.NS",
    "NTPC.NS", "ONGC.NS", "POWERGRID.NS", "RELIANCE.NS", "SBILIFE.NS",
    "SBIN.NS", "SHRIRAMFIN.NS", "SUNPHARMA.NS", "TATACONSUM.NS", "TATAMOTORS.NS",
    "TATASTEEL.NS", "TCS.NS", "TECHM.NS", "TITAN.NS", "ULTRACEMCO.NS", "WIPRO.NS"
][:50]  # Just ensure it's exactly 50 tickers

def fetch_historical_data(tickers: List[str], period: str = "1y") -> pd.DataFrame:
    """
    Fetches daily historical Close price data for a list of tickers.
    
    Args:
        tickers (List[str]): List of ticker symbols formatted for yfinance (e.g., 'RELIANCE.NS').
        period (str): The time period to fetch data for (default is '1y').
        
    Returns:
        pd.DataFrame: A DataFrame containing the historical 'Close' prices for successfully fetched tickers.
    """
    historical_data: Dict[str, pd.Series] = {}
    
    for ticker in tickers:
        try:
            # We fetch one by one to ensure isolated error handling, so one bad ticker doesn't crash the batch.
            df = yf.download(ticker, period=period, progress=False)
            
            if not df.empty and 'Close' in df.columns:
                # Based on yfinance version, 'Close' may be a Series or part of a MultiIndex if multiple tickers
                # Since we download one by one, df['Close'] should typically be a Series.
                close_series = df['Close']
                if isinstance(close_series, pd.DataFrame):
                    # Edge case handling for some yfinance versions returning df for single column
                    close_series = close_series.iloc[:, 0]
                
                historical_data[ticker] = close_series.dropna()
            else:
                logging.warning(f"No 'Close' data found for {ticker}.")
                
        except Exception as e:
            logging.warning(f"Failed to fetch historical data for {ticker}. Error: {e}")
            
    # Combine all series into a single DataFrame
    if not historical_data:
        return pd.DataFrame()

    df = pd.DataFrame(historical_data)

    # --- Data Sanitization ---

    # Step 1: Identify and drop columns that are entirely NaN (delisted / bad tickers)
    all_nan_cols = df.columns[df.isna().all()].tolist()
    if all_nan_cols:
        for bad_ticker in all_nan_cols:
            logging.warning(f"Dropped {bad_ticker} due to missing/NaN data.")
        df = df.drop(columns=all_nan_cols)

    # Step 2: Patch isolated missing daily prices (trading halts, API gaps)
    # Forward-fill first, then backward-fill to handle gaps at the start of the series
    df = df.ffill().bfill()

    return df

def fetch_realtime_cmp(ticker_symbol: str) -> Optional[float]:
    """
    Fetches the exact Current Market Price (CMP) using nsepython, with a fallback to yfinance.
    
    Args:
        ticker_symbol (str): The ticker symbol (e.g., 'RELIANCE.NS').
        
    Returns:
        float: The current market price, or None if completely failed.
    """
    # Strip '.NS' suffix for nsepython
    clean_symbol = ticker_symbol.replace('.NS', '')
    
    try:
        from nsepython import nse_quote_ltp
        # Attempt to fetch using nsepython
        cmp = nse_quote_ltp(clean_symbol)
        if cmp is not None:
            return float(cmp)
    except Exception as e:
        logging.warning(f"nsepython failed for {clean_symbol}. Error: {e}. Falling back to yfinance...")
        
    # Fallback to yfinance if nsepython fails or times out
    try:
        ticker_data = yf.Ticker(ticker_symbol)
        info = ticker_data.info
        
        # Check standard info fields for current price
        if 'currentPrice' in info and info['currentPrice'] is not None:
            return float(info['currentPrice'])
        elif 'regularMarketPrice' in info and info['regularMarketPrice'] is not None:
            return float(info['regularMarketPrice'])
        else:
            # Fallback to downloading the last day's data if info is incomplete
            df = ticker_data.history(period="1d")
            if not df.empty:
                return float(df['Close'].iloc[-1])
    except Exception as e:
        logging.warning(f"yfinance fallback failed for {ticker_symbol}. Error: {e}")
        
    return None

if __name__ == "__main__":
    # Test fetching historical data for 3 sample stocks
    print("=== Testing Historical Data Fetcher ===")
    test_tickers = NIFTY_50_TICKERS[:3]
    print(f"Fetching 1y data for: {test_tickers}")
    
    historical_df = fetch_historical_data(test_tickers, period="1y")
    print(f"\nHistorical Data Shape: {historical_df.shape}")
    print("Latest 5 days of data:")
    print(historical_df.tail())
    
    # Test real-time CMP for 1 stock
    print("\n=== Testing Real-Time CMP Fetcher ===")
    test_cmp_ticker = NIFTY_50_TICKERS[0]
    cmp_price = fetch_realtime_cmp(test_cmp_ticker)
    
    if cmp_price is not None:
        print(f"Current Market Price for {test_cmp_ticker}: {cmp_price}")
    else:
        print(f"Failed to fetch real-time CMP for {test_cmp_ticker}.")
