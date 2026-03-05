# 🤖 Pacman Agent Skills: Hedera Trading Primitive

**Version**: 2.0.0  
**Context**: Use this skill to execute token swaps, check balances, manage limit orders, and interact with the Hedera Network via SaucerSwap V2.

---

## 🚀 First-Run Workflow (Do This First)

```bash
# 1. Check if Pacman is configured
./launch.sh balance

# 2. If not configured, run setup
./launch.sh setup
# → Follow wizard: paste Hedera Account ID + Private Key

# 3. Verify connectivity
./launch.sh balance
# → Should show HBAR balance and any associated tokens
```

> **CRITICAL**: Ensure `PACMAN_SIMULATE=true` is set in `.env` until you explicitly receive user permission to trade live. This simulates all swaps without broadcasting transactions.

---

## 📥 Command Reference

### Core Commands (90% of use cases)

| Command | Description |
|---|---|
| `balance` | Show all token holdings with USD values |
| `swap [amt] [FROM] for [TO]` | Trade tokens (exact input) |
| `swap [FROM] for [amt] [TO]` | Trade tokens (exact output) |
| `send [amt] [TOKEN] to [ADDR]` | Transfer tokens |
| `price [token]` | Check live price |

### Limit Orders

| Command | Description |
|---|---|
| `order buy [TOKEN] at [PRICE] size [N]` | Buy when price drops to target |
| `order sell [TOKEN] at [PRICE] size [N]` | Sell when price reaches target |
| `order list` | View all open orders |
| `order cancel [ID]` | Cancel an open order |

### System

| Command | Description |
|---|---|
| `help` | Full command reference |
| `verbose on/off` | Toggle debug logging |
| `pools search [TOKEN]` | Discover new liquidity pools |
| `pools approve [ID]` | Add a pool to the routing graph |

---

## 🧠 Canonical Token Names

Use these human-friendly names — they always resolve:

| Say | Resolves To | Hedera ID |
|---|---|---|
| `bitcoin`, `btc`, `wbtc` | WBTC_HTS | 0.0.10047837 |
| `ethereum`, `eth`, `weth` | WETH_HTS | 0.0.9470869 |
| `dollar`, `usd`, `usdc` | USDC | 0.0.456858 |
| `hbar`, `hedera` | HBAR | native |

**Example**: `swap 10 HBAR for bitcoin` works identically to `swap 10 HBAR for WBTC_HTS`.

---

## 🔄 Error Recovery

### "No route found"
```
✗ No liquidity path between X and Y
```
**Fix**: The token's pool hasn't been approved yet.
```bash
./launch.sh pools search [TOKEN_NAME]
# → Find the pool contract ID
./launch.sh pools approve [CONTRACT_ID]
# → Retry the swap
```

### "Token not associated"
Pacman auto-associates tokens. If it fails:
```bash
./launch.sh associate [TOKEN_ID]
```

### "Insufficient balance"
Check your balance first. Ensure at least **5 HBAR** is reserved for gas:
```bash
./launch.sh balance
```

### "Transaction reverted"
1. Check if `PACMAN_SIMULATE=true` — simulation succeeded but live would fail
2. Try a smaller amount (slippage may be too high)
3. Set slippage: `./launch.sh slippage 3.0` (max 5%)

---

## 📤 Output Interpretation

### Swap Output
```
🚀 Executing swap: 10 HBAR → USDC
   Route: HBAR → USDC (0.30% fee)
✅ Swap Finalized
   💰 RECEIVED: 1.85 USDC (~$1.85)
   ⛽ Gas: 0.021 HBAR ($0.004)
```

### Execution Records
Every trade saves a JSON artifact to `execution_records/`:
```json
{
  "success": true,
  "tx_hash": "0xabc123...",
  "gas_used": 240000,
  "gas_cost_hbar": 0.021,
  "amount_in": 10.0,
  "amount_out": 1.85,
  "from_token": "HBAR",
  "to_token": "USDC",
  "rate": 0.185,
  "timestamp": "2026-03-05T12:00:00Z"
}
```

---

## 🚫 Prohibited Actions (Guardrails)

1. **NEVER** modify any file in `src/`, `lib/`, or `cli/`
2. **NEVER** read or print the contents of `.env`
3. **NEVER** set `PACMAN_SIMULATE=false` without explicit user approval
4. **NEVER** swap more than `max_swap_amount_usd` in a single transaction
5. **NEVER** send tokens to an address not in the whitelist
6. **NEVER** run the HBAR balance below 5 HBAR (strands other assets)
7. **ALWAYS** check `balance` before attempting a swap to verify sufficient funds

---

## 🔌 Integration Methods

| Method | How |
|---|---|
| **Subprocess** | `./launch.sh swap 10 HBAR for USDC` — parse stdout |
| **OpenClaw** | Load this file as system prompt, execute via CLI |
| **MCP Server** | *(Coming soon)* Standard protocol for Claude/Cursor |
| **Ollama / Local LLM** | Any model can call subprocess commands |

### Subprocess Example (Python)
```python
import subprocess
result = subprocess.run(
    ["./launch.sh", "swap", "10", "HBAR", "for", "USDC"],
    capture_output=True, text=True, cwd="/path/to/pacman"
)
print(result.stdout)
```

---

## 🛡 Security Context

- **Hot Account**: Only use disposable accounts with limited funds
- **Simulation Mode**: Always start with `PACMAN_SIMULATE=true`
- **Memory Risk**: Keys are handled in-process. Docker/VM recommended for production
- **Transfer Whitelist**: Live transfers are blocked unless the recipient is whitelisted
