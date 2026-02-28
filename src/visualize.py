"""
Visualizations for portfolio construction benchmark.

Charts:
  01. Cumulative performance (4 strategies)
  02. Drawdown comparison
  03. Weight evolution (per strategy)
  04. Markowitz weight instability
  05. Metrics comparison bars
  06. Turnover + rebalance count
  07. Rolling Sharpe ratio
  08. Transaction cost impact (grouped bars)
  09. Robustness: alternative allocations
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd

from src.data_loader import load_prices, load_returns
from src import rule_based, markowitz, black_litterman
from src.metrics import (
    cumulative_returns,
    drawdown_series,
    all_metrics,
    annual_turnover,
    rebalance_count,
    cagr,
)

# --- Style ---

COLORS = {
    "Rule-Based": "#2563eb",       # blue
    "Markowitz": "#dc2626",        # red
    "Black-Litterman": "#9333ea",  # purple
    "Equal-Weight": "#64748b",     # slate
}
ASSET_COLORS = {
    "SPY": "#2563eb",
    "EEM": "#059669",
    "AGG": "#d97706",
    "VNQ": "#dc2626",
}

FIGURES_DIR = Path(__file__).parent.parent / "results" / "figures"


def _setup_style():
    plt.rcParams.update({
        "figure.facecolor": "#0f172a",
        "axes.facecolor": "#0f172a",
        "axes.edgecolor": "#334155",
        "axes.labelcolor": "#e2e8f0",
        "text.color": "#e2e8f0",
        "xtick.color": "#94a3b8",
        "ytick.color": "#94a3b8",
        "grid.color": "#1e293b",
        "grid.alpha": 0.8,
        "legend.facecolor": "#1e293b",
        "legend.edgecolor": "#334155",
        "legend.labelcolor": "#e2e8f0",
        "font.family": "sans-serif",
        "font.size": 11,
        "axes.titlesize": 14,
        "axes.titleweight": "bold",
        "figure.titlesize": 16,
        "figure.titleweight": "bold",
        "savefig.dpi": 200,
        "savefig.bbox": "tight",
        "savefig.facecolor": "#0f172a",
    })


def _format_date_axis(ax):
    ax.xaxis.set_major_locator(mdates.YearLocator(2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.tick_params(axis="x", rotation=0)


# --- Chart functions ---

def plot_cumulative_performance(results: dict, save: bool = True) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(14, 6))

    for name, (ret, _) in results.items():
        cum = cumulative_returns(ret)
        ax.plot(cum.index, cum.values, label=name, color=COLORS[name],
                linewidth=1.8 if name == "Rule-Based" else 1.2,
                alpha=1.0 if name == "Rule-Based" else 0.8)

    ax.set_title("Cumulative Performance: $1 Invested (2004–2024)")
    ax.set_ylabel("Portfolio Value ($)")
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("$%.1f"))
    ax.legend(loc="upper left", framealpha=0.9)
    ax.grid(True, alpha=0.3)
    _format_date_axis(ax)

    if save:
        fig.savefig(FIGURES_DIR / "01_cumulative_performance.png")
    return fig


def plot_drawdowns(results: dict, save: bool = True) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(14, 5))

    for name, (ret, _) in results.items():
        dd = drawdown_series(ret)
        ax.fill_between(dd.index, dd.values, 0, alpha=0.15, color=COLORS[name])
        ax.plot(dd.index, dd.values, label=name, color=COLORS[name], linewidth=0.8)

    ax.set_title("Drawdowns")
    ax.set_ylabel("Drawdown")
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(1.0))
    ax.legend(loc="lower left", framealpha=0.9)
    ax.grid(True, alpha=0.3)
    _format_date_axis(ax)

    if save:
        fig.savefig(FIGURES_DIR / "02_drawdowns.png")
    return fig


def plot_weight_evolution(results: dict, save: bool = True) -> list[plt.Figure]:
    figs = []
    for idx, (name, (_, weights)) in enumerate(results.items(), start=1):
        fig, ax = plt.subplots(figsize=(14, 4))

        w_weekly = weights.resample("W").last()
        ax.stackplot(
            w_weekly.index,
            [w_weekly[col].values for col in weights.columns],
            labels=weights.columns,
            colors=[ASSET_COLORS[col] for col in weights.columns],
            alpha=0.85,
        )

        ax.set_title(f"Weight Evolution: {name}")
        ax.set_ylabel("Allocation")
        ax.set_ylim(0, 1)
        ax.yaxis.set_major_formatter(mticker.PercentFormatter(1.0))
        ax.legend(loc="upper right", ncol=4, framealpha=0.9)
        ax.grid(True, alpha=0.3)
        _format_date_axis(ax)

        if save:
            fig.savefig(FIGURES_DIR / f"03{chr(96+idx)}_weights_{name.lower().replace('-', '_')}.png")
        figs.append(fig)

    return figs


def plot_markowitz_instability(mk_weights: pd.DataFrame, save: bool = True) -> plt.Figure:
    fig, axes = plt.subplots(2, 2, figsize=(14, 8), sharex=True)

    for ax, asset in zip(axes.flat, mk_weights.columns):
        w = mk_weights[asset]
        ax.plot(w.index, w.values, color=ASSET_COLORS[asset], linewidth=0.6, alpha=0.9)
        ax.axhline(y=0, color="#475569", linewidth=0.5, linestyle="--")
        ax.set_title(asset, fontsize=12)
        ax.set_ylabel("Weight")
        ax.yaxis.set_major_formatter(mticker.PercentFormatter(1.0))
        ax.set_ylim(-0.02, 0.75)
        ax.grid(True, alpha=0.3)
        _format_date_axis(ax)

    fig.suptitle("Markowitz: Weight Instability Per Asset", y=1.02)
    fig.tight_layout()

    if save:
        fig.savefig(FIGURES_DIR / "04_markowitz_instability.png")
    return fig


def plot_metrics_comparison(results: dict, save: bool = True) -> plt.Figure:
    target = {"SPY": 0.60, "EEM": 0.15, "AGG": 0.20, "VNQ": 0.05}
    prices = load_prices()
    returns = prices.pct_change().dropna()
    benchmark_ret = sum(returns[a] * w for a, w in target.items())

    metrics_data = {}
    for name, (ret, wgt) in results.items():
        metrics_data[name] = all_metrics(ret, wgt, benchmark_returns=benchmark_ret)

    display_metrics = ["CAGR", "Volatility", "Sharpe", "Max Drawdown"]
    names = list(results.keys())

    fig, axes = plt.subplots(1, 4, figsize=(18, 5))

    for ax, metric in zip(axes, display_metrics):
        values = [metrics_data[name][metric] for name in names]
        x = range(len(names))
        bars = ax.bar(x, values, color=[COLORS[n] for n in names], width=0.6, alpha=0.9)

        ax.set_title(metric, fontsize=12)
        ax.set_xticks(list(x))
        ax.set_xticklabels(names, rotation=30, ha="right", fontsize=8)
        ax.grid(True, axis="y", alpha=0.3)

        if metric in ("CAGR", "Volatility", "Max Drawdown"):
            ax.yaxis.set_major_formatter(mticker.PercentFormatter(1.0))
            fmt = lambda v: f"{v:.1%}"
        else:
            ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.2f"))
            fmt = lambda v: f"{v:.3f}"

        for bar, val in zip(bars, values):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.003,
                    fmt(val), ha="center", va="bottom", fontsize=8, color="#e2e8f0")

    fig.suptitle("Performance Metrics Comparison", y=1.02)
    fig.tight_layout()

    if save:
        fig.savefig(FIGURES_DIR / "05_metrics_comparison.png")
    return fig


def plot_turnover_comparison(results: dict, save: bool = True) -> plt.Figure:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    names = list(results.keys())
    x = range(len(names))

    turnovers = [annual_turnover(wgt) for _, (_, wgt) in results.items()]
    rebalances = [rebalance_count(wgt) for _, (_, wgt) in results.items()]

    bars1 = ax1.bar(x, turnovers, color=[COLORS[n] for n in names], width=0.6, alpha=0.9)
    ax1.set_title("Annual Turnover", fontsize=12)
    ax1.yaxis.set_major_formatter(mticker.PercentFormatter(1.0))
    ax1.set_xticks(list(x))
    ax1.set_xticklabels(names, rotation=30, ha="right", fontsize=9)
    ax1.grid(True, axis="y", alpha=0.3)
    for bar, val in zip(bars1, turnovers):
        ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.02,
                 f"{val:.0%}", ha="center", va="bottom", fontsize=10, color="#e2e8f0")

    bars2 = ax2.bar(x, rebalances, color=[COLORS[n] for n in names], width=0.6, alpha=0.9)
    ax2.set_title("Rebalancing Events (20 years)", fontsize=12)
    ax2.set_xticks(list(x))
    ax2.set_xticklabels(names, rotation=30, ha="right", fontsize=9)
    ax2.grid(True, axis="y", alpha=0.3)
    for bar, val in zip(bars2, rebalances):
        ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 5,
                 str(val), ha="center", va="bottom", fontsize=10, color="#e2e8f0")

    fig.suptitle("Operational Complexity")
    fig.tight_layout(rect=[0, 0, 1, 0.95])

    if save:
        fig.savefig(FIGURES_DIR / "06_turnover_comparison.png")
    return fig


def plot_rolling_sharpe(results: dict, window: int = 252, save: bool = True) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(14, 5))

    for name, (ret, _) in results.items():
        rolling_mean = ret.rolling(window).mean() * 252
        rolling_std = ret.rolling(window).std() * np.sqrt(252)
        rolling_sharpe = (rolling_mean - 0.02) / rolling_std
        rolling_sharpe = rolling_sharpe.dropna()

        ax.plot(rolling_sharpe.index, rolling_sharpe.values,
                label=name, color=COLORS[name],
                linewidth=1.2 if name == "Rule-Based" else 0.8,
                alpha=1.0 if name in ("Rule-Based", "Markowitz") else 0.7)

    ax.axhline(y=0, color="#475569", linewidth=0.5, linestyle="--")
    ax.set_title("Rolling 1-Year Sharpe Ratio")
    ax.set_ylabel("Sharpe Ratio")
    ax.legend(loc="upper right", framealpha=0.9)
    ax.grid(True, alpha=0.3)
    _format_date_axis(ax)

    if save:
        fig.savefig(FIGURES_DIR / "07_rolling_sharpe.png")
    return fig


def plot_transaction_cost_impact(prices: pd.DataFrame, save: bool = True) -> plt.Figure:
    """Chart 08: Grouped bar chart showing CAGR at 0, 10, 20 bps."""
    tc_levels = [0, 10, 20]
    strategies = ["Rule-Based", "Markowitz", "Black-Litterman", "Equal-Weight"]

    # Run all combinations
    cagr_matrix = {}
    for tc in tc_levels:
        rb_ret, _ = rule_based.run(prices, transaction_cost_bps=tc)
        mk_ret, _ = markowitz.run(prices, transaction_cost_bps=tc)
        bl_ret, _ = black_litterman.run(prices, transaction_cost_bps=tc)

        eq_targets = {"SPY": 0.25, "EEM": 0.25, "AGG": 0.25, "VNQ": 0.25}
        eq_ret, _ = rule_based.run(prices, target_weights=eq_targets, transaction_cost_bps=tc)

        cagr_matrix[tc] = {
            "Rule-Based": cagr(rb_ret),
            "Markowitz": cagr(mk_ret),
            "Black-Litterman": cagr(bl_ret),
            "Equal-Weight": cagr(eq_ret),
        }

    fig, ax = plt.subplots(figsize=(14, 6))

    bar_width = 0.22
    x = np.arange(len(strategies))

    tc_colors = ["#22c55e", "#eab308", "#ef4444"]  # green, yellow, red
    tc_labels = ["0 bps", "10 bps", "20 bps"]

    for i, tc in enumerate(tc_levels):
        values = [cagr_matrix[tc][s] for s in strategies]
        offset = (i - 1) * bar_width
        bars = ax.bar(x + offset, values, bar_width, label=tc_labels[i],
                      color=tc_colors[i], alpha=0.85)

        for bar, val in zip(bars, values):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.001,
                    f"{val:.2%}", ha="center", va="bottom", fontsize=8, color="#e2e8f0")

    # Add drag annotations
    for j, strat in enumerate(strategies):
        drag = cagr_matrix[20][strat] - cagr_matrix[0][strat]
        y_pos = max(cagr_matrix[0][strat], cagr_matrix[20][strat]) + 0.006
        ax.text(j, y_pos, f"drag: {drag*100:+.2f}pp",
                ha="center", fontsize=9, color="#94a3b8", style="italic")

    ax.set_title("CAGR at Different Transaction Cost Levels")
    ax.set_xticks(list(x))
    ax.set_xticklabels(strategies, fontsize=10)
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(1.0))
    ax.legend(loc="upper right", framealpha=0.9)
    ax.grid(True, axis="y", alpha=0.3)
    ax.set_ylim(0, ax.get_ylim()[1] * 1.12)

    fig.tight_layout()

    if save:
        fig.savefig(FIGURES_DIR / "08_transaction_cost_impact.png")
    return fig


def plot_robustness(prices: pd.DataFrame, save: bool = True) -> plt.Figure:
    """Chart 09: Rule-based variants vs Markowitz/BL."""
    variants = {
        "RB 50/20/25/5": {"SPY": 0.50, "EEM": 0.20, "AGG": 0.25, "VNQ": 0.05},
        "RB 60/15/20/5": {"SPY": 0.60, "EEM": 0.15, "AGG": 0.20, "VNQ": 0.05},
        "RB 70/10/15/5": {"SPY": 0.70, "EEM": 0.10, "AGG": 0.15, "VNQ": 0.05},
    }

    # Run rule-based variants
    rb_results = {}
    for label, targets in variants.items():
        ret, wgt = rule_based.run(prices, target_weights=targets)
        rb_results[label] = {"CAGR": cagr(ret), "Turnover": annual_turnover(wgt)}

    # Run optimizers for comparison
    mk_ret, mk_wgt = markowitz.run(prices)
    bl_ret, bl_wgt = black_litterman.run(prices)

    all_strats = {
        **rb_results,
        "Markowitz": {"CAGR": cagr(mk_ret), "Turnover": annual_turnover(mk_wgt)},
        "Black-Litterman": {"CAGR": cagr(bl_ret), "Turnover": annual_turnover(bl_wgt)},
    }

    fig, ax = plt.subplots(figsize=(12, 7))

    colors_map = {
        "RB 50/20/25/5": "#60a5fa",   # light blue
        "RB 60/15/20/5": "#2563eb",   # blue (default)
        "RB 70/10/15/5": "#1d4ed8",   # dark blue
        "Markowitz": "#dc2626",
        "Black-Litterman": "#9333ea",
    }

    for name, data in all_strats.items():
        ax.scatter(data["Turnover"], data["CAGR"],
                   color=colors_map[name], s=200, zorder=5, edgecolors="white", linewidth=1.5)
        # Label offset
        x_off = 0.03 if "RB" in name else -0.03
        ha = "left" if "RB" in name else "right"
        ax.annotate(name, (data["Turnover"], data["CAGR"]),
                    textcoords="offset points", xytext=(12 if "RB" in name else -12, 8),
                    fontsize=10, color=colors_map[name], ha=ha,
                    fontweight="bold")

    # Draw a shaded region around rule-based variants
    rb_turnovers = [d["Turnover"] for n, d in all_strats.items() if "RB" in n]
    rb_cagrs = [d["CAGR"] for n, d in all_strats.items() if "RB" in n]
    ax.axhspan(min(rb_cagrs) - 0.003, max(rb_cagrs) + 0.003,
               alpha=0.08, color="#2563eb", zorder=0)

    ax.set_title("Robustness: CAGR vs. Annual Turnover")
    ax.set_xlabel("Annual Turnover")
    ax.set_ylabel("CAGR")
    ax.xaxis.set_major_formatter(mticker.PercentFormatter(1.0))
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(1.0))
    ax.grid(True, alpha=0.3)

    fig.tight_layout()

    if save:
        fig.savefig(FIGURES_DIR / "09_robustness.png")
    return fig


def generate_all():
    """Generate all charts."""
    _setup_style()
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading data...")
    prices = load_prices()

    print("Running strategies...")
    rb_ret, rb_wgt = rule_based.run(prices)
    mk_ret, mk_wgt = markowitz.run(prices)
    bl_ret, bl_wgt = black_litterman.run(prices)

    eq_targets = {"SPY": 0.25, "EEM": 0.25, "AGG": 0.25, "VNQ": 0.25}
    eq_ret, eq_wgt = rule_based.run(prices, target_weights=eq_targets)

    results = {
        "Rule-Based": (rb_ret, rb_wgt),
        "Markowitz": (mk_ret, mk_wgt),
        "Black-Litterman": (bl_ret, bl_wgt),
        "Equal-Weight": (eq_ret, eq_wgt),
    }

    print("Generating charts...")

    print("  01 Cumulative Performance")
    plot_cumulative_performance(results)

    print("  02 Drawdowns")
    plot_drawdowns(results)

    print("  03 Weight Evolution (3 strategies, skip Equal-Weight)")
    core = {k: v for k, v in results.items() if k != "Equal-Weight"}
    plot_weight_evolution(core)

    print("  04 Markowitz Instability")
    plot_markowitz_instability(mk_wgt)

    print("  05 Metrics Comparison")
    plot_metrics_comparison(results)

    print("  06 Turnover Comparison")
    plot_turnover_comparison(results)

    print("  07 Rolling Sharpe")
    plot_rolling_sharpe(results)

    print("  08 Transaction Cost Impact")
    plot_transaction_cost_impact(prices)

    print("  09 Robustness")
    plot_robustness(prices)

    print(f"\nAll charts saved to {FIGURES_DIR}/")
    plt.close("all")


if __name__ == "__main__":
    generate_all()
