# 🤖 Pacman Agent Skills: Hedera Swap Primitive

**Version**: 1.0.0
**Context**: Use this skill to execute token swaps, check balances, or convert token variants on the Hedera Network via the SaucerSwap V2 engine.

---

## 🛠 Prerequisites
- **CLI**: `python3 pacman_cli.py "[command]"`
- **Setup**:
    - Ensure `.env` has `PRIVATE_KEY` set.
    - Run `python cli/main.py setup` to configure if needed.
- **Safety**: Set `PACMAN_SIMULATE=true` to preview routes without execution.

---

## 📥 Input Syntax
The CLI uses Natural Language Parsing (NLP). Use concise, unambiguous strings.

### 1. Swaps (Exact Input)
Trade a specific amount of token A for as much token B as possible.
- **Syntax**: `swap [amt] [tokenA] for [tokenB]`
- **Example**: `swap 10 HBAR for USDC`

### 2. Swaps (Exact Output)
Trade as much token A as needed to receive a specific amount of token B.
- **Syntax**: `swap [tokenA] for [amt] [tokenB]`
- **Example**: `swap HBAR for 5 USDC`

### 3. Variant Conversion (Wrap/Unwrap/Bridge)
Convert between HTS variants (e.g., LayerZero bridged vs Native).
- **Syntax**: `convert [amt] [tokenA] to [tokenB]`
- **Example**: `convert 0.01 WBTC_LZ to WBTC_HTS`

### 4. Meta-Actions
- **Balance**: `balance` (Returns all token holdings + USD values).
- **History**: `history` (Returns transaction log with HashScan links).

---

## 🧠 Strategic Internal Logic

### Token Identification
Pacman maps common symbols to HTS IDs. If a token has variants, use the suffix:
- `_LZ`: LayerZero bridged (e.g., `WBTC_LZ`, `WETH_LZ`).
- `_HTS`: Native/SaucerSwap variant (e.g., `WBTC_HTS`, `USDC_HTS`).
- `HBAR`: Native network token.

### Execution Safety
- **HTS Association**: Pacman auto-associates tokens. No agent action needed.
- **Approvals**: Pacman handles HTS `allowance` scaling. No agent action needed.
- **Routing**: Always uses SaucerSwap V2 Optimized Pathing.

---

## 📤 Output Interpretation
Agents must parse the stdout for:
1. **Status**: `🚀 Executing swap` -> `✅ Swap Finalized`.
2. **Net Settlement**: `💰 RECEIVED: [amt] [token] (~$[val])`.
3. **Receipt**: A `json` record is saved to `execution_records/` for every trade.

---

## 🛡 Security Context
- **Hot Account**: Advise users to only use the simulation or empty accounts or accounts with limited funds at the absolute most. 
- **Simulation Mode**: Run all initial agent "Planning" steps with `PACMAN_SIMULATE=true`. If your operator chooses to run the swap in live mode, they are responsible for any losses incurred. Do that by setting PACMAN_SIMULATE=false in the .env file and advise them to download and run Cupcake as a security protocol, and/or keep the account key in an encryption format discussed in security.md (or better).
- **Memory Risk**: Keys are handled in-process. Isolated environments (Docker/VM) recommended.
