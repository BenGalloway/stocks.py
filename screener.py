import yfinance as yf
import pandas_ta as ta
import sys
import time

PRICE_MIN = 20.0
VOLUME_MIN = 500_000

def fetch_with_retry(ticker_symbol, retries=3, wait=10):
    for attempt in range(retries):
        try:
            stock = yf.Ticker(ticker_symbol)
            df = stock.history(period="2y")
            if not df.empty:
                return stock, df
            return stock
        except Exception as e:
            print(f" Attempt {attempt+1} failed for {ticker_symbol}: {e}")
            time.sleep(wait * (attempt+1))

    # All retries exhausted, yfinance likely rate limiting
    print("\n⛔ yfinance appears to be rate limited after multiple retries.")
    print("Wait a while then rerun — the database will skip already-scanned tickers.")
    sys.exit(1)

def passes_prefilter(ticker_symbol):
    """
    Lightweight check: price > $20 and 30-day avg volume > 500,000.
    Uses only 35 days of data to stay fast.
    """
    try:
        stock = yf.Ticker(ticker_symbol)
        df = stock.history(period="35d")

        if df.empty or len(df) < 20:
            return False, "Not enough recent data for prefilter."

        current_price = df['Close'].iloc[-1]
        avg_volume = df['Volume'].iloc[-30:].mean()

        if current_price < PRICE_MIN:
            return False, f"Price ${current_price:.2f} below ${PRICE_MIN} threshold."
        if avg_volume < VOLUME_MIN:
            return False, f"Avg volume {avg_volume:,.0f} below {VOLUME_MIN:,} threshold."

        return True, "Passed prefilter."

    except Exception as e:
        return False, f"Prefilter error: {e}"


def evaluate_ticker(ticker_symbol):
    """
    Full technical + fundamental evaluation.
    Only called if ticker passes the prefilter.
    """
    try:
        stock, df = fetch_with_retry(ticker_symbol)
        if stock is None:
            return False, "Failed after retries, likely rate limited."

        if df.empty or len(df) < 250:
            return False, "Not enough trading days."

        df['WMA_246'] = ta.wma(df['Close'], length=246)
        df['OBV'] = ta.obv(df['Close'], df['Volume'])

        current_price = df['Close'].iloc[-1]
        current_wma = df['WMA_246'].iloc[-1]

        if current_price < current_wma:
            return False, "Price below 246 WMA."

        # Fundamental Data
        financials = stock.financials
        balance_sheet = stock.balance_sheet

        if financials.empty or balance_sheet.empty:
            return False, "Missing fundamental data."

        try:
            gross_profit = financials.loc['Gross Profit'].iloc[0]
            if gross_profit <= 0:
                return False, "Negative gross profit."
        except KeyError:
            pass

        try:
            current_debt = balance_sheet.loc['Total Debt'].iloc[0]
            prev_debt = balance_sheet.loc['Total Debt'].iloc[1]
            if current_debt >= prev_debt:
                return False, "Debt did not decrease YoY."
        except KeyError:
            pass

        return True, "Passed all criteria!"

    except Exception as e:
        return False, f"Error processing: {e}"