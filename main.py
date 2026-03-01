import time
import csv
from tickers import get_all_tickers
from database import setup_db, can_scan_ticker, log_scan, reset_db, log_approved, get_all_approved
from screener import passes_prefilter, evaluate_ticker

SLEEP_BETWEEN_TICKERS = 1.5
COOLDOWN_DAYS = 21

def run_screener():
    conn = setup_db()
    approved_tickers = []

    print("Fetching ticker universe...")
    all_tickers = get_all_tickers()
    print(f"Loaded {len(all_tickers)} tickers.\n")

    # If we've scanned everything before, reset so nothing gets skipped
    skippable = [t for t in all_tickers if not can_scan_ticker(t, conn, COOLDOWN_DAYS)]
    if len(skippable) == len(all_tickers):
        print("All tickers have been scanned recently. Resetting database for fresh run.")
        reset_db(conn)

    scanned_count = 0
    skipped_count = 0

    for ticker in all_tickers:
        if not can_scan_ticker(ticker, conn, COOLDOWN_DAYS):
            skipped_count += 1
            continue

        # Stage 1: Fast prefilter (price + volume)
        prefilter_passed, prefilter_reason = passes_prefilter(ticker)
        if not prefilter_passed:
            print(f"🔵 {ticker} skipped prefilter: {prefilter_reason}")
            log_scan(ticker, conn)
            time.sleep(0.5)  # shorter sleep for lightweight calls
            scanned_count += 1
            continue

        # Stage 2: Full evaluation
        print(f"Evaluating {ticker} (passed prefilter)...")
        passed, reason = evaluate_ticker(ticker)

        if passed:
            print(f"🟢 {ticker} PASSED!")
            approved_tickers.append(ticker)
            log_approved(ticker, conn)
        else:
            print(f"🔴 {ticker} failed: {reason}")

        log_scan(ticker, conn)
        scanned_count += 1
        time.sleep(SLEEP_BETWEEN_TICKERS)

        all_approved = get_all_approved(conn)
        with open("approved_tickers.txt", "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Ticker", "Approved Date"])
            writer.writerows(all_approved)
        print(f"Approved tickers exported to approved_tickers.csv")

    conn.close()

    print(f"\n--- Scan Complete ---")
    print(f"Scanned: {scanned_count} | Skipped (cooldown): {skipped_count}")
    print(f"Approved tickers: {approved_tickers}")
    return approved_tickers


if __name__ == "__main__":
    run_screener()