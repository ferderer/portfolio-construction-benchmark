"""
Rule-based portfolio construction.

Fixed target allocation per risk profile with threshold-based rebalancing.
This is what most Robo-Advisors actually use in production.

Parameters:
    target_weights: fixed allocation (e.g., 60/15/20/5)
    threshold: rebalance when any asset drifts ±threshold from target
    check_frequency: how often to check (quarterly = every 63 trading days)
    transaction_cost_bps: one-way transaction cost in basis points (default: 0)
"""

import numpy as np
import pandas as pd


# Default: "Balanced Growth" profile
DEFAULT_TARGETS = {"SPY": 0.60, "EEM": 0.15, "AGG": 0.20, "VNQ": 0.05}


def run(
    prices: pd.DataFrame,
    target_weights: dict[str, float] | None = None,
    threshold: float = 0.05,
    check_frequency: int = 63,  # ~quarterly
    transaction_cost_bps: float = 0.0,
) -> tuple[pd.Series, pd.DataFrame]:
    """
    Run rule-based backtest.

    Args:
        prices: daily prices, DatetimeIndex, columns = asset tickers
        target_weights: target allocation per asset (must sum to 1.0)
        threshold: rebalance trigger (absolute deviation from target)
        check_frequency: check for rebalancing every N trading days
        transaction_cost_bps: one-way cost per trade in basis points
                              (e.g., 10.0 = 10 bps = 0.10%)

    Returns:
        (portfolio_returns, weights_history)
    """
    if target_weights is None:
        target_weights = DEFAULT_TARGETS

    tc = transaction_cost_bps / 10_000  # convert bps to decimal

    assets = list(target_weights.keys())
    targets = np.array([target_weights[a] for a in assets])
    assert abs(targets.sum() - 1.0) < 1e-9, f"Weights must sum to 1.0, got {targets.sum()}"

    prices = prices[assets]
    returns = prices.pct_change().dropna()
    n_days = len(returns)

    # Track weights over time
    weights = np.empty((n_days, len(assets)))
    portfolio_returns = np.empty(n_days)

    # Start with target allocation
    current_weights = targets.copy()

    for t in range(n_days):
        day_returns = returns.iloc[t].values

        # Portfolio return for this day
        port_ret = np.dot(current_weights, day_returns)
        portfolio_returns[t] = port_ret

        # Drift weights based on asset returns
        new_weights = current_weights * (1 + day_returns)
        new_weights = new_weights / new_weights.sum()

        # Check if rebalancing is needed (only at check_frequency intervals)
        if (t + 1) % check_frequency == 0:
            max_drift = np.max(np.abs(new_weights - targets))
            if max_drift > threshold:
                # Transaction cost: proportional to total weight turnover
                turnover = np.sum(np.abs(targets - new_weights))
                cost = turnover * tc
                portfolio_returns[t] -= cost

                new_weights = targets.copy()

        current_weights = new_weights
        weights[t] = current_weights

    port_ret_series = pd.Series(portfolio_returns, index=returns.index, name="RuleBased")
    weights_df = pd.DataFrame(weights, index=returns.index, columns=assets)

    return port_ret_series, weights_df
