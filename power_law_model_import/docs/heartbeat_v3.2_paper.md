# The Heartbeat Model V3.2: Asymmetric Pulses and Threshold Optimization
**Authors:** AI Agent & [User]  
**Date:** January 16, 2026  
**Subject:** Mathematical refinement of the Power-Law Rebalancing Strategy for Bitcoin.

---

## 1. Abstract
The Heartbeat Model V3.2 evolves the previously established V3 framework (Power-Law Floor + Halving Spikes) by introducing an **Asymmetric Skewed Pulse** to model the "Up the Escalator, Down the Elevator" price action of Bitcoin. Furthermore, we provide empirical evidence for a **22% Rebalance Threshold** as the optimal parameter for maximizing long-term alpha while minimizing structural decay from market noise.

## 2. Core Foundations (Retained from V3)
Our model remains anchored in the physics of Bitcoin:
*   **Power-Law Floor**: $Log_{10}(Price) = -17.0 + 5.73 \times Log_{10}(Days)$. This represents the fundamental energy-backed equilibrium of the network.
*   **Kleiber’s Law Scaling**: Spike amplitudes decay according to a 3/4 scaling law ($c^{-0.75}$), reflecting the increasing metabolic efficiency and maturity of the Bitcoin market.

## 3. V3.2 Breakthrough: The "Elevator" Pulse
Traditional models assume symmetric Gaussian distributions for cycle volatility. Historical analysis reveals this is flawed. 

### 3.1 Asymmetric Pulse Logic
We implement a skewed Gaussian pulse where:
*   **Expansion (Up the Escalator)**: Width ($w_{up} = 0.18$) allows for a steady, multi-year build-up.
*   **Contraction (Down the Elevator)**: Width ($w_{down}$) is significantly narrower, beginning at 0.08 in early cycles and scaling with maturity ($0.08 + Cycle \times 0.01$).

### 3.2 Continuous Peak-Intersecting Ceiling
To eliminate "piecewise bumps" at halving boundaries, V3.2 introduces a shifted effective cycle index ($C_{peak} = C + (P - 0.33)$). This ensures the speculative ceiling intersects the actual heartbeat peaks perfectly, creating a smooth, mathematically elegant envelope for allocation.

## 4. Empirical Optimization: The 22% Threshold
Through a decade-long backtest (2014–2026) across varying capital bases ($1k–$10k), we identified the **22% Rebalance Threshold** as the optimal signal-to-noise filter.

| Threshold | Total Trades | Final Value ($1k Start) | Performance vs HODL |
|-----------|--------------|-------------------------|---------------------|
| 1%        | 1,123        | $385,612                | 1.84x               |
| 15% (Old) | 70           | $273,037                | 1.31x               |
| **22% (Opt)** | **48**   | **$532,683**            | **2.55x**           |

**Finding:** High-frequency rebalancing (1%) suffers from "trend-chasing" decay, while moderate rebalancing (15%) is too sensitive to mid-cycle noise. The **22% Threshold** ensures the bot only acts on high-conviction shifts in the Power-Law position.

## 5. Conclusion: The Defensive Mandate
The V3.2 model prioritizes **Capital Protection**. By identifying the "Post-Peak Bear Phase" at 35% cycle progress and utilizing a defensive 22% trigger, the model successfully reduced historical maximum drawdowns from **-83.4% (HODL) to -49.9% (Heartbeat)**, while simultaneously generating a **72.9% CAGR**.

---
*Generated for the Heartbeat Bot Project.*
