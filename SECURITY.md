# Security Best Practices

## Private Key Safety

- **Never share your `.env` file.** It contains your private keys in plaintext.
- **Use a dedicated hot wallet.** Do not use your main savings account. Fund the Pacman account with only what you're willing to risk.
- **Back up your keys.** Run `backup-keys --file` to export to `~/Downloads`. Store backups offline.
- **`.env` is gitignored.** If you fork this repo, verify `.env` is in `.gitignore` before pushing.

## Transfer Whitelists

The transfer whitelist is the **most critical safety feature** in Pacman.

- All outbound transfers are blocked unless the recipient is whitelisted in `data/settings.json` or is one of your own accounts in `data/accounts.json`.
- EVM addresses (`0x...`) are blocked entirely — only Hedera IDs (`0.0.xxx`) are accepted.
- Run `whitelist` to view, `whitelist add 0.0.xxx` to add, `whitelist remove 0.0.xxx` to remove.
- **Never fabricate account IDs** in examples, tests, or documentation. Agents have sent real money to placeholder accounts.

## Safety Limits

All enforced via `data/governance.json` (single source of truth):

| Limit | Value | Purpose |
|-------|-------|---------|
| Max per swap | $100 | Prevents large accidental trades |
| Max daily volume | $100 | Caps total daily exposure |
| Max slippage | 5% | Prevents execution at terrible prices |
| Min HBAR reserve | 5 HBAR | Ensures gas for future transactions |
| Min robot portfolio | $5 | Ensures trade profit exceeds costs |

Agents can adjust these **only on explicit user command**. They are never modified autonomously.

## Account Architecture

| Account | ID | Role | Key Source |
|---------|-----|------|------------|
| Main | 0.0.10289160 | User trading | `PRIVATE_KEY` in `.env` |
| Robot | 0.0.10379302 | Rebalancer daemon | `ROBOT_PRIVATE_KEY` in `.env` |
| Deprecated | 0.0.10301803 | Backup only | Never use, never delete |

- `MAIN_OPERATOR_KEY` in `.env` is the Hedera admin key (used for staking, token association).
- `PRIVATE_KEY` is the ECDSA signing key (used for EVM swaps, transfers).
- These can be different keys for the same account.

## AI Agent Safety

When driven by an AI agent (OpenClaw), these rules apply:

- Agents **never** modify `.env`, `accounts.json`, `settings.json`, or `governance.json`.
- Agents **never** create accounts, switch accounts, or approve pools without explicit user instruction.
- Agents **never** simulate — all trades are live.
- Agents **never** use V1 as a fallback for V2 routing failures.
- Agents **never** suggest MoonPay when the user has swappable tokens worth >= $1.
- If an operation fails, agents **report the exact error** — they do not guess or attempt workarounds.

## Network Security

- RPC endpoint: `https://mainnet.hashio.io/api` (Hedera JSON-RPC relay)
- Mirror Node: `https://mainnet-public.mirrornode.hedera.com` (read-only, public)
- No API keys are sent to third parties except MoonPay (fiat onramp, user-initiated only).
- The dashboard API (`http://127.0.0.1:8088`) requires `PACMAN_API_SECRET` header and binds to localhost only.

## Reporting Vulnerabilities

If you discover a security issue, please report it privately rather than opening a public issue. Contact the repository owner directly.
