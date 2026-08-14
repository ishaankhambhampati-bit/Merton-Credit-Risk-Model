"""
This is a separate dataset from screener.py that deliberately oversamples
the BB/B/CCC credit tier, where the model actually has discriminating
work to do, rather than spreading companies thin across the full rating
spectrum. Keeps a small set of safe tickers (AAPL, JNJ, KO) purely for contrast.

HOW TO USE:
  1. Ensure every TICKERHistoricalData.csv referenced below is in this
     folder (downloaded from Nasdaq, 1-year daily).
  2. Run: python screener_stress_test.py
"""

import csv
from merton_model import calibrate, kmv_default_barrier

RISK_FREE_RATE = 0.0400
TIME_HORIZON_YEARS = 1.0

COMPANIES = [
    # -- Safe tickers (for contrast only) --
    {"ticker": "AAPL", "csv_file": "AAPLHistoricalData.csv", "short_term": 0.7542,  "long_term": 4.8882},
    {"ticker": "JNJ",  "csv_file": "JNJHistoricalData.csv",  "short_term": 4.8517,  "long_term": 15.4961},
    {"ticker": "KO",   "csv_file": "KOHistoricalData.csv",   "short_term": 0.0130,  "long_term": 9.0796},

    # -- BB tier --
    {"ticker": "CCL",  "csv_file": "CCLHistoricalData.csv",  "short_term": 1.0740,  "long_term": 17.0978},
    {"ticker": "RCL",  "csv_file": "RCLHistoricalData.csv",  "short_term": 5.3991,  "long_term": 73.3272},
    {"ticker": "UAL",  "csv_file": "UALHistoricalData.csv",  "short_term": 12.6192, "long_term": 52.8985},
    {"ticker": "DAL",  "csv_file": "DALHistoricalData.csv",  "short_term": 4.2638,  "long_term": 15.3599},
    {"ticker": "WYNN", "csv_file": "WYNNHistoricalData.csv", "short_term": 13.8770, "long_term": 90.2723},
    {"ticker": "MGM",  "csv_file": "MGMHistoricalData.csv",  "short_term": 0.0000,  "long_term": 24.35},
    {"ticker": "CAR",  "csv_file": "CARHistoricalData.csv",  "short_term": 0.6511,  "long_term": 170.4459},

    # -- B tier / weaker high-yield --
    {"ticker": "LUMN", "csv_file": "LUMNHistoricalData.csv", "short_term": 0.0543,  "long_term": 12.7491},
    {"ticker": "CNK",  "csv_file": "CNKHistoricalData.csv",  "short_term": 0.20,    "long_term": 17.12},
    {"ticker": "IHRT", "csv_file": "IHRTHistoricalData.csv", "short_term": 0.49,    "long_term": 32.94},

    # -- CCC / distressed --
    {"ticker": "BALY", "csv_file": "BALYHistoricalData.csv", "short_term": 0.3513,  "long_term": 89.6836},
    {"ticker": "AMC",  "csv_file": "AMCHistoricalData.csv",  "short_term": 0.1668,  "long_term": 4.1482},
    {"ticker": "HTZ",  "csv_file": "HTZHistoricalData.csv",  "short_term": 54.01,   "long_term": 0.00},
]


def load_nasdaq_csv(path):
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

        debt_barrier_kmv = kmv_default_barrier(company["short_term"], company["long_term"])
        debt_barrier_total = company["short_term"] + company["long_term"]

        try:
            equity_series = load_nasdaq_csv(company["csv_file"])
        except FileNotFoundError:
            print(f"  Skipping -- {company['csv_file']} not found yet. "
                  f"Download it from Nasdaq and place it in this folder.")
            continue

        result_kmv = calibrate(
            equity_series=equity_series, D=debt_barrier_kmv,
            r=RISK_FREE_RATE, T=TIME_HORIZON_YEARS,
        )
        result_total = calibrate(
            equity_series=equity_series, D=debt_barrier_total,
            r=RISK_FREE_RATE, T=TIME_HORIZON_YEARS,
        )

        print(f"  KMV barrier (${debt_barrier_kmv:.2f}):   First-passage PD: "
              f"{result_kmv['probability_of_default_first_passage']:.4%}")
        print(f"  Total debt (${debt_barrier_total:.2f}):  First-passage PD: "
              f"{result_total['probability_of_default_first_passage']:.4%}")

        results.append({
            "ticker": ticker,
            "distance_to_default": result_total["distance_to_default"],
            "pd_kmv_pct": result_kmv["probability_of_default_first_passage"] * 100,
            "pd_total_pct": result_total["probability_of_default_first_passage"] * 100,
            "sigma_V": result_total["sigma_V"],
        })

    if results:
        print("\n\n=== Summary (sorted by total-debt-barrier risk, highest first) ===")
        results.sort(key=lambda r: r["pd_total_pct"], reverse=True)
        print(f"{'Ticker':<8}{'KMV Barrier PD':<18}{'Total Debt PD':<18}{'Asset Vol':<12}")
        for r in results:
            print(f"{r['ticker']:<8}{r['pd_kmv_pct']:<18.4f}{r['pd_total_pct']:<18.4f}{r['sigma_V']:<12.2%}")

        print(f"\nCompanies with data: {len(results)} / {len(COMPANIES)}")


if __name__ == "__main__":
    run_screener()
