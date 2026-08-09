import yfinance as yf
import json

WATCHLIST = ["SPCX", "ASTS", "NVDA", "TSLA", "PLTR", "AMD", "AAPL", "MSFT", "AMZN", "GOOGL", "META", "AVGO", "SMCI", "COIN", "MSTR", "IONQ", "RKLB"]
data_results = {}

for t in WATCHLIST:
    try:
        ticker = yf.Ticker(t)
        hist = ticker.history(period="1mo")
        if not hist.empty:
            data_results[t] = {"price": float(hist['Close'].iloc[-1]), "date": str(hist.index[-1].date())}
    except:
        continue

with open('stock_data.json', 'w') as f:
    json.dump(data_results, f, indent=4)
