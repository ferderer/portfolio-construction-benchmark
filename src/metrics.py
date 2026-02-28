"""
Portfolio performance metrics.

All functions expect:
  - portfolio_returns: pd.Series with daily portfolio returns
  - weights_history: pd.DataFrame (dates x assets) for turnover/tracking
"""

import numpy as np
import pandas as pd

TRADING_DAYS = 252


def cagr(portfolio_returns: pd.Series) -> float:
    """Compound Annual Growth Rate."""
    cumulative = (1 + portfolio_returns).prod()
    n_years = len(portfolio_returns) / TRADING_DAYS
    return cumulative ** (1 / n_years) - 1


def annualized_volatility(portfolio_returns: pd.Series) -> float:
    """Annualized standard deviation of returns."""
    return portfolio_returns.std() * np.sqrt(TRADING_DAYS)


def sharpe_ratio(portfolio_returns: pd.Series, risk_free_rate: float = 0.02) -> float:
    """Annualized Sharpe ratio."""
    excess = cagr(portfolio_returns) - risk_free_rate
    vol = annualized_volatility(portfolio_returns)
    return excess / vol if vol > 0 else 0.0


def max_drawdown(portfolio_returns: pd.Series) -> float:
    """Maximum drawdown (returned as positive number, e.g. 0.35 = 35%)."""
    cumulative = (1 + portfolio_returns).cumprod()
    running_max = cumulative.cummax()
    drawdown = (cumulative - running_max) / running_max
    return abs(drawdown.min())


def drawdown_series(portfolio_returns: pd.Series) -> pd.Series:
    """Full drawdown time series."""
    cumulative = (1 + portfolio_returns).cumprod()
    running_max = cumulative.cummax()
    return (cumulative - running_max) / running_max


def annual_turnover(weights_history: pd.DataFrame) -> float:
    """
    Average annual turnover.

    Turnover = sum of absolute weight changes per rebalance.
    Annualized by scaling to 252 trading days.
    """
    if len(weights_history) < 2:
        return 0.0
    diffs = weights_history.diff().dropna()
    daily_turnover = diffs.abs().sum(axis=1)
    total_turnover = daily_turnover.sum()
    n_years = len(weights_history) / TRADING_DAYS
    return total_turnover / n_years


def tracking_error(
    portfolio_returns: pd.Series,
    benchmark_returns: pd.Series,
) -> float:
    """Annualized tracking error vs. a benchmark (e.g., target allocation)."""
    diff = portfolio_returns - benchmark_returns
    return diff.std() * np.sqrt(TRADING_DAYS)


def rebalance_count(weights_history: pd.DataFrame, threshold: float = 0.005) -> int:
    """Count number of actual rebalancing events (weight change > threshold)."""
    if len(weights_history) < 2:
        return 0
    diffs = weights_history.diff().dropna()
    # A rebalance event is when the max single-asset weight change exceeds threshold
    max_change_per_day = diffs.abs().max(axis=1)
    return (max_change_per_day > threshold).sum()


def cumulative_returns(portfolio_returns: pd.Series) -> pd.Series:
    """Cumulative return series (starting at 1.0)."""
    return (1 + portfolio_returns).cumprod()


def all_metrics(
    portfolio_returns: pd.Series,
    weights_history: pd.DataFrame,
    benchmark_returns: pd.Series | None = None,
    risk_free_rate: float = 0.02,
) -> dict:
    """Compute all metrics as a dictionary."""
    result = {
        "CAGR": cagr(portfolio_returns),
        "Volatility": annualized_volatility(portfolio_returns),
        "Sharpe": sharpe_ratio(portfolio_returns, risk_free_rate),
        "Max Drawdown": max_drawdown(portfolio_returns),
        "Annual Turnover": annual_turnover(weights_history),
        "Rebalance Count": rebalance_count(weights_history),
    }
    if benchmark_returns is not None:
        result["Tracking Error"] = tracking_error(portfolio_returns, benchmark_returns)
    return result
