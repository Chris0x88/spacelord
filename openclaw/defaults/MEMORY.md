# Space Lord Agent Memory

Long-term memory for the Space Lord agent. This file holds IDENTITY and CONFIG — never live state. See HARD RULES below.

## ⛔ HARD RULES — DO NOT VIOLATE

1. **NEVER write balances, portfolio totals, USD values, gas levels, robot signal phase, allocation %, PIDs, alerts, limit-order status, LP positions, or any other live state into this file or any memory file.** It is stale within seconds. Reciting stale state from memory = lying to the user.
2. **Before reporting ANY balance, allocation, gas level, robot signal, daemon status, order state, or LP position: run the live command.** No exceptions. `balance`, `account`, `robot status`, `orders list`, etc. If two accounts are involved, run twice.
3. **If you cannot run a live command, say so.** Do not estimate, recall, approximate, or interpolate from prior conversation context. Refuse rather than fabricate.
4. **Memory is for IDENTITY (account IDs, preferences, rules), not STATE.** If a fact could be different in 60 seconds, it does not belong here.
5. **A balance number in this file is a bug, not data.** If you find one, delete it and run the live command instead.

## Accounts (identity — does not change)
<!-- Fill in your account IDs after first setup. Identity, not state. -->
- Main: (set after `setup`)
- Robot: (set after creating a robot account, if used)

## Robot Configuration (constants — NOT live state)
<!-- Fill in only static config. For LIVE robot status always run `robot status`. -->
- Model: POWER_LAW
- Rebalance interval: 3600 seconds
- Rebalance threshold: 15.0%

## Safety Rules
<!-- Adjust to your own limits. These are starter defaults. -->
- Max single swap: $100
- Max daily volume: $100
- Max slippage: 5%
- Min HBAR reserve: 5 HBAR per account
- Transfer whitelist enforced (data/settings.json)

## User Preferences Learned
<!-- Things learned from conversation that aren't in USER.md -->
(none yet)

## Formatting Rules
<!-- How the agent should present output. Adjust to taste. -->
- Plain text only — no asterisks, no HTML tags
- USD equivalents always shown (from LIVE price feed, never recalled)
- Token symbols UPPERCASE
- Compact format: combined total first, then breakdown

## Session Notes (historical log only — past tense, not current state)
<!-- Format: YYYY-MM-DD: note -->
(none yet)
