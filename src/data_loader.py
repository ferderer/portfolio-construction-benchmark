"""
Download and prepare ETF price data from Yahoo Finance.

Assets:
    SPY  – S&P 500          (US Large Cap)
    EEM  – MSCI Emerging Markets
    AGG  – US Aggregate Bond
    VNQ  – Vanguard Real Estate (REITs)

Period: 2004-01-01 to 2024-12-31 (~20 years)
"""

from pathlib import Path

import pandas as pd
import yfinance as yf

TICKERS = ["SPY", "EEM", "AGG", "VNQ"]
START = "2004-01-01"
END = "2024-12-31"

RAW_DIR = Path(__file__).parent.parent / "data" / "raw"
PROCESSED_DIR = Path(__file__).parent.parent / "data" / "processed"


def download_prices(tickers: list[str] = TICKERS, start: str = START, end: str = END) -> pd.DataFrame:
    """Download adjusted close prices from Yahoo Finance."""
    print(f"Downloading {tickers} from {start} to {end} ...")
    raw = yf.download(tickers, start=start, end=end, auto_adjust=True)

    # yf.download returns MultiIndex columns: (Price, Ticker)
    # We need just Close prices
    if isinstance(raw.columns, pd.MultiIndex):
        prices = raw["Close"]
    else:
        prices = raw[["Close"]]
        prices.columns = tickers

    prices = prices[tickers]  # enforce column order
    return prices


def validate_prices(prices: pd.DataFrame) -> None:
    """Sanity checks on downloaded data."""
    print(f"\nShape: {prices.shape}")
    print(f"Date range: {prices.index.min().date()} to {prices.index.max().date()}")
    print(f"\nMissing values:\n{prices.isna().sum()}")
    print(f"\nFirst available date per asset:")
    for col in prices.columns:
        first_valid = prices[col].first_valid_index()
        print(f"  {col}: {first_valid.date() if first_valid else 'NO DATA'}")

    # Check for suspicious gaps (> 5 consecutive trading days)
    for col in prices.columns:
        series = prices[col].dropna()
        gaps = series.index.to_series().diff().dt.days
        max_gap = gaps.max()
        if max_gap > 7:
            print(f"  ⚠ {col}: max gap = {max_gap} days")


def clean_prices(prices: pd.DataFrame) -> pd.DataFrame:
    """
    Clean price data:
    1. Forward-fill small gaps (weekends, holidays already handled by Yahoo)
    2. Drop rows where ANY asset has no data (align start dates)
    3. Verify no NaN remains
    """
    # Forward-fill gaps up to 5 days (holidays across markets)
    cleaned = prices.ffill(limit=5)

    # Align: drop rows before all assets have data
    cleaned = cleaned.dropna()

    assert cleaned.isna().sum().sum() == 0, "NaN values remain after cleaning"
    print(f"\nCleaned shape: {cleaned.shape}")
    print(f"Aligned date range: {cleaned.index.min().date()} to {cleaned.index.max().date()}")

    return cleaned


def compute_returns(prices: pd.DataFrame) -> pd.DataFrame:
    """Compute daily simple returns."""
    returns = prices.pct_change().dropna()
    return returns


def save_data(prices: pd.DataFrame, returns: pd.DataFrame) -> None:
    """Save processed data to CSV."""
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    prices_path = PROCESSED_DIR / "prices.csv"
    returns_path = PROCESSED_DIR / "returns.csv"

    prices.to_csv(prices_path)
    returns.to_csv(returns_path)

    print(f"\nSaved: {prices_path}  ({prices.shape})")
    print(f"Saved: {returns_path}  ({returns.shape})")


def save_raw(prices: pd.DataFrame) -> None:
    """Save raw download for reproducibility."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    raw_path = RAW_DIR / "yahoo_prices_raw.csv"
    prices.to_csv(raw_path)
    print(f"Saved raw: {raw_path}")


def load_prices() -> pd.DataFrame:
    """Load processed prices from CSV."""
    path = PROCESSED_DIR / "prices.csv"
    return pd.read_csv(path, index_col=0, parse_dates=True)


def load_returns() -> pd.DataFrame:
    """Load processed returns from CSV."""
    path = PROCESSED_DIR / "returns.csv"
    return pd.read_csv(path, index_col=0, parse_dates=True)


def main():
    """Full pipeline: download → validate → clean → compute returns → save."""
    try:
        # Download
        raw_prices = download_prices()

        if raw_prices.empty:
            raise RuntimeError("Yahoo Finance returned empty data")

        save_raw(raw_prices)

        # Validate
        validate_prices(raw_prices)

        # Clean
        prices = clean_prices(raw_prices)

        # Returns
        returns = compute_returns(prices)

    except Exception as e:
        print(f"\n⚠ Yahoo Finance unavailable: {e}")
        print("Falling back to synthetic data (see synthetic_data.py)\n")
        from src.synthetic_data import generate_synthetic_data
        prices, returns = generate_synthetic_data()

    # Summary stats
    print(f"\n{'='*60}")
    print("SUMMARY STATISTICS (annualized)")
    print(f"{'='*60}")
    ann_return = returns.mean() * 252
    ann_vol = returns.std() * (252**0.5)
    sharpe = ann_return / ann_vol

    summary = pd.DataFrame({"CAGR (approx)": ann_return, "Volatility": ann_vol, "Sharpe": sharpe})
    print(summary.round(4))

    # Correlation matrix
    print(f"\nCorrelation matrix:")
    print(returns.corr().round(3))

    # Save
    save_data(prices, returns)

    return prices, returns


if __name__ == "__main__":
    main()
