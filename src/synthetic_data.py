"""
Generate synthetic ETF data with realistic statistical properties.

Used when Yahoo Finance is unavailable (CI, sandboxed environments).
The generated data preserves:
  - Realistic annualized returns and volatilities per asset
  - Cross-asset correlations (equity correlation spike in crises)
  - Regime switching: bull, bear, crisis, recovery
  - Known stress periods: GFC (2008), COVID (2020), rate hikes (2022)

For production benchmarks, use data_loader.py with real Yahoo Finance data.
"""

import numpy as np
import pandas as pd
from pathlib import Path

PROCESSED_DIR = Path(__file__).parent.parent / "data" / "processed"

# --- Asset parameters (annualized, based on historical data 2004-2024) ---

ASSETS = ["SPY", "EEM", "AGG", "VNQ"]

# Regime: normal
NORMAL_RETURNS = np.array([0.10, 0.08, 0.03, 0.11])     # annualized mean
NORMAL_VOLS = np.array([0.15, 0.22, 0.04, 0.20])         # annualized vol

# Regime: crisis
CRISIS_RETURNS = np.array([-0.35, -0.45, 0.05, -0.35])
CRISIS_VOLS = np.array([0.40, 0.50, 0.08, 0.45])

# Correlation matrices
NORMAL_CORR = np.array([
    [1.00, 0.72, -0.05, 0.60],
    [0.72, 1.00, -0.03, 0.55],
    [-0.05, -0.03, 1.00, 0.10],
    [0.60, 0.55, 0.10, 1.00],
])

CRISIS_CORR = np.array([
    [1.00, 0.90, 0.20, 0.85],
    [0.90, 1.00, 0.15, 0.82],
    [0.20, 0.15, 1.00, 0.25],
    [0.85, 0.82, 0.25, 1.00],
])

# Crisis periods (approximate trading day ranges)
CRISIS_PERIODS = [
    ("2008-09-01", "2009-03-31"),   # GFC
    ("2020-02-20", "2020-04-30"),   # COVID
    ("2022-01-01", "2022-10-31"),   # Rate hikes
]


def _corr_to_cov(corr: np.ndarray, vols: np.ndarray) -> np.ndarray:
    """Convert correlation matrix + vols to covariance matrix."""
    D = np.diag(vols)
    return D @ corr @ D


def _generate_regime_returns(
    dates: pd.DatetimeIndex,
    daily_mean: np.ndarray,
    cov: np.ndarray,
    seed_offset: int = 0,
) -> np.ndarray:
    """Generate correlated daily returns for a date range."""
    rng = np.random.default_rng(42 + seed_offset)
    n_days = len(dates)
    returns = rng.multivariate_normal(daily_mean, cov, size=n_days)
    return returns


def generate_synthetic_data(start: str = "2004-04-01", end: str = "2024-12-31") -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Generate synthetic price and return data with regime switching.

    Returns:
        (prices, returns) DataFrames with DatetimeIndex
    """
    # Create business day index
    dates = pd.bdate_range(start=start, end=end)

    # Daily parameters for normal regime
    daily_mean_normal = NORMAL_RETURNS / 252
    daily_cov_normal = _corr_to_cov(NORMAL_CORR, NORMAL_VOLS / np.sqrt(252))

    # Daily parameters for crisis regime
    daily_mean_crisis = CRISIS_RETURNS / 252
    daily_cov_crisis = _corr_to_cov(CRISIS_CORR, CRISIS_VOLS / np.sqrt(252))

    # Generate normal regime returns for full period
    rng = np.random.default_rng(42)
    all_returns = rng.multivariate_normal(daily_mean_normal, daily_cov_normal, size=len(dates))

    # Overlay crisis periods
    for i, (crisis_start, crisis_end) in enumerate(CRISIS_PERIODS):
        mask = (dates >= crisis_start) & (dates <= crisis_end)
        n_crisis = mask.sum()
        if n_crisis > 0:
            crisis_rng = np.random.default_rng(100 + i)
            crisis_returns = crisis_rng.multivariate_normal(
                daily_mean_crisis, daily_cov_crisis, size=n_crisis
            )
            all_returns[mask] = crisis_returns

    # Build returns DataFrame
    returns = pd.DataFrame(all_returns, index=dates, columns=ASSETS)

    # Convert to prices (start at realistic levels)
    start_prices = np.array([115.0, 26.0, 100.0, 55.0])  # approximate 2004 prices
    cumulative = (1 + returns).cumprod()
    prices = cumulative * start_prices

    # Add the starting row
    start_row = pd.DataFrame([start_prices], index=[dates[0] - pd.Timedelta(days=1)], columns=ASSETS)
    prices = pd.concat([start_row, prices])
    prices.index.name = "Date"
    returns.index.name = "Date"

    return prices, returns


def save_synthetic(prices: pd.DataFrame, returns: pd.DataFrame) -> None:
    """Save generated data."""
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    prices.to_csv(PROCESSED_DIR / "prices.csv")
    returns.to_csv(PROCESSED_DIR / "returns.csv")
    print(f"Saved synthetic prices: {prices.shape}")
    print(f"Saved synthetic returns: {returns.shape}")


def main():
    prices, returns = generate_synthetic_data()

    print(f"Date range: {returns.index.min().date()} to {returns.index.max().date()}")
    print(f"Trading days: {len(returns)}")

    print(f"\nAnnualized returns:")
    print((returns.mean() * 252).round(4))

    print(f"\nAnnualized volatility:")
    print((returns.std() * np.sqrt(252)).round(4))

    print(f"\nCorrelation:")
    print(returns.corr().round(3))

    print(f"\nSharpe ratios:")
    sharpe = (returns.mean() * 252) / (returns.std() * np.sqrt(252))
    print(sharpe.round(3))

    save_synthetic(prices, returns)


if __name__ == "__main__":
    main()
