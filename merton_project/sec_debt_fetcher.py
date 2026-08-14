"""
This pulls short-term debt, long-term debt, and shares outstanding directly
from SEC's XBRL "company facts" API. This is data taken directly
from each company's own filed financial statements.
"""

import json
import os
import time
import requests
from datetime import datetime

USER_AGENT = "REPLACE_ME YourName your_real_email@example.com"  
HEADERS = {"User-Agent": USER_AGENT}

CIK_MAPPING_FILE = "company_tickers.json"
SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
REQUEST_DELAY = 0.15


SHORT_TERM_DEBT_TAGS = [
    "ShortTermBorrowings",
    "DebtCurrent",
    "LongTermDebtCurrent",
    "ShortTermDebtAndCurrentPortionOfLongTermDebt",
    "OtherShortTermBorrowings",
    "SecuredDebtCurrent",
    "LinesOfCreditCurrent",
    "NotesPayableCurrent",
    "LongTermDebtAndCapitalLeaseObligationsCurrent",
    "CommercialPaper",
]
LONG_TERM_DEBT_TAGS = [
    "LongTermDebtNoncurrent",
    "LongTermDebt",
    "LongTermDebtAndCapitalLeaseObligations",
    "SecuredLongTermDebt",
    "UnsecuredLongTermDebt",
    "SeniorLongTermNotes",
    "LongTermNotesPayable",
]
SHARES_OUTSTANDING_TAGS = [
    "CommonStockSharesOutstanding",
    "EntityCommonStockSharesOutstanding",
]


def download_cik_mapping(url=SEC_TICKERS_URL, local_path=CIK_MAPPING_FILE, max_age_days=7):
    if os.path.exists(local_path):
        age_seconds = time.time() - os.path.getmtime(local_path)
        if age_seconds < max_age_days * 24 * 3600:
            return
    resp = requests.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    with open(local_path, "wb") as f:
        f.write(resp.content)


def get_cik_from_ticker(ticker, local_path=CIK_MAPPING_FILE):
    download_cik_mapping(local_path=local_path)
    with open(local_path, "r") as f:
        data = json.load(f)
    ticker_upper = ticker.upper()
    for entry in data.values():
        if entry["ticker"].upper() == ticker_upper:
            return str(entry["cik_str"]).zfill(10)
    raise ValueError(f"Ticker {ticker} not found in SEC ticker mapping.")


def get_company_facts(cik_padded):
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik_padded}.json"
    resp = requests.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    return resp.json()


def _most_recent_value(facts, tag, unit="USD", max_age_days=400):
    
    try:
        entries = facts["facts"]["us-gaap"][tag]["units"][unit]
    except KeyError:
        return None, None

    if not entries:
        return None, None

    entries_sorted = sorted(entries, key=lambda e: e.get("end", ""), reverse=True)
    most_recent = entries_sorted[0]
    end_date_str = most_recent.get("end", "")

    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
            age_days = (datetime.now() - end_date).days
            if age_days > max_age_days:
                
                return None, None
        except ValueError:
            pass

    return most_recent.get("val"), end_date_str


def _most_recent_shares(facts):
    try:
        entries = facts["facts"]["dei"]["EntityCommonStockSharesOutstanding"]["units"]["shares"]
        entries_sorted = sorted(entries, key=lambda e: e.get("end", ""), reverse=True)
        return entries_sorted[0].get("val"), entries_sorted[0].get("end")
    except (KeyError, IndexError):
        pass

    for tag in SHARES_OUTSTANDING_TAGS:
        try:
            entries = facts["facts"]["us-gaap"][tag]["units"]["shares"]
            entries_sorted = sorted(entries, key=lambda e: e.get("end", ""), reverse=True)
            return entries_sorted[0].get("val"), entries_sorted[0].get("end")
        except KeyError:
            continue
    return None, None


def fetch_debt_data(ticker):
    
    cik = get_cik_from_ticker(ticker)
    time.sleep(REQUEST_DELAY)
    facts = get_company_facts(cik)
    time.sleep(REQUEST_DELAY)

    result = {"ticker": ticker, "cik": cik}

    for tag in SHORT_TERM_DEBT_TAGS:
        val, end_date = _most_recent_value(facts, tag)
        if val is not None:
            result["short_term_debt"] = val
            result["short_term_debt_tag"] = tag
            result["short_term_debt_date"] = end_date
            break
    else:
        result["short_term_debt"] = None
        result["short_term_debt_tag"] = None
        print(f"  WARNING: no short-term debt tag matched for {ticker} -- check manually.")

    for tag in LONG_TERM_DEBT_TAGS:
        val, end_date = _most_recent_value(facts, tag)
        if val is not None:
            result["long_term_debt"] = val
            result["long_term_debt_tag"] = tag
            result["long_term_debt_date"] = end_date
            break
    else:
        result["long_term_debt"] = None
        result["long_term_debt_tag"] = None
        print(f"  WARNING: no long-term debt tag matched for {ticker} -- check manually.")

    shares, shares_date = _most_recent_shares(facts)
    result["shares_outstanding"] = shares
    result["shares_outstanding_date"] = shares_date
    if shares is None:
        print(f"  WARNING: no shares outstanding tag matched for {ticker} -- check manually.")

    return result


if __name__ == "__main__":
    if "REPLACE_ME" in USER_AGENT:
        raise SystemExit("Set a real USER_AGENT first (your name + email).")

    
    test_ticker = "MSFT"
    data = fetch_debt_data(test_ticker)
    print(json.dumps(data, indent=2))
