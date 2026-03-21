# STOP — This directory is NOT for the OpenClaw agent

## What this is
A **standalone Telegram wallet bot** that runs as a separate process.
It uses `TELEGRAM_WALLET_BOT_TOKEN` and operates in its own Telegram chat.

## What the OpenClaw agent should read instead
- `SKILL.md` — Agent behavior and commands
- `CLAUDE.md` — Project governance
- `cli/commands/telegram.py` — Agent's fast-lane bridge (subprocess)
- `src/plugins/telegram/router.py` — Shared routing logic
- `src/plugins/telegram/formatters.py` — Shared HTML formatters

## Files in this directory (all wallet-bot-only)
| File | Purpose |
|------|---------|
| `poller.py` | Long-polling Telegram runner (./launch.sh telegram-start) |
| `interceptor.py` | Webhook server alternative to poller |
| `ghost.py` | Secure key input via Telegram Mini App |
| `config.py` | Wallet bot config (TELEGRAM_WALLET_BOT_TOKEN) |
| `setup_webhook.py` | Webhook registration CLI |
| `mini_app/` | Mini App HTML frontend for ghost tunnel |
| `workspace/` | Wallet bot workspace docs (AGENTS.md, SOUL.md, etc.) |

## The two Telegram bots are COMPLETELY SEPARATE

| | OpenClaw Agent Bot | Wallet Bot (this dir) |
|---|---|---|
| Token | `TELEGRAM_BOT_TOKEN` | `TELEGRAM_WALLET_BOT_TOKEN` |
| Brain | SKILL.md + LLM | Hard-coded router logic |
| Entry | OpenClaw gateway | ./launch.sh telegram-start |
| Chat | Separate Telegram chat | Separate Telegram chat |
