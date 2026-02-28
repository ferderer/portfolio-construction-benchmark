"""
Black-Litterman portfolio construction with momentum-based views.

The model combines:
  1. Market equilibrium returns (CAPM prior) derived from market-cap weights
  2. Investor "views" — automated via dampened momentum signals

Improvements over naive momentum views:
  - Dampened: views are scaled by confidence factor (default 0.25)
  - Vol-scaled uncertainty: high-vol assets get wider confidence intervals
  - Relative views: "SPY outperforms EEM" rather than absolute return targets
  - Mean-reversion guard: extreme momentum gets capped

Parameters:
    lookback: window for covariance estimation (default: 756 = 3 years)
    momentum_window: lookback for momentum signals (default: 252 = 1 year)
    rebalance_frequency: reoptimize every N days (default: 21 = monthly)
    risk_aversion: market risk aversion parameter delta (default: 2.5)
    tau: scaling factor for uncertainty in prior (default: 0.05)
    max_weight: maximum allocation per asset (default: 0.60)
    view_confidence: how much to trust momentum signals (default: 0.25)
    transaction_cost_bps: one-way transaction cost in basis points (default: 0)
"""

import numpy as np
import pandas as pd
from scipy.optimize import minimize


# Approximate market-cap weights (simplified, ~2024)
MARKET_CAP_WEIGHTS = np.array([0.55, 0.15, 0.20, 0.10])


def _implied_equilibrium_returns(
    cov: np.ndarray,
    market_weights: np.ndarray,
    risk_aversion: float,
) -> np.ndarray:
    """Compute implied equilibrium returns: Pi = delta * Sigma * w_mkt."""
    return risk_aversion * cov @ market_weights


def _momentum_views(
    returns: pd.DataFrame,
    cov: np.ndarray,
    momentum_window: int,
    view_confidence: float,
) -> tuple[np.ndarray | None, np.ndarray | None, np.ndarray | None]:
    """
    Generate views from dampened, vol-scaled momentum signals.

    Combines absolute and relative views:
      - Absolute: each asset with significant momentum gets a dampened view
      - Relative: strongest vs weakest momentum asset (if spread is large enough)

    View uncertainty is proportional to asset volatility — the model
    is less confident about high-vol assets.

    Args:
        returns: historical returns for momentum calculation
        cov: current covariance matrix (for vol-scaling uncertainty)
        momentum_window: lookback period
        view_confidence: dampening factor (0.0 = ignore momentum, 1.0 = full momentum)

    Returns:
        (P, Q, omega) or (None, None, None) if no meaningful views
    """
    n_assets = returns.shape[1]
    asset_vols = np.sqrt(np.diag(cov)) * np.sqrt(252)  # annualized

    # Annualized momentum
    momentum = returns.iloc[-momentum_window:].mean() * 252

    views_P = []
    views_Q = []
    views_omega = []

    # --- Absolute views (dampened) ---
    for i in range(n_assets):
        mom = momentum.iloc[i]
        if abs(mom) > 0.03:  # 3% threshold
            pick = np.zeros(n_assets)
            pick[i] = 1.0
            views_P.append(pick)

            # Dampen strong momentum (mean-reversion guard)
            # Cap momentum contribution at ±15% annualized
            capped_mom = np.clip(mom, -0.15, 0.15)
            views_Q.append(capped_mom * view_confidence)

            # Uncertainty proportional to asset volatility squared
            # Higher vol → less confident → wider uncertainty
            omega_val = (asset_vols[i] * 0.5) ** 2
            views_omega.append(omega_val)

    # --- Relative view: strongest vs weakest ---
    mom_values = momentum.values
    best_idx = np.argmax(mom_values)
    worst_idx = np.argmin(mom_values)
    spread = mom_values[best_idx] - mom_values[worst_idx]

    if spread > 0.08 and best_idx != worst_idx:  # meaningful spread
        pick = np.zeros(n_assets)
        pick[best_idx] = 1.0
        pick[worst_idx] = -1.0
        views_P.append(pick)

        # Dampened spread view
        capped_spread = min(spread, 0.20)
        views_Q.append(capped_spread * view_confidence * 0.5)

        # Uncertainty: average of both assets' vols
        avg_vol = (asset_vols[best_idx] + asset_vols[worst_idx]) / 2
        views_omega.append((avg_vol * 0.6) ** 2)

    if len(views_P) == 0:
        return None, None, None

    P = np.array(views_P)
    Q = np.array(views_Q)
    omega = np.diag(views_omega)

    return P, Q, omega


def _black_litterman_returns(
    cov: np.ndarray,
    pi: np.ndarray,
    P: np.ndarray,
    Q: np.ndarray,
    omega: np.ndarray,
    tau: float,
) -> np.ndarray:
    """
    Combine equilibrium returns with views using Black-Litterman formula.

    mu_BL = [(tau*Sigma)^-1 + P'*Omega^-1*P]^-1
             * [(tau*Sigma)^-1 * Pi + P'*Omega^-1 * Q]
    """
    tau_cov_inv = np.linalg.inv(tau * cov)
    omega_inv = np.linalg.inv(omega)

    precision = tau_cov_inv + P.T @ omega_inv @ P
    mu_bl = np.linalg.solve(precision, tau_cov_inv @ pi + P.T @ omega_inv @ Q)

    return mu_bl


def _optimize_max_sharpe(
    expected_returns: np.ndarray,
    cov_matrix: np.ndarray,
    max_weight: float,
    risk_free_rate: float = 0.02 / 252,
) -> np.ndarray:
    """Max Sharpe optimization (same as Markowitz, but with BL returns)."""
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
        neg_sharpe, x0, method="SLSQP",
        bounds=bounds, constraints=constraints,
        options={"maxiter": 1000, "ftol": 1e-12},
    )
    return result.x if result.success else np.ones(n_assets) / n_assets


def run(
    prices: pd.DataFrame,
    lookback: int = 756,
    momentum_window: int = 252,
    rebalance_frequency: int = 21,
    risk_aversion: float = 2.5,
    tau: float = 0.05,
    max_weight: float = 0.60,
    view_confidence: float = 0.25,
    transaction_cost_bps: float = 0.0,
) -> tuple[pd.Series, pd.DataFrame]:
    """
    Run Black-Litterman backtest.

    Args:
        prices: daily prices
        lookback: covariance estimation window
        momentum_window: lookback for momentum views
        rebalance_frequency: reoptimize every N days
        risk_aversion: delta parameter for equilibrium returns
        tau: uncertainty scaling for prior
        max_weight: max allocation per asset
        view_confidence: dampening factor for momentum views (0.0–1.0)
        transaction_cost_bps: one-way cost per trade in basis points

    Returns:
        (portfolio_returns, weights_history)
    """
    tc = transaction_cost_bps / 10_000

    assets = list(prices.columns)
    returns = prices.pct_change().dropna()
    n_days = len(returns)
    n_assets = len(assets)

    weights = np.empty((n_days, n_assets))
    portfolio_returns = np.empty(n_days)

    current_weights = np.ones(n_assets) / n_assets
    market_weights = MARKET_CAP_WEIGHTS

    for t in range(n_days):
        day_returns = returns.iloc[t].values

        # Portfolio return
        port_ret = np.dot(current_weights, day_returns)
        portfolio_returns[t] = port_ret

        # Drift weights
        new_weights = current_weights * (1 + day_returns)
        new_weights = new_weights / new_weights.sum()

        # Reoptimize
        min_history = max(lookback, momentum_window)
        if t >= min_history and (t % rebalance_frequency == 0):
            hist_returns = returns.iloc[t - lookback : t]
            cov = hist_returns.cov().values

            # Equilibrium returns
            pi = _implied_equilibrium_returns(cov, market_weights, risk_aversion)

            # Momentum views (dampened, vol-scaled)
            momentum_hist = returns.iloc[t - momentum_window : t]
            P, Q, omega = _momentum_views(momentum_hist, cov, momentum_window, view_confidence)

            if P is not None:
                mu_bl = _black_litterman_returns(cov, pi, P, Q, omega, tau)
            else:
                mu_bl = pi

            optimal = _optimize_max_sharpe(mu_bl, cov, max_weight)

            # Transaction cost
            turnover = np.sum(np.abs(optimal - new_weights))
            cost = turnover * tc
            portfolio_returns[t] -= cost

            new_weights = optimal

        current_weights = new_weights
        weights[t] = current_weights

    port_ret_series = pd.Series(portfolio_returns, index=returns.index, name="BlackLitterman")
    weights_df = pd.DataFrame(weights, index=returns.index, columns=assets)

    return port_ret_series, weights_df
