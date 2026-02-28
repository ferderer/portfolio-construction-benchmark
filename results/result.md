Loading data...
  5098 price observations, 5097 return observations
  Period: 2004-09-29 to 2024-12-30
  Assets: ['SPY', 'EEM', 'AGG', 'VNQ']

======================================================================
RESULTS (no transaction costs)
======================================================================

                  CAGR Volatility Sharpe Max Drawdown Annual Turnover  Rebalance Count Tracking Error
Rule-Based       8.76%     15.89%  0.425       47.41%         101.91%              211          0.95%
Markowitz        8.15%     11.83%  0.520       33.99%         223.36%              677          7.45%
Black-Litterman  7.12%     23.27%  0.220       63.94%         236.38%              501          8.70%
Equal-Weight     7.70%     16.77%  0.340       48.58%         152.21%              445          4.10%

======================================================================
RESULTS (10 bps transaction costs)
======================================================================

                  CAGR Volatility Sharpe Max Drawdown Annual Turnover  Rebalance Count Tracking Error
Rule-Based       8.75%     15.89%  0.425       47.41%         101.91%              211          0.95%
Markowitz        8.03%     11.83%  0.510       34.08%         223.36%              677          7.45%
Black-Litterman  6.98%     23.27%  0.214       63.99%         236.38%              501          8.70%
Equal-Weight     7.69%     16.77%  0.339       48.59%         152.21%              445          4.10%

======================================================================
RESULTS (20 bps transaction costs)
======================================================================

                  CAGR Volatility Sharpe Max Drawdown Annual Turnover  Rebalance Count Tracking Error
Rule-Based       8.74%     15.89%  0.424       47.42%         101.91%              211          0.95%
Markowitz        7.92%     11.83%  0.500       34.18%         223.36%              677          7.45%
Black-Litterman  6.84%     23.27%  0.208       64.04%         236.38%              501          8.70%
Equal-Weight     7.68%     16.77%  0.338       48.60%         152.21%              445          4.10%

======================================================================
TRANSACTION COST IMPACT (CAGR reduction)
======================================================================
  Rule-Based            0 bps: 8.76%  →  10 bps: 8.75% (-0.01pp)  →  20 bps: 8.74% (-0.01pp)
  Markowitz             0 bps: 8.15%  →  10 bps: 8.03% (-0.11pp)  →  20 bps: 7.92% (-0.23pp)
  Black-Litterman       0 bps: 7.12%  →  10 bps: 6.98% (-0.14pp)  →  20 bps: 6.84% (-0.28pp)

======================================================================
ROBUSTNESS: ALTERNATIVE ALLOCATIONS (no transaction costs)
======================================================================
  Rule-Based (70/10/15/5):  CAGR=9.35%  Sharpe=0.440  MaxDD=48.93%  Turnover=81%
  Rule-Based (50/20/25/5):  CAGR=8.16%  Sharpe=0.404  MaxDD=45.19%  Turnover=119%

======================================================================
ROBUSTNESS: REBALANCING SENSITIVITY (60/15/20/5, no transaction costs)
======================================================================
  Monthly ±3%             CAGR=8.75%  Sharpe=0.425  MaxDD=46.91%  Turnover=103%  Rebalances=220
  Quarterly ±5%           CAGR=8.76%  Sharpe=0.425  MaxDD=47.41%  Turnover=102%  Rebalances=211
  Semi-annual ±10%        CAGR=9.36%  Sharpe=0.459  MaxDD=44.27%  Turnover=98%  Rebalances=178

----------------------------------------------------------------------
MARKOWITZ WEIGHT ANALYSIS (last 5 rebalance points)
----------------------------------------------------------------------
              SPY  EEM    AGG  VNQ
Date
2024-09-03  0.606  0.0  0.394  0.0
2024-10-09  0.600  0.0  0.400  0.0
2024-11-06  0.610  0.0  0.390  0.0
2024-11-07  0.600  0.0  0.400  0.0
2024-12-18  0.597  0.0  0.403  0.0

Markowitz weight statistics:
  SPY allocation range: 0.0% – 63.0%
  EEM allocation range: 0.0% – 45.5%
  AGG allocation range: 0.0% – 72.2%
  VNQ allocation range: 0.0% – 41.5%

Saved: summary_0bps.csv, summary_10bps.csv, summary_20bps.csv
Saved: cumulative_returns.csv
