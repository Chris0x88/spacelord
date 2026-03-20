# X402 Plugin Manifest

## Overview
Minimal HTTP 402 (Payment Required) implementation for agent-to-agent commerce. Exposes Pacman trading signals as a payment-gated resource.

## Files

### 1. `__init__.py` (empty)
- Package marker for the x402 plugin module

### 2. `server.py` (251 lines)
Main FastAPI application implementing X402 endpoints:

**Endpoints:**
- `GET /` — Root with service info
- `GET /health` — Health check (no payment required)
- `GET /signal` — Latest trading signal (payment-gated)
- `GET /signal/history?limit=10` — Recent activity log (payment-gated)

**Key Functions:**
- `load_robot_state()` — Loads signal from `data/robot_state.json`
- `payment_required_response()` — HTTP 402 response with payment instructions
- `verify_payment_on_mirrornode(tx_hash)` — Validates payment (stubbed, calls Mirror Node in production)
- `get_signal(x_payment_tx)` — Returns signal after payment verification
- `get_signal_history(limit, x_payment_tx)` — Returns recent history after verification
- `run_server(host, port, reload)` — Starts Uvicorn server

**Configuration (from environment):**
- `HEDERA_ACCOUNT_ID` — Payment destination (default: 0.0.10289160)
- `HEDERA_MIRRORNODE_URL` — Mirror Node endpoint
- `X402_RATE_HBAR` — Payment amount (0.14 HBAR ≈ $0.03)
- `X402_MEMO` — Transaction memo for routing ("pacman-signal-access")

### 3. `README.md` (170 lines)
Complete documentation covering:
- X402 standard explanation (RFC 3875, RFC 9110)
- How the plugin works
- API examples with curl
- Full agent payment flow example
- Running instructions
- Design notes and future work

### 4. `example_client.py` (140 lines)
Demonstration of X402 client flow:
- Shows HTTP 402 → Payment → HTTP 200 sequence
- `X402Client` class with `request_signal()` and `simulate_payment()`
- Mock transaction ID generation
- Can be run standalone: `python3 src/plugins/x402/example_client.py`

## Usage

### Start the server:
```bash
python -m src.plugins.x402.server
# or
python3 src/plugins/x402/server.py
```

### Test with curl (no payment):
```bash
curl -i http://127.0.0.1:8000/signal
# Returns HTTP 402 with payment instructions
```

### Test with mock payment:
```bash
curl -i -H "X-Payment-Tx: 0.0.456-789-1234567890" \
  http://127.0.0.1:8000/signal
# Returns HTTP 200 with signal data
```

### Interactive API docs:
```
http://127.0.0.1:8000/docs
```

## Payment Flow

1. Client requests `/signal` without `X-Payment-Tx` header
2. Server returns HTTP 402 with:
   - `hedera_account`: 0.0.10289160
   - `amount_hbar`: 0.14
   - `memo`: pacman-signal-access
3. Client creates and signs payment transaction (TransferTransaction)
4. Client re-requests with `X-Payment-Tx: <tx_hash>` header
5. Server verifies payment via Mirror Node
6. Server returns HTTP 200 with signal data

## Production Readiness

**This is a proof-of-concept.** Currently stubbed/missing:
- ✗ Mirror Node payment verification (calls Mirror Node API in production)
- ✗ Replay attack prevention (need tx ID tracking)
- ✗ Rate limiting (need per-IP request throttling)
- ✗ TLS/HTTPS (use reverse proxy in production)
- ✗ Caching (add Redis for payment cache)
- ✗ Subscription tiers (hard-coded 0.14 HBAR per request)

**Suitable for:**
- Testing X402 pattern with agents
- Demo/PoC for payment-gated APIs
- Educational reference
- Local development

## Architecture Notes

- **Stateless:** No database, no session state. Each request verifies payment independently.
- **Mirror Node dependent:** For production, integrate Hedera Mirror Node API for transaction verification.
- **Memo-based routing:** Uses transaction memo to identify payment intent.
- **Minimal dependencies:** Only FastAPI and Uvicorn (both production-grade frameworks).

## Integration with Pacman

- Reads signals from `data/robot_state.json` (loaded at request time, always current)
- Uses `HEDERA_ACCOUNT_ID` from `.env` as payment destination
- Does not modify any Pacman state or configuration
- Completely isolated from core trading logic

## See Also

- `/data/governance.json` — Safety limits and account configuration
- `/data/robot_state.json` — Current robot signal and portfolio state
- `/src/plugins/hcs/` — Hedera Consensus Service integration (future HCS topic streaming)
