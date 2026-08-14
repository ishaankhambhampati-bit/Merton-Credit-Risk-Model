"""
Fetches debt data for the 25-company main dataset for overall empirical testing.
"""

from sec_debt_fetcher import fetch_debt_data

TICKERS = [
    "AAPL", "MSFT", "JNJ", "PG", "WMT", "KO", "EMR",
    "HD", "MCD", "PEP", "UNP", "TGT", "NSC",
    "VST", "OXY", "MMM", "LOW", "KHC",
    "CCL", "RCL", "UAL", "DAL",
    "LUMN", "BALY", "AMC",
]


def run_batch():
    config_lines = []

    for ticker in TICKERS:
        print(f"\n=== {ticker} ===")

        try:
            debt_data = fetch_debt_data(ticker)
        except Exception as e:
            print(f"  failed to fetch debt data: {e}")
            continue

        short_term = debt_data.get("short_term_debt")
        long_term = debt_data.get("long_term_debt")
        shares = debt_data.get("shares_outstanding")

        if short_term is None or long_term is None or shares is None or shares == 0:
            print(f"Incomplete or invalid debt data for {ticker}. Fill in manually "
                  f"Use the Nasdaq balance sheet if needed.")
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

    print("\n\n=== Paste this into screener.py's COMPANIES list ===")
    print("(Manually download each HistoricalData.csv from Nasdaq)")
    print("\n".join(config_lines))


if __name__ == "__main__":
    run_batch()
