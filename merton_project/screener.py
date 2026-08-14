"""
This runs the Merton model across multiple companies and prints a comparison
table. Each company needs its own 1-year daily closing price CSV (same
format as the Nasdaq export used for VST).

DEBT BARRIER: uses the KMV convention (short-term debt + 50% of long-term
debt) rather than total debt. 
To fill in short_term_debt / long_term_debt manually for a company:
  1. Go to stockanalysis.com/stocks/TICKER/financials/balance-sheet/
  2. Find "Current Portion of Long-Term Debt" (or "Short-Term Debt") and
     "Long-Term Debt" -- use the most recent quarter shown
  3. Divide both by shares outstanding to get per-share figures, matching
     how the rest of this project works in per-share terms

HOW TO USE:
  1. Download 1-year daily historical price CSVs for each company from
     Nasdaq (nasdaq.com/market-activity/stocks/TICKER/historical) or
     Yahoo Finance -- same process as before.
  2. Put them in the same folder as this script, named clearly
     (e.g. AAPLHistoricalData.csv).
  3. Fill in the COMPANIES list below with each ticker, its CSV filename,
     and its short-term/long-term debt-per-share figures.
  4. Run: python screener.py
"""

import csv
from merton_model import calibrate, kmv_default_barrier

RISK_FREE_RATE = 0.0400  # 1yr Treasury, Aug 4 2026 -- same for all companies
TIME_HORIZON_YEARS = 1.0

COMPANIES = [
   
    {"ticker": "VST",  "csv_file": "VSTHistoricalData.csv",  "short_term": 20.0160151848, "long_term": 54.9261522036},
    {"ticker": "AAPL", "csv_file": "AAPLHistoricalData.csv", "short_term": 0.89129540781, "long_term": 4.88965044551}, 
   {"ticker": "F", "csv_file": "FHistoricalData.csv", "short_term": 12.90, "long_term": 27.55},
    {"ticker": "HON", "csv_file": "HONHistoricalData.csv", "short_term": 24.48, "long_term": 82.74},
    {"ticker": "AMC",  "csv_file": "AMCHistoricalData.csv",  "short_term": 0.17510552079, "long_term": 4.19883545351},  
    {"ticker": "OXY",  "csv_file": "OXYHistoricalData.csv",  "short_term": 0.426289173, "long_term": 15.32931844},  
    {"ticker": "CCL",  "csv_file": "CCLHistoricalData.csv",  "short_term": 1.07372262774, "long_term": 17.0934306569},  
    {"ticker": "KO",   "csv_file": "KOHistoricalData.csv",   "short_term": 1.52139534884, "long_term": None}, 
    {"ticker": "MSFT", "csv_file": "MSFTHistoricalData.csv", "short_term": 1.2426, "long_term": 4.1838},  
    {"ticker": "JNJ", "csv_file": "JNJHistoricalData.csv", "short_term": 4.8517, "long_term": 15.4961},  
    {"ticker": "PG", "csv_file": "PGHistoricalData.csv", "short_term": 4.8597, "long_term": 9.8269},  
    {"ticker": "WMT", "csv_file": "WMTHistoricalData.csv", "short_term": 1.3412, "long_term": 4.6352},  
    {"ticker": "HD", "csv_file": "HDHistoricalData.csv", "short_term": 5.1930, "long_term": 49.5398},  
    {"ticker": "MCD", "csv_file": "MCDHistoricalData.csv", "short_term": 2.5334, "long_term": 56.4457},  
    {"ticker": "PEP", "csv_file": "PEPHistoricalData.csv", "short_term": 7.7677, "long_term": 31.0069},  
    {"ticker": "UNP", "csv_file": "UNPHistoricalData.csv", "short_term": 2.1681, "long_term": 53.5521},  
    {"ticker": "LOW", "csv_file": "LOWHistoricalData.csv", "short_term": 0.6777, "long_term": 71.0157},  
    {"ticker": "KHC", "csv_file": "KHCHistoricalData.csv", "short_term": 1.1654, "long_term": 14.8580},  
    {"ticker": "RCL", "csv_file": "RCLHistoricalData.csv", "short_term": 5.3991, "long_term": 73.3272},  
    {"ticker": "UAL", "csv_file": "UALHistoricalData.csv", "short_term": 12.6192, "long_term": 52.8985},  
    {"ticker": "DAL", "csv_file": "DALHistoricalData.csv", "short_term": 4.2638, "long_term": 15.3599},  
    {"ticker": "LUMN", "csv_file": "LUMNHistoricalData.csv", "short_term": 0.0543, "long_term": 12.7491},  
    {"ticker": "BALY", "csv_file": "BALYHistoricalData.csv", "short_term": 0.3513, "long_term": 89.6836},  
]


def load_nasdaq_csv(path):
    """
    Parses a Nasdaq-format historical data CSV (Date, Close/Last, Volume,
    Open, High, Low with $-prefixed prices, most-recent-first) into an
    oldest-to-newest list of closing prices -- same parsing logic used
    for the VST data.
    """
    with open(path) as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    rows.reverse()  
    return [float(row["Close/Last"].replace("$", "")) for row in rows]


def run_screener():
    results = []

    for company in COMPANIES:
        ticker = company["ticker"]
        print(f"\n=== {ticker} ===")

        if company["short_term"] is None or company["long_term"] is None:
            print(f"  Skipping -- short_term/long_term debt not filled in yet for {ticker}.")
            continue

        debt_barrier_kmv = kmv_default_barrier(company["short_term"], company["long_term"])
        debt_barrier_total = company["short_term"] + company["long_term"]

        try:
            equity_series = load_nasdaq_csv(company["csv_file"])
        except FileNotFoundError:
            print(f"  Skipping -- {company['csv_file']} not found yet. "
                  f"Download it and place it in this folder.")
            continue

        result_kmv = calibrate(
            equity_series=equity_series, D=debt_barrier_kmv,
            r=RISK_FREE_RATE, T=TIME_HORIZON_YEARS,
        )
        result_total = calibrate(
            equity_series=equity_series, D=debt_barrier_total,
            r=RISK_FREE_RATE, T=TIME_HORIZON_YEARS,
        )

        print(f"  KMV barrier (ST + 0.5*LT = ${debt_barrier_kmv:.2f}):")
        print(f"    First-passage PD: {result_kmv['probability_of_default_first_passage']:.4%}")
        print(f"  Total debt barrier (ST + LT = ${debt_barrier_total:.2f}):")
        print(f"    First-passage PD: {result_total['probability_of_default_first_passage']:.4%}")

        results.append({
            "ticker": ticker,
            "distance_to_default": result_total["distance_to_default"],
            "pd_kmv_pct": result_kmv["probability_of_default_first_passage"] * 100,
            "pd_total_pct": result_total["probability_of_default_first_passage"] * 100,
            "sigma_V": result_total["sigma_V"],
        })

    if results:
        print("\n=== Summary (sorted by total-debt-barrier risk, highest first) ===")
        results.sort(key=lambda r: r["pd_total_pct"], reverse=True)
        print(f"{'Ticker':<8}{'KMV Barrier PD':<18}{'Total Debt PD':<18}{'Asset Vol':<12}")
        for r in results:
            print(f"{r['ticker']:<8}{r['pd_kmv_pct']:<18.4f}{r['pd_total_pct']:<18.4f}{r['sigma_V']:<12.2%}")


if __name__ == "__main__":
    run_screener()
