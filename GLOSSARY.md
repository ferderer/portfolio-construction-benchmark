# Glossary

Terms you'll encounter in the article and codebase, explained for developers.

## Portfolio Construction

**Asset Allocation** — The split of money across asset classes (equities, bonds, REITs). A "60/15/20/5 allocation" means 60% in SPY, 15% in EEM, 20% in AGG, 5% in VNQ. This is the core decision every portfolio construction method makes.

**Rebalancing** — Resetting drifted weights back to target. If SPY rallies and grows from 60% to 68% of your portfolio, rebalancing sells SPY and buys the underweight assets to restore the target. The *when* and *how* of rebalancing is what distinguishes the three methods in this benchmark.

**Threshold-Based Rebalancing** — Only rebalance when an asset drifts beyond a defined band (e.g., ±5% from target). Avoids unnecessary trades in calm markets. Combined with a check frequency (e.g., quarterly) to limit operational overhead.

**Cash-Flow Rebalancing** — Using incoming deposits or withdrawals to adjust weights instead of trading existing positions. Common in production Robo-Advisors because it avoids transaction costs entirely. Not implemented in this benchmark to isolate the pure optimization comparison.

**Target Allocation / Risk Profile** — A fixed weight vector like `{SPY: 0.60, EEM: 0.15, AGG: 0.20, VNQ: 0.05}` assigned based on a client's risk tolerance. "Balanced Growth" is one of typically 5–7 profiles a Robo-Advisor offers.

## The Three Methods

**Mean-Variance Optimization (Markowitz)** — Harry Markowitz's 1952 framework. Given expected returns and a covariance matrix, find the portfolio weights that maximize return for a given risk level (or minimize risk for a given return). Elegant in theory. In practice, the optimizer is extremely sensitive to input estimates — small changes in the covariance matrix produce wildly different allocations.

**Efficient Frontier** — The set of all optimal portfolios from Markowitz optimization, plotted as return vs. risk. Every portfolio on the frontier offers the maximum possible return for its risk level. Portfolios below the frontier are suboptimal.

**Black-Litterman Model** — Published by Fischer Black and Robert Litterman (1992) at Goldman Sachs. Fixes Markowitz's input sensitivity by starting from market equilibrium returns (what the market "believes") and then overlaying investor views. Produces more stable allocations than raw Markowitz, but requires quantified views — which is the practical problem for Robo-Advisors.

**Market Equilibrium Returns (Prior)** — The implied expected returns that make current market-cap weights the optimal portfolio under CAPM. Calculated as `Π = δ × Σ × w_mkt` where δ is risk aversion, Σ is the covariance matrix, and w_mkt are market-cap weights. This is the "starting point" in Black-Litterman before views are applied.

**Investor Views** — Quantified beliefs about future returns that get merged with the equilibrium prior. Example: "SPY will outperform EEM by 3% annually." In this benchmark, views are generated automatically from momentum signals rather than human judgment.

**Tau (τ)** — A scalar in Black-Litterman that controls how much uncertainty is placed on the prior (equilibrium returns). Lower τ means more trust in the market equilibrium; higher τ means views have more influence. Typical values: 0.01–0.10.

## Metrics

**CAGR (Compound Annual Growth Rate)** — The annualized return accounting for compounding. $1 growing to $4 over 20 years = 7.2% CAGR. Unlike simple average return, CAGR accounts for the fact that a −50% loss requires a +100% gain to recover.

**Volatility** — Annualized standard deviation of daily returns. SPY at 19% volatility means roughly ±19% annual swing in a normal year. Used as the standard proxy for risk.

**Sharpe Ratio** — Risk-adjusted return: `(CAGR − risk-free rate) / volatility`. A Sharpe of 0.5 means you earn 0.5% excess return per 1% of risk. Higher is better. Allows comparing strategies with different risk levels on equal footing.

**Max Drawdown** — The largest peak-to-trough decline. A 47% max drawdown means the portfolio lost 47% from its highest point before recovering. Matters more to real clients than volatility — nobody panics about standard deviation, but they panic about seeing −47% on their statement.

**Turnover** — The total volume of trades as a percentage of portfolio value. 100% annual turnover means the entire portfolio was traded once per year. Higher turnover = higher transaction costs = lower net returns. This metric is the key differentiator between rule-based (low) and optimization-based (high) approaches.

**Tracking Error** — Annualized standard deviation of the return difference between a portfolio and its benchmark. A 0.95% tracking error against the target allocation means the portfolio stays very close to its intended profile. A 7.5% tracking error means the optimizer is doing something very different from what was promised to the client.

**Basis Points (bps)** — 1 bps = 0.01%. Transaction costs of "10 bps" means 0.10% per trade. Used because percentage differences at this scale are awkward to express. 100 bps = 1%.

## Momentum & Signals

**Momentum** — The empirical observation that assets that performed well recently tend to continue performing well in the short term (and vice versa). In this benchmark, 12-month trailing return is used as the momentum signal for Black-Litterman views.

**View Confidence / Dampening** — A scaling factor (0.0–1.0) applied to momentum signals before they become Black-Litterman views. At `view_confidence=0.25`, only 25% of the observed momentum feeds into the model. This prevents the optimizer from overreacting to recent trends.

**Relative View** — A view expressed as a spread between two assets ("SPY will outperform EEM by X%") rather than an absolute return target. More robust because relative relationships are more predictable than absolute returns.

## Risk & Covariance

**Covariance Matrix** — Measures how asset returns move together. The diagonal contains variances (volatilities squared), off-diagonals contain covariances. A 4-asset portfolio has a 4×4 matrix = 10 unique values. Markowitz optimization is notoriously sensitive to estimation errors in this matrix.

**Rolling Window** — Estimating the covariance matrix using only the last N days of data (e.g., 756 days = 3 years). The trade-off: shorter windows react faster to regime changes but produce noisier estimates. Longer windows are more stable but may include irrelevant historical regimes.

**Correlation Spike** — During crises, correlations between risky assets increase dramatically. SPY-EEM correlation goes from ~0.70 in normal markets to ~0.90 in a crash. This breaks diversification exactly when you need it most — and makes covariance estimates from calm periods misleading.

**Risk Aversion (δ)** — A parameter representing how much return an investor requires per unit of additional risk. Used in Black-Litterman to derive equilibrium returns. Higher δ = more risk-averse = equilibrium tilts toward bonds. Typical values: 2.0–3.0.

## Regulatory Context

**MiFID II** — EU regulation (Markets in Financial Instruments Directive II) governing investment services. Requires firms to demonstrate that investment decisions are *suitable* for each client — meaning the logic must be explainable. An optimizer that puts 0% in Emerging Markets and 60% in bonds based on covariance estimates is hard to justify in a suitability assessment.

**Geeignetheitsprüfung (Suitability Assessment)** — The MiFID II requirement that every investment recommendation must be appropriate for the specific client based on their knowledge, experience, financial situation, and risk tolerance. This is why "the model said so" is not an acceptable explanation in regulated financial services.

**BaFin** — Germany's Federal Financial Supervisory Authority (Bundesanstalt für Finanzdienstleistungsaufsicht). Supervises banks, insurance companies, and financial service providers including Robo-Advisors. Their auditors need to understand *why* the system made a specific allocation decision.

## Assets in This Benchmark

**SPY** — SPDR S&P 500 ETF. Tracks the 500 largest US companies. The most liquid ETF in the world. Represents "US Large Cap Equities" in the allocation.

**EEM** — iShares MSCI Emerging Markets ETF. Exposure to companies in China, Taiwan, India, Brazil, etc. Higher expected return, higher volatility, higher correlation with SPY during crises.

**AGG** — iShares Core US Aggregate Bond ETF. Broad US investment-grade bond exposure. Low volatility (~5%), low/negative correlation with equities. The portfolio's shock absorber.

**VNQ** — Vanguard Real Estate ETF. US REITs (Real Estate Investment Trusts). Historically high returns but devastating in real estate crises (−68% in GFC). The most volatile asset in this benchmark.
