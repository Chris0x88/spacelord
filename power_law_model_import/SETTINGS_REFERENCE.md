# Settings & Configuration Reference

All settings are set via environment variables (`.env` file or deployment platform).

---

## Rebalancing Settings (Most Important)

| Variable | Default | Research Notes |
|----------|---------|----------------|
| `REBALANCE_THRESHOLD_PERCENT` | **15.0** | **Optimal.** 15% threshold achieves 1.51x vs HODL. Lower = more trades = worse performance. Raise to 20% for tax-optimization. |
| `EXTREME_THRESHOLD_PERCENT` | 5.0 | For sudden large moves — triggers an immediate rebalance regardless of schedule |
| `REBALANCE_INTERVAL_SECONDS` | 3600 | How often the bot checks (3600=hourly, 86400=daily). More frequent = more responsive but more noise. |

### Threshold Quick Reference

| Threshold | Trades/yr | vs HODL | Use Case |
|-----------|-----------|---------|----------|
| 5% | 200+ | 0.90x | Too noisy — don't use |
| 10% | ~15 | 1.20x | OK, lower gains |
| **15%** | **~10** | **1.51x** | **Recommended** |
| 20% | ~6 | 1.50x | Tax-optimized (fewer events) |

---

## Trading Settings

| Variable | Default | Notes |
|----------|---------|-------|
| `SLIPPAGE_PERCENT` | 0.5 | Max acceptable slippage per trade (0.5%) |
| `MIN_TRADE_USDC` | 1.0 | Minimum trade size — prevents dust trades |
| `REQUIRE_PROFIT` | true | Only execute trades profitable after fees |

---

## Model Selection

| Variable | Default | Options |
|----------|---------|---------|
| `ALLOCATION_MODEL` | `POWER_LAW` | `POWER_LAW` = simple power law, `HEARTBEAT` = full heartbeat model with cycle phase penalty |

**Recommended:** `HEARTBEAT` — this is the full V3 model. `POWER_LAW` is a simpler fallback.

---

## Hedera-Specific (Bot-only, not needed for model)

These settings are only needed if running the actual swap bot on Hedera. Skip for the model/UI only.

| Variable | Notes |
|----------|-------|
| `PRIVATE_KEY` | Hedera account private key (required for trading) |
| `RPC_URL` | Primary Hedera JSON-RPC endpoint |
| `MAINNET_RPC_URL` | Fallback RPC |
| `HBAR_RESERVE_MIN` | Minimum HBAR to keep for gas (default: 5 HBAR) |
| `HBAR_PER_TRADE` | Estimated HBAR per trade (default: 0.3 HBAR) |

---

## What Gets Displayed in the App

The app's **Settings tab** shows and lets users adjust:
- Rebalance threshold (with "15% recommended" label)
- Check interval
- Min trade size
- Slippage tolerance

The model's allocation signal is always displayed (no auth required). The **start/stop bot** and **force rebalance** buttons only appear for authorized wallet addresses.
