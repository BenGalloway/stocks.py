import pandas as pd

def get_all_tickers():
    tickers = set()

    try:
        nasdaq = pd.read_csv('https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt', sep='|')
        tickers.update(nasdaq['Symbol'].dropna().tolist())
    except Exception as e:
        print(f"NASDAQ fetch failed: {e}")

    try:
        other = pd.read_csv('https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt', sep='|')
        tickers.update(other['ACT Symbol'].dropna().tolist())
    except Exception as e:
        print(f"Other exchange fetch failed: {e}")

    cleaned = [
        t for t in tickers
        if isinstance(t, str)
        and 1 <= len(t) <= 5
        and t.isalpha()
    ]

    return sorted(set(cleaned))