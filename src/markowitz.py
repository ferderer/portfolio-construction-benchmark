"""
Markowitz Mean-Variance Optimization.

Rolling-window estimation of expected returns and covariance,
then optimize for maximum Sharpe ratio (tangent portfolio).

This implementation deliberately shows the practical problems:
  - Unstable covariance estimates from short windows
  - Extreme allocations (0% or 100% in single assets)
  - Sensitivity to input data

Parameters:
    lookback: rolling window for covariance estimation (default: 756 = 3 years)
    rebalance_frequency: reoptimize every N trading days (default: 21 = monthly)
    max_weight: maximum allocation per asset (default: 0.60)
"""

import numpy as np
import pandas as pd
from scipy.optimize import minimize


def _optimize_max_sharpe(
    expected_returns: np.ndarray,
    cov_matrix: np.ndarray,
    max_weight: float,
    risk_free_rate: float = 0.02 / 252,
) -> np.ndarray:
    """
    Find the tangent portfolio (max Sharpe ratio) via optimization.

    Long-only, fully invested, with optional max weight constraint.
    """
    n_assets = len(expected_returns)

    def neg_sharpe(w):
        port_ret = w @ expected_returns
        port_vol = np.sqrt(w @ cov_matrix @ w)
        if port_vol < 1e-10:
            return 0.0
        return -(port_ret - risk_free_rate) / port_vol

    constraints = [{"type": "eq", "fun": lambda w: w.sum() - 1.0}]
    bounds = [(0.0, max_weight) for _ in range(n_assets)]
    x0 = np.ones(n_assets) / n_assets

    result = minimize(
        neg_sharpe,
        x0,
        method="SLSQP",
        bounds=bounds,
        constraints=constraints,
        options={"maxiter": 1000, "ftol": 1e-12},
    )

    if result.success:
        return result.x
    else:
        # Fallback to equal weight if optimization fails
        return np.ones(n_assets) / n_assets


def run(
    prices: pd.DataFrame,
    lookback: int = 756,
    rebalance_frequency: int = 21,
    max_weight: float = 0.60,
    transaction_cost_bps: float = 0.0,
) -> tuple[pd.Series, pd.DataFrame]:
    """
    Run Markowitz backtest with rolling optimization.

    Args:
        prices: daily prices, DatetimeIndex
        lookback: rolling window for estimation (trading days)
        rebalance_frequency: reoptimize every N days
        max_weight: max allocation per asset (0.60 = no single asset > 60%)
        transaction_cost_bps: one-way cost per trade in basis points

    Returns:
        (portfolio_returns, weights_history)
    """
    tc = transaction_cost_bps / 10_000

    assets = list(prices.columns)
    returns = prices.pct_change().dropna()
    n_days = len(returns)

    weights = np.empty((n_days, len(assets)))
    portfolio_returns = np.empty(n_days)

    # Can't optimize until we have enough history
    current_weights = np.ones(len(assets)) / len(assets)

    for t in range(n_days):
        day_returns = returns.iloc[t].values

        # Portfolio return
        port_ret = np.dot(current_weights, day_returns)
        portfolio_returns[t] = port_ret

        # Drift weights
        new_weights = current_weights * (1 + day_returns)
        new_weights = new_weights / new_weights.sum()

        # Reoptimize at frequency, once we have enough data
        if t >= lookback and (t % rebalance_frequency == 0):
            hist_returns = returns.iloc[t - lookback : t]
            mu = hist_returns.mean().values
            cov = hist_returns.cov().values

            optimal = _optimize_max_sharpe(mu, cov, max_weight)

            # Transaction cost
            turnover = np.sum(np.abs(optimal - new_weights))
            cost = turnover * tc
            portfolio_returns[t] -= cost

            new_weights = optimal

        current_weights = new_weights
        weights[t] = current_weights

    port_ret_series = pd.Series(portfolio_returns, index=returns.index, name="Markowitz")
    weights_df = pd.DataFrame(weights, index=returns.index, columns=assets)

    return port_ret_series, weights_df
