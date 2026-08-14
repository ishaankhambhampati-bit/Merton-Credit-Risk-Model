"""
Fetches debt data for the 16-company STRESS-TEST dataset. Is meant to oversample the BB/B/CCC
credit tier. 

Note that MGM, HTZ, CNK, and IHRT needed manual balance-sheet lookups
because the automated SEC XBRL fetch couldn't match a debt
tag for them. Their manually-verified figures are already correct in
screener_stress_test.py. This script exists so that you can re-attempt the
automated fetch. For example if  sec_debt_fetcher.py's tag list gets expanded
later.
"""

from sec_debt_fetcher import fetch_debt_data

TICKERS = [
    "AAPL", "JNJ", "KO",
    "CCL", "RCL", "UAL", "DAL", "WYNN", "MGM", "CAR",
    "LUMN", "CNK", "IHRT",
    "BALY", "AMC", "HTZ",
]


def run_batch():
    config_lines = []

    for ticker in TICKERS:
        print(f"\n=== {ticker} ===")

        try:
            debt_data = fetch_debt_data(ticker)
        except Exception as e:
            print(f"  FAILED to fetch debt data: {e}")
            continue

        short_term = debt_data.get("short_term_debt")
        long_term = debt_data.get("long_term_debt")
        shares = debt_data.get("shares_outstanding")

        if short_term is None or long_term is None or shares is None or shares == 0:
            print(f"  Incomplete or invalid debt data for {ticker} -- fill in manually "
                  f"via Nasdaq balance sheet if needed (this happened for MGM, HTZ, CNK, "
                  f"and IHRT last time -- see screener_stress_test.py for the manually "
                  f"verified figures already in use).")
            continue

        short_term_per_share = short_term / shares
        long_term_per_share = long_term / shares

        print(f"  Short-term debt/share: ${short_term_per_share:.2f} "
              f"(tag: {debt_data['short_term_debt_tag']}, as of {debt_data['short_term_debt_date']})")
        print(f"  Long-term debt/share:  ${long_term_per_share:.2f} "
              f"(tag: {debt_data['long_term_debt_tag']}, as of {debt_data['long_term_debt_date']})")

        config_lines.append(
            f'    {{"ticker": "{ticker}", "csv_file": "{ticker}HistoricalData.csv", '
            f'"short_term": {short_term_per_share:.4f}, "long_term": {long_term_per_share:.4f}}},'
        )

    print("\n\n=== Paste this into screener_stress_test.py's COMPANIES list ===")
    print("(remember: you still need to manually download each *HistoricalData.csv from Nasdaq)")
    print("\n".join(config_lines))


if __name__ == "__main__":
    run_batch()
