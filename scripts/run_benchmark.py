"""
Run all three portfolio construction strategies on the same data
and compare results.

Usage: python -m scripts.run_benchmark
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from src.data_loader import load_prices, load_returns
from src import rule_based, markowitz, black_litterman
from src.metrics import all_metrics


def run_strategies(prices, returns, tc_bps: float = 0.0) -> dict:
    """Run all strategies with given transaction cost."""
    rb_ret, rb_wgt = rule_based.run(prices, transaction_cost_bps=tc_bps)
    mk_ret, mk_wgt = markowitz.run(prices, transaction_cost_bps=tc_bps)
    bl_ret, bl_wgt = black_litterman.run(prices, transaction_cost_bps=tc_bps)

    # 1/N equal-weight benchmark
    equal_targets = {"SPY": 0.25, "EEM": 0.25, "AGG": 0.25, "VNQ": 0.25}
    eq_ret, eq_wgt = rule_based.run(prices, target_weights=equal_targets, transaction_cost_bps=tc_bps)

    return {
        "Rule-Based": (rb_ret, rb_wgt),
        "Markowitz": (mk_ret, mk_wgt),
        "Black-Litterman": (bl_ret, bl_wgt),
        "Equal-Weight": (eq_ret, eq_wgt),
    }


def print_results(strategies: dict, returns: pd.DataFrame, label: str = ""):
    """Print formatted results table."""
    target = {"SPY": 0.60, "EEM": 0.15, "AGG": 0.20, "VNQ": 0.05}
    benchmark_returns = sum(returns[a] * w for a, w in target.items())

    results = {}
    for name, (ret, wgt) in strategies.items():
        m = all_metrics(ret, wgt, benchmark_returns=benchmark_returns)
        results[name] = m

    df = pd.DataFrame(results).T
    df["CAGR"] = df["CAGR"].map("{:.2%}".format)
    df["Volatility"] = df["Volatility"].map("{:.2%}".format)
    df["Sharpe"] = df["Sharpe"].map("{:.3f}".format)
    df["Max Drawdown"] = df["Max Drawdown"].map("{:.2%}".format)
    df["Annual Turnover"] = df["Annual Turnover"].map("{:.2%}".format)
    df["Rebalance Count"] = df["Rebalance Count"].astype(int)
    df["Tracking Error"] = df["Tracking Error"].map("{:.2%}".format)

    print(f"\n{df.to_string()}")
    return results


def main():
    print("Loading data...")
    prices = load_prices()
    returns = load_returns()
    print(f"  {len(prices)} price observations, {len(returns)} return observations")
    print(f"  Period: {prices.index.min().date()} to {prices.index.max().date()}")
    print(f"  Assets: {list(prices.columns)}")

    # Benchmark for tracking error
    target = {"SPY": 0.60, "EEM": 0.15, "AGG": 0.20, "VNQ": 0.05}
    benchmark_returns = sum(returns[a] * w for a, w in target.items())

    # --- Run without transaction costs ---
    print("\n" + "=" * 70)
    print("RESULTS (no transaction costs)")
    print("=" * 70)

    strategies_0 = run_strategies(prices, returns, tc_bps=0.0)
    raw_0 = print_results(strategies_0, returns)

    # --- Run with 10 bps transaction costs ---
    print("\n" + "=" * 70)
    print("RESULTS (10 bps transaction costs)")
    print("=" * 70)

    strategies_10 = run_strategies(prices, returns, tc_bps=10.0)
    raw_10 = print_results(strategies_10, returns)

    # --- Run with 20 bps transaction costs ---
    print("\n" + "=" * 70)
    print("RESULTS (20 bps transaction costs)")
    print("=" * 70)

    strategies_20 = run_strategies(prices, returns, tc_bps=20.0)
    raw_20 = print_results(strategies_20, returns)

    # --- Cost impact summary ---
    print("\n" + "=" * 70)
    print("TRANSACTION COST IMPACT (CAGR reduction)")
    print("=" * 70)
    for name in ["Rule-Based", "Markowitz", "Black-Litterman"]:
        cagr_0 = raw_0[name]["CAGR"]
        cagr_10 = raw_10[name]["CAGR"]
        cagr_20 = raw_20[name]["CAGR"]
        print(f"  {name:20s}  0 bps: {cagr_0:.2%}  →  10 bps: {cagr_10:.2%} ({(cagr_10-cagr_0)*100:+.2f}pp)"
              f"  →  20 bps: {cagr_20:.2%} ({(cagr_20-cagr_0)*100:+.2f}pp)")

    # --- Robustness: alternative allocation ---
    print("\n" + "=" * 70)
    print("ROBUSTNESS: ALTERNATIVE ALLOCATIONS (no transaction costs)")
    print("=" * 70)

    alt_targets = {
        "70/10/15/5": {"SPY": 0.70, "EEM": 0.10, "AGG": 0.15, "VNQ": 0.05},
        "50/20/25/5": {"SPY": 0.50, "EEM": 0.20, "AGG": 0.25, "VNQ": 0.05},
    }
    for label, targets in alt_targets.items():
        alt_ret, alt_wgt = rule_based.run(prices, target_weights=targets, transaction_cost_bps=0.0)
        m = all_metrics(alt_ret, alt_wgt, benchmark_returns=benchmark_returns)
        print(f"  Rule-Based ({label}):  CAGR={m['CAGR']:.2%}  Sharpe={m['Sharpe']:.3f}"
              f"  MaxDD={m['Max Drawdown']:.2%}  Turnover={m['Annual Turnover']:.0%}")

    # --- Robustness: rebalancing frequency/threshold sensitivity ---
    print("\n" + "=" * 70)
    print("ROBUSTNESS: REBALANCING SENSITIVITY (60/15/20/5, no transaction costs)")
    print("=" * 70)

    rebal_configs = [
        ("Monthly ±3%",      21,  0.03),
        ("Quarterly ±5%",    63,  0.05),  # default
        ("Semi-annual ±10%", 126, 0.10),
    ]
    for label, freq, thresh in rebal_configs:
        r_ret, r_wgt = rule_based.run(prices, check_frequency=freq, threshold=thresh, transaction_cost_bps=0.0)
        m = all_metrics(r_ret, r_wgt, benchmark_returns=benchmark_returns)
        print(f"  {label:22s}  CAGR={m['CAGR']:.2%}  Sharpe={m['Sharpe']:.3f}"
              f"  MaxDD={m['Max Drawdown']:.2%}  Turnover={m['Annual Turnover']:.0%}  Rebalances={m['Rebalance Count']}")

    # --- Markowitz weight analysis ---
    mk_weights = strategies_0["Markowitz"][1]
    print("\n" + "-" * 70)
    print("MARKOWITZ WEIGHT ANALYSIS (last 5 rebalance points)")
    print("-" * 70)
    mk_diffs = mk_weights.diff().abs().sum(axis=1)
    rebal_dates = mk_diffs[mk_diffs > 0.01].index[-5:]
    if len(rebal_dates) > 0:
        print(mk_weights.loc[rebal_dates].round(3).to_string())

    print("\nMarkowitz weight statistics:")
    for col in mk_weights.columns:
        print(f"  {col} allocation range: {mk_weights[col].min():.1%} – {mk_weights[col].max():.1%}")

    # Save results
    results_dir = Path(__file__).parent.parent / "results"
    results_dir.mkdir(exist_ok=True)

    pd.DataFrame(raw_0).T.to_csv(results_dir / "summary_0bps.csv")
    pd.DataFrame(raw_10).T.to_csv(results_dir / "summary_10bps.csv")
    pd.DataFrame(raw_20).T.to_csv(results_dir / "summary_20bps.csv")
    print(f"\nSaved: summary_0bps.csv, summary_10bps.csv, summary_20bps.csv")

    # Save cumulative returns (0 bps for charting)
    from src.metrics import cumulative_returns
    cum = pd.DataFrame({
        "RuleBased": cumulative_returns(strategies_0["Rule-Based"][0]),
        "Markowitz": cumulative_returns(strategies_0["Markowitz"][0]),
        "BlackLitterman": cumulative_returns(strategies_0["Black-Litterman"][0]),
    })
    cum.to_csv(results_dir / "cumulative_returns.csv")
    print(f"Saved: cumulative_returns.csv")


if __name__ == "__main__":
    main()
