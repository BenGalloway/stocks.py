import yfinance as yf
import pandas as pd
import time
import sys

# --- Weights ---
VALUE_WEIGHT = 0.50
GROWTH_WEIGHT = 0.30
QUALITY_WEIGHT = 0.20

# --- Individual metric weights within each category ---
# Value: P/E vs sector, Price to Book, Price to Free Cash Flow
# Growth: EPS YoY, Revenue YoY
# Quality: Debt reduction magnitude, Gross margin, Return on equity

def fetch_ticker_data(ticker_symbol, retries=3, wait=10):
    for attempt in range(retries):
        try:
            stock = yf.Ticker(ticker_symbol)
            info = stock.info
            financials = stock.financials
            balance_sheet = stock.balance_sheet
            if info:
                return stock, info, financials, balance_sheet
        except Exception as e:
            print(f"  Attempt {attempt+1} failed for {ticker_symbol}: {e}")
            time.sleep(wait * (attempt + 1))
    
    print(f"\n⛔ yfinance appears to be rate limited. Saving progress and exiting.")
    sys.exit(1)


def score_value(info, financials, balance_sheet):
    scores = []

    # P/E ratio vs sector average
    # yfinance doesn't provide sector P/E directly so we score
    # on absolute P/E — lower is better, capped at 0-100
    try:
        pe = info.get('trailingPE', None)
        if pe and pe > 0:
            # Score inversely — P/E of 10 = 90, P/E of 50 = 50, P/E of 100+ = 0
            pe_score = max(0, 100 - pe)
            scores.append(pe_score)
    except:
        pass

    # Price to Book — lower is better
    try:
        pb = info.get('priceToBook', None)
        if pb and pb > 0:
            # P/B of 1 = 90, P/B of 5 = 50, P/B of 10+ = 0
            pb_score = max(0, 100 - (pb * 10))
            scores.append(pb_score)
    except:
        pass

    # Price to Free Cash Flow — lower is better
    try:
        price = info.get('currentPrice', None)
        fcf = info.get('freeCashflow', None)
        shares = info.get('sharesOutstanding', None)
        if price and fcf and shares and fcf > 0:
            pfcf = (price * shares) / fcf
            # P/FCF of 10 = 90, P/FCF of 50 = 50, P/FCF of 100+ = 0
            pfcf_score = max(0, 100 - pfcf)
            scores.append(pfcf_score)
    except:
        pass

    return sum(scores) / len(scores) if scores else None


def score_growth(info, financials):
    scores = []

    # EPS Growth YoY
    try:
        eps_current = financials.loc['Basic EPS'].iloc[0] if 'Basic EPS' in financials.index else None
        eps_prev = financials.loc['Basic EPS'].iloc[1] if 'Basic EPS' in financials.index else None
        if eps_current and eps_prev and eps_prev != 0:
            eps_growth = ((eps_current - eps_prev) / abs(eps_prev)) * 100
            # Cap score between 0-100, 50% growth = 100 score
            eps_score = max(0, min(100, eps_growth * 2))
            scores.append(eps_score)
    except:
        pass

    # Revenue Growth YoY
    try:
        rev_current = financials.loc['Total Revenue'].iloc[0]
        rev_prev = financials.loc['Total Revenue'].iloc[1]
        if rev_current and rev_prev and rev_prev != 0:
            rev_growth = ((rev_current - rev_prev) / abs(rev_prev)) * 100
            # Cap score between 0-100, 50% growth = 100 score
            rev_score = max(0, min(100, rev_growth * 2))
            scores.append(rev_score)
    except:
        pass

    return sum(scores) / len(scores) if scores else None


def score_quality(info, financials, balance_sheet):
    scores = []

    # Debt reduction magnitude — bigger reduction = better score
    try:
        current_debt = balance_sheet.loc['Total Debt'].iloc[0]
        prev_debt = balance_sheet.loc['Total Debt'].iloc[1]
        if prev_debt and prev_debt > 0:
            debt_reduction_pct = ((prev_debt - current_debt) / prev_debt) * 100
            debt_score = max(0, min(100, debt_reduction_pct * 5))
            scores.append(debt_score)
    except:
        pass

    # Gross Margin — higher is better
    try:
        gross_margin = info.get('grossMargins', None)
        if gross_margin:
            margin_score = max(0, min(100, gross_margin * 100))
            scores.append(margin_score)
    except:
        pass

    # Return on Equity — higher is better
    try:
        roe = info.get('returnOnEquity', None)
        if roe:
            roe_score = max(0, min(100, roe * 100))
            scores.append(roe_score)
    except:
        pass

    return sum(scores) / len(scores) if scores else None


def rank_tickers(input_csv='approved_tickers.csv', output_csv='ranked_results.csv'):
    # Load approved tickers
    df_input = pd.read_csv(input_csv)
    tickers = df_input['Ticker'].tolist()
    print(f"Loaded {len(tickers)} approved tickers to rank.\n")

    results = []

    for i, ticker in enumerate(tickers, 1):
        print(f"[{i}/{len(tickers)}] Scoring {ticker}...")

        stock, info, financials, balance_sheet = fetch_ticker_data(ticker)

        value_score = score_value(info, financials, balance_sheet)
        growth_score = score_growth(info, financials)
        quality_score = score_quality(info, financials, balance_sheet)

        # Skip if we couldn't get enough data to score meaningfully
        if value_score is None and growth_score is None and quality_score is None:
            print(f"  ⚠️ {ticker} skipped — insufficient data.")
            continue

        # Use 0 for any missing category rather than skipping entirely
        v = value_score if value_score is not None else 0
        g = growth_score if growth_score is not None else 0
        q = quality_score if quality_score is not None else 0

        final_score = (v * VALUE_WEIGHT) + (g * GROWTH_WEIGHT) + (q * QUALITY_WEIGHT)

        results.append({
            'Ticker': ticker,
            'Final Score': round(final_score, 2),
            'Value Score': round(v, 2),
            'Growth Score': round(g, 2),
            'Quality Score': round(q, 2),
        })

        time.sleep(1.0)

    # Sort by final score descending
    df_results = pd.DataFrame(results)
    df_results = df_results.sort_values('Final Score', ascending=False).reset_index(drop=True)
    df_results.index += 1  # Rank starts at 1
    df_results.index.name = 'Rank'

    df_results.to_csv(output_csv)
    print(f"\n✅ Ranking complete. Results saved to {output_csv}")
    print(df_results.head(25).to_string())
    return df_results


if __name__ == "__main__":
    rank_tickers()