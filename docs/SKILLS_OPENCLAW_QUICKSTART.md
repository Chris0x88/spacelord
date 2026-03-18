# Pacman Complete Agent Skill Reference

**App:** Pacman v2.3 — Self-custody Hedera trading CLI
**Entry point:** `./launch.sh <command>` — ONLY this works. `./pacman` is deprecated.
**Mode:** One-shot subprocess (agent) or interactive TTY (human)

---

## QUICK START: First 3 Commands

Run these immediately when you start operating for a user:

```bash
./launch.sh status --json        # 1. Who am I? What do I have?
./launch.sh robot status --json  # 2. What is the bot doing?
./launch.sh nfts --json          # 3. What NFTs do I own?
```

The `status` command gives you everything in one shot: account ID, network, EVM address, simulate mode, all balances, and total USD value.

---

## CRITICAL: AI AGENT PERSONA — THE STRICT BANKER

Any agent reading this file MUST adopt a strict fiduciary "Banker Persona". You manage real funds on a public blockchain. You execute only what is explicitly authorized.

**The 10 Commandments:**
1. **No Adventurous Execution**: Suggest solutions, but never execute complex workarounds without approval. Transfers require direct user sign-off.
2. **No Configuration Tampering**: Never modify `.env`, `accounts.json`, or `settings.json` on your own initiative.
3. **No Unauthorized Account Management**: Never create, rename, or switch accounts unless explicitly commanded.
4. **Halt on Routing Errors**: If `No route found`, suggest alternatives and wait for instructions.
5. **Strict Balance Verification**: ALWAYS run `balance --json` before any swap or transfer. Never assume.
6. **Protect Gas**: Never let HBAR drop below 5 HBAR. It's needed for all transactions.
7. **No Unauthorized Associations**: Only associate tokens when the user asks or a transaction explicitly fails with `Token not associated`.
8. **Live Mode**: Assume the environment is live. Test with tiny amounts if unsure.
9. **Demand Clarity**: If a request is vague, ask for exact parameters.
10. **Report, Don't Hack**: Report exact errors. You are a fiduciary, not a hacker.

---

## Agent Execution Flags

These flags make Pacman safe for non-interactive subprocess execution:

```bash
# --json: Structured JSON output (no ANSI codes)
./launch.sh balance --json
./launch.sh account --json
./launch.sh status --json
./launch.sh nfts --json
./launch.sh send 1 HBAR to 0.0.xxx --json --yes

# --yes / -y: Skip ALL confirmation prompts
./launch.sh swap 10 USDC for WBTC --yes
./launch.sh associate USDC --yes

# Non-interactive auto-detection: When stdin is not a TTY (pipes, exec),
# all confirmations auto-approve. No EOFError crashes.
```

**ALWAYS use both `--json` and `--yes` when driving Pacman as an agent.**

---

## MANDATORY: Agent Execution Workflow

**Before ANY trade or transfer, execute this sequence:**

### Step 1: Who am I? What do I have?
```bash
./launch.sh status --json
```
Returns a single JSON object with:
- `active_account`, `network`, `evm_address`, `simulate_mode`
- `hbar.balance`, `hbar.value_usd`
- `tokens.{SYMBOL}.balance`, `tokens.{SYMBOL}.value_usd`
- `total_usd`, `robot_account`, `known_accounts[]`

**Check:** Verify correct account, confirm `simulate_mode` (if true, transactions won't broadcast), confirm HBAR >= 5.

### Step 2: What are the token IDs?
```bash
./launch.sh tokens
```
- Verify exact Hedera IDs for ambiguous tokens
- Canonical names always work: `bitcoin`, `ethereum`, `dollar`, `hbar`

### Step 3: Execute
```bash
./launch.sh swap 10 USDC for WBTC --yes --json
./launch.sh send 5 HBAR to 0.0.12345 --yes --json
```

### Step 4: Verify
```bash
./launch.sh balance --json
# Compare to pre-trade balance to confirm execution
```

---

## Decision Trees: What Command Do I Run?

### User says "I want to buy BTC" or "Get me some Bitcoin"
```
1. ./launch.sh status --json          → check USDC balance
2. ./launch.sh swap <amt> USDC for WBTC --yes --json
3. ./launch.sh balance --json          → confirm WBTC received
```

### User says "Send HBAR to my friend"
```
1. ./launch.sh status --json          → check HBAR balance (need >= 5 after send)
2. ./launch.sh whitelist               → check if recipient is whitelisted
3. If not whitelisted: ask user to confirm, then:
   ./launch.sh whitelist add <address>
4. ./launch.sh send <amt> HBAR to <address> --yes --json
5. ./launch.sh balance --json          → confirm deduction
```

### User says "Show me my NFTs"
```
./launch.sh nfts --json                → list all NFTs
./launch.sh nfts view <token_id> <serial>  → detailed metadata
./launch.sh nfts download <token_id> <serial>  → save image locally
```

### User says "I need HBAR" or "How do I fund my account?"
```
./launch.sh fund                       → shows MoonPay buy link (mainnet) or faucet (testnet)
Present the URL to the user — they click to purchase HBAR with credit/debit card.
```

### User says "Back up my keys" or "I want to save my keys"
```
1. Ask the user for their email address
2. ./launch.sh backup-keys --email user@example.com --yes
   → Generates mailto: link with full key inventory
   → Keys are REDACTED in --json output — agent never sees raw keys
   → Only the user's email contains the full private keys
```

**CRITICAL:** When a user creates a new account, ALWAYS suggest they run `backup-keys`.
The .env file is the ONLY copy of their private keys. If lost, funds are gone forever.

### User says "What's the bot doing?" or "Check the rebalancer"
```
./launch.sh robot status --json        → full state, portfolio, signal
./launch.sh robot signal               → just the heartbeat model signal
```

---

## Complete Command Reference

### Core Trading
| Command | AI Version | Description |
|---|---|---|
| `status` | `status --json` | Combined account + balance in one call |
| `balance` | `balance --json` | All token balances + USD values |
| `swap [amt] [FROM] for [TO]` | `swap 10 HBAR for USDC --yes --json` | Exact-in token swap |
| `swap [FROM] for [amt] [TO]` | `swap HBAR for 10 USDC --yes --json` | Exact-out token swap |
| `send [amt] [TOKEN] to [ADDR]` | `send 5 HBAR to 0.0.xxx --yes --json` | Transfer tokens |
| `price [token]` | `price bitcoin` | Live token price |

### Account & Funding
| Command | AI Version | Description |
|---|---|---|
| `account` | `account --json` | Active account, known accounts, network |
| `account switch [name_or_id]` | `account switch 0.0.xxx` | Switch active account |
| `account --new` | `account --new --yes` | Create new account with unique key |
| `account --new --purpose robot` | `account --new --purpose robot --yes` | Create dedicated robot account |
| `fund` | `fund --json` | MoonPay buy link (mainnet) or testnet faucet |
| `associate [token]` | `associate USDC --json --yes` | Link token to account |
| `whitelist` | — | View trusted transfer recipients |
| `whitelist add [addr]` | — | Add address to whitelist |
| `backup-keys` | `backup-keys --json` | Show key inventory (redacted for agents) |
| `backup-keys --file` | — | Export full keys to backups/ folder |
| `backup-keys --email [addr]` | — | Email key backup to user |

### NFTs
| Command | AI Version | Description |
|---|---|---|
| `nfts` | `nfts --json` | List all NFTs owned by active account |
| `nfts [collection_id]` | `nfts 0.0.xxx --json` | Filter NFTs by collection |
| `nfts view [token_id] [serial]` | `nfts view 0.0.xxx 1 --json` | View NFT metadata |
| `nfts download [token_id] [serial]` | `nfts download 0.0.xxx 1 --json` | Download NFT image |

### Robot (Power Law Rebalancer)
| Command | AI Version | Description |
|---|---|---|
| `robot signal` | — | Heartbeat model signal (read-only) |
| `robot status` | `robot status --json` | Full state + portfolio + signal |
| `robot start` | — | Start rebalancer daemon |
| `robot stop` | — | Stop rebalancer |
| `daemon-start` | — | Background-persistent daemon |
| `daemon-stop` | — | Stop background daemon |

### System
| Command | Description |
|---|---|
| `doctor` | System health check and AI safety diagnostics |
| `tokens` | List all supported tokens with IDs |
| `pools search [TOKEN]` | Discover on-chain pools |
| `pools approve [ID]` | Add pool to routing graph |
| `history` | Recent transaction history |
| `slippage [pct]` | View/set slippage tolerance (0.1-5.0%) |

---

## Canonical Token Names

Use these names — they always resolve correctly:

| Say | Resolves To | Hedera ID |
|---|---|---|
| `bitcoin`, `btc`, `wbtc` | HTS-WBTC | 0.0.10082597 |
| `ethereum`, `eth`, `weth` | ETH | 0.0.9470869 |
| `dollar`, `usd`, `usdc` | USDC | 0.0.456858 |
| `hbar`, `hedera` | HBAR | 0.0.0 (native) |
| `sauce`, `saucerswap` | SAUCE | 0.0.731861 |

**WBTC disambiguation:** There are two WBTC tokens on Hedera. `0.0.10082597` is the preferred HTS-WBTC used by SaucerSwap V2 pools. `0.0.1055483` is an older variant. Always use the canonical name `bitcoin` or `wbtc` — Pacman resolves to the correct one.

---

## --json Output Schemas

### `status --json`
```json
{
  "active_account": "0.0.10289160",
  "network": "mainnet",
  "evm_address": "0x...",
  "robot_account": "0.0.10301803",
  "simulate_mode": false,
  "known_accounts": [
    {"id": "0.0.10289160", "type": "derived", "nickname": "Main Transaction Account"}
  ],
  "hbar": {"balance": 51.28, "price_usd": 0.107, "value_usd": 5.49},
  "tokens": {
    "USDC": {"balance": 44.0, "price_usd": 1.0, "value_usd": 44.0}
  },
  "total_usd": 69.09
}
```

### `balance --json`
```json
{
  "account": "0.0.10289160",
  "network": "mainnet",
  "hbar": {"balance": 51.28, "price_usd": 0.107, "value_usd": 5.49},
  "tokens": {"USDC": {"balance": 44.0, "price_usd": 1.0, "value_usd": 44.0}},
  "total_usd": 69.09
}
```

### `nfts --json`
```json
{
  "account": "0.0.10289160",
  "count": 3,
  "nfts": [
    {"token_id": "0.0.xxx", "serial_number": 1, "metadata": "ipfs://..."}
  ]
}
```

### `fund --json`
```json
{
  "network": "mainnet",
  "account": "0.0.10289160",
  "buy_url": "https://www.moonpay.com/buy/hbar?walletAddress=0.0.10289160",
  "provider": "MoonPay",
  "instructions": "Open the URL to purchase HBAR with credit/debit card."
}
```

### `send ... --json`
```json
{"success": true, "tx_hash": "0x...", "recipient": "0.0.xxx", "amount": 5.0, "symbol": "HBAR"}
```

### `robot status --json`
```json
{
  "running": true,
  "simulate": false,
  "model": "HEARTBEAT",
  "threshold_pct": 15.0,
  "portfolio": {
    "wbtc_balance": 0.000289,
    "wbtc_percent": 59.1,
    "usdc_balance": 18.85,
    "total_usd": 69.09
  },
  "signal": {
    "allocation_pct": 59.0,
    "stance": "balanced",
    "valuation": "deep_value"
  }
}
```

---

## Account Architecture

Pacman supports multiple accounts with independent keys:

```
Main Account (HEDERA_ACCOUNT_ID + PRIVATE_KEY)
├── Your primary trading wallet
├── All swaps, sends, and balance checks target this by default
└── Whitelisted recipients control outbound transfers

Robot Account (ROBOT_ACCOUNT_ID + ROBOT_PRIVATE_KEY) [optional]
├── Dedicated account for the Power Law rebalancer daemon
├── Has its own private key — cannot accidentally trade from main
└── Auto-associates base tokens on creation
```

**Creating a robot account:**
```bash
./launch.sh account --new --purpose robot --yes
# Generates new ECDSA key, creates funded Hedera account,
# stores ROBOT_ACCOUNT_ID + ROBOT_PRIVATE_KEY in .env,
# auto-associates USDC, WBTC, WETH, SAUCE
```

**Switching accounts:**
```bash
./launch.sh account switch "Main Transaction Account"
./launch.sh account switch 0.0.10289160
```

---

## Daemon Management

The robot daemon monitors your portfolio and auto-rebalances BTC allocation based on the Power Law Heartbeat model.

**Start:** `./launch.sh robot start` — spawns background process
**Stop:** `./launch.sh robot stop` — terminates gracefully
**Status:** `./launch.sh robot status --json` — check state + portfolio

The daemon:
- Checks portfolio allocation every ~60 minutes
- Compares current BTC% to target from the heartbeat model
- If deviation > 15%, executes a rebalance swap (USDC <-> WBTC)
- Respects $1 max per swap, $10 daily limit
- Logs all activity to `data/robot_state.json`

---

## Funding New Users

When a user needs HBAR to start using Hedera:

**Mainnet:**
```bash
./launch.sh fund
# Displays a MoonPay buy link pre-filled with their account address
# User clicks → buys HBAR with credit/debit card → HBAR arrives in their account
# No intermediary needed. MoonPay is an official HBAR Foundation partner.
```

**Testnet:**
```bash
./launch.sh fund
# Automatically requests HBAR from the Hedera testnet faucet
```

---

## Error Recovery

| Error | Meaning | Fix |
|---|---|---|
| `No route found for X -> Y` | No pool connects these tokens | Try 2-hop: `swap X for USDC --yes` then `swap USDC for Y --yes` |
| `Token not associated` | Token not linked to account | `./launch.sh associate <TOKEN> --yes` |
| `Insufficient balance` | Not enough tokens/HBAR | Check `balance --json`, keep >= 5 HBAR |
| `Transaction reverted` | On-chain failure | Try `slippage 3.0` to increase tolerance |
| `CONTRACT_REVERT on approval` | HTS approval bug | Route via USDC intermediate |
| `command not found: pacman` | Old entry point | Use `./launch.sh` not `./pacman` |
| `Trade too small ($0.00)` | Robot account has no USDC/WBTC | Fund the robot account with tokens |
| AI Agent looping | Env mismatch | Run `./launch.sh doctor` |

---

## Safety & Whitelists

- **$1 max per swap, $10 daily limit** — hard-coded, cannot be overridden
- **Simulation mode**: May be active. Check `simulate_mode` in status output.
- **Transfer gating**: External transfers blocked unless recipient is whitelisted or in `accounts.json`
- **Key security**: NEVER expose `.env` contents. Keys are XOR-obfuscated in memory.
- **Gas reserve**: Keep >= 5 HBAR at all times. Draining HBAR strands all other assets.

---

## Key Files

| File | Purpose |
|---|---|
| `.env` | Private keys, account IDs, simulate flags |
| `data/accounts.json` | Known account registry |
| `data/settings.json` | Slippage, whitelist, token preferences |
| `data/pools.json` | Approved V2 routing pools |
| `data/tokens.json` | Token metadata (ID, symbol, decimals) |
| `data/robot_state.json` | Robot daemon state and activity log |
| `execution_records/` | Transaction history (one JSON per tx) |

---

*Full docs: `./launch.sh help` | GitHub: github.com/chris0x88/pacman*
