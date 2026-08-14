"""
Two choices to get pricing data into the model. User can pick for convenience:

Choice 1: Download 1-year pricing data csv files from Nasdaq.com. This is 
the best and most efficient way of importing pricing data into the model that I've seen
when testing.

Choice 2: etch_alpha_vantage() [for other people running this repo]
Fully automated via Alpha Vantage's free API. This is better for someone
who just wants to try a new ticker quickly. However Alpha Vantage's free tier
caps history at ~100 trading days and you have to pay for the full feature. 
"""

import csv
import requests


def load_nasdaq_csv(path):
    with open(path) as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    rows.reverse()  # Nasdaq exports newest-first; model needs oldest-first
    return [float(row["Close/Last"].replace("$", "")) for row in rows]


def fetch_alpha_vantage(ticker, api_key, outputsize="compact"):
    
    params = {
        "function": "TIME_SERIES_DAILY",
        "symbol": ticker.upper(),
        "outputsize": outputsize,
        "apikey": api_key,
    }
    resp = requests.get("https://www.alphavantage.co/query", params=params, timeout=20)
    resp.raise_for_status()
    data = resp.json()

    for error_key in ("Note", "Error Message", "Information"):
        if error_key in data:
            print(f"  Alpha Vantage {error_key}: {data[error_key]}")
            return None

    series = data.get("Time Series (Daily)")
    if not series:
        return None

    dates_sorted = sorted(series.keys())
    return [float(series[d]["4. close"]) for d in dates_sorted]
