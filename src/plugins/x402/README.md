# X402 Payment-Gated Signal Access

## What is X402?

**HTTP 402 Payment Required** is an HTTP status code defined in RFC 3875 (and formally standardized in RFC 9110) intended for agent-to-agent commerce. Instead of redirecting to a login page or returning 401 (Unauthorized), a service returns 402 with payment instructions embedded in the response.

This enables a novel flow:
1. **Access without authentication** — no login required
2. **Micropayments as the access control** — pay per signal, not per subscription
3. **Peer-to-peer commerce** — agents can pay agents directly via blockchain

X402 is designed for APIs that want to monetize small, frequent requests without the overhead of account management.

## How the Pacman X402 Plugin Works

This plugin implements a minimal X402 server for the Pacman Hedera wallet trading signals. It exposes two payment-gated endpoints:

### `/signal` — Get Latest Trading Signal

**Without Payment:**
```bash
curl http://localhost:8000/signal
```

Returns HTTP 402:
```json
{
  "status": "payment_required",
  "payment_destination": {
    "hedera_account": "0.0.10289160",
    "amount_hbar": 0.14,
    "memo": "pacman-signal-access"
  },
  "details": "Send 0.14 HBAR to 0.0.10289160 with memo 'pacman-signal-access'. Then retry with X-Payment-Tx header containing the transaction hash."
}
```

**With Payment Proof:**
```bash
curl -H "X-Payment-Tx: 0.0.123-456-78901" \
  http://localhost:8000/signal
```

Returns HTTP 200 with signal data:
```json
{
  "status": "ok",
  "timestamp": "2026-03-21T12:34:56.789Z",
  "signal": {
    "date": "2026-03-20",
    "price": 69924.55,
    "allocation_pct": 60.1,
    "stance": "accumulate",
    "tagline": "Cycle 5 | 48% complete | Late Cycle Peak Zone | Price at 15% of range (deep value) | Favorable accumulation: 60% BTC recommended"
  },
  "metadata": {
    "trades_executed": 39,
    "last_rebalance": "2026-03-19T20:50:18.175781",
    "portfolio": { "wbtc_balance": 0.00023978, "usdc_balance": 11.501914, ... }
  }
}
```

### `/signal/history` — Get Signal History

Same 402 flow, but returns recent HCS messages and activity log:
```bash
curl -H "X-Payment-Tx: 0.0.123-456-78901" \
  http://localhost:8000/signal/history?limit=10
```

## Getting Started

### Prerequisites

- Python 3.8+
- FastAPI and Uvicorn

```bash
pip install fastapi uvicorn
```

### Running the Server

From the Pacman root directory:

```bash
python -m src.plugins.x402.server
```

This starts the server on `http://127.0.0.1:8000`.

### Full Example: Agent Payment Flow

1. **Agent discovers endpoint and sees 402:**
   ```python
   import requests
   resp = requests.get("http://localhost:8000/signal")
   # resp.status_code == 402
   # resp.json()['payment_destination']['hedera_account'] == "0.0.10289160"
   # resp.json()['payment_destination']['amount_hbar'] == 0.14
   ```

2. **Agent creates and sends payment transaction:**
   ```python
   from hedera import TransferTransaction, AccountId, Hbar

   tx = TransferTransaction() \
       .addHbarTransfer("0.0.xxx", Hbar(-0.14)) \
       .addHbarTransfer("0.0.10289160", Hbar(0.14)) \
       .setTransactionMemo("pacman-signal-access") \
       .freezeWith(client) \
       .sign(agent_key) \
       .execute(client)

   receipt = tx.getReceipt(client)
   tx_hash = receipt.transactionId  # "0.0.123-456-78901"
   ```

3. **Agent retries with payment proof:**
   ```python
   resp = requests.get(
       "http://localhost:8000/signal",
       headers={"X-Payment-Tx": tx_hash}
   )
   # resp.status_code == 200
   signal = resp.json()['signal']
   ```

## Design Notes

- **Rate:** 0.14 HBAR ≈ $0.03 at ~$0.19/HBAR, roughly $10/year for daily access.
- **Memo requirement:** The memo field acts as a lightweight service identifier. Agents can index payments by memo.
- **Mirror Node verification:** The `verify_payment_on_mirrornode()` function is stubbed. In production, query the Hedera Mirror Node to validate:
  - Transaction result is SUCCESS
  - Recipient is the correct account
  - Amount is at least the required rate
  - Memo matches expected value
- **No state:** The server is stateless. Each request independently verifies the payment transaction. This avoids session management complexity.
- **Proof of concept:** This implementation prioritizes simplicity and clarity over production features (rate limiting, caching, TLS, etc.).

## API Docs

Once running, visit `http://localhost:8000/docs` for interactive API documentation (Swagger UI).

## Security Considerations

- **Replay attacks:** A valid `X-Payment-Tx` header can be reused. In production, track consumed transactions or use nonces.
- **Mirror Node lag:** The Hedera Mirror Node may lag behind network consensus by a few seconds. Consider allowing a brief verification grace period.
- **Micropayment abuse:** Attackers could spam requests with fake transaction hashes. Implement request rate limiting per source IP and/or proof-of-work challenges.

## Future Work

- **Persistent payment cache:** Track consumed transaction IDs to prevent replay.
- **Subscription tiers:** Support monthly/yearly subscriptions via HCS consent channels.
- **Webhooks:** Notify subscribers of new signals via HCS messages.
- **Multi-token support:** Accept USDC, WBTC, or other tokens in addition to HBAR.
- **DeFi integration:** Integrate with SaucerSwap or other Hedera DEXes to auto-swap payment currencies.

## References

- RFC 3875: The 402 Payment Required Status Code
- RFC 9110: HTTP Semantics (updated definition)
- Hedera Mirror Node API: https://docs.hedera.com/hedera/sdks-and-apis/rest-api
- Pacman governance: `/data/governance.json`
