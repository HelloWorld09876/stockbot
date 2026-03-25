# Nifty 50 StockBot MVP

A modular Python-based stock bot that fetches Nifty 50 data, scans for signals (Golden Cross or Momentum), calculates optimal capital allocation (Max Sharpe or Equal Weight), and provides a FastAPI endpoint to run the pipeline.

## 🚀 How to Run the Bot

### 1. Install Dependencies

Ensure you are in the project root directory and have your virtual environment activated:

```bash
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 2. Start the Application

The easiest way to run the entire stack (FastAPI Backend + Vite Frontend) is using the provided batch script.

```bash
.\run.bat
```

This will:
- Start the FastAPI server on `http://localhost:8000`
- Start the React frontend on `http://localhost:5173`

*(Note: Ensure `requirements.txt` is installed and frontend dependencies are installed via `cd frontend && npm install` before running)*

### 3. Run the Bot Pipeline

Open your browser or use `curl` to hit the `/run-bot` endpoint:

* **Golden Cross Strategy (Default):**
  [http://localhost:8000/run-bot?strategy=golden_cross](http://localhost:8000/run-bot?strategy=golden_cross)

* **Momentum / Alpha Strategy:**
  [http://localhost:8000/run-bot?strategy=alpha](http://localhost:8000/run-bot?strategy=alpha)

### 4. Manage Trades (Database)

You can view or add manual trades via the database API:

* **View all trades:** [http://localhost:8000/db/trades/](http://localhost:8000/db/trades/)
* **Interactive API Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)

## 📁 Module Overview

| Module | Responsibility |
| :--- | :--- |
| `data_ingestion.py` | Fetches historical data (yfinance) and real-time CMP (nsepython). |
| `strategy_engine.py` | Vectorized logic for **Golden Cross** and **Alpha/Momentum**. |
| `portfolio_allocation.py` | Efficient Frontier (Max Sharpe) with a 1/N Equal Weight fallback. |
| `db_api.py` | FastAPI backend for logging trades into a SQLite database. |
| `backend/` | The master orchestrator tying all phases together into a decoupled API. |
| `frontend/` | A modern React/Vite web application that visualizes advice, portfolio data, and signals. |

## 🛠️ Data Sanitization

The bot automatically:

* Drops delisted or all-NaN stocks (like `TATAMOTORS.NS`).
* Fills intermittent data gaps via forward/backward filling to ensure the Portfolio Optimizer doesn't crash on singular matrices.
