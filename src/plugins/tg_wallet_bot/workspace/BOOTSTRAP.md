# Bootstrap Context

## Slash Commands Available

`/start` `/portfolio` `/swap` `/send` `/price` `/robot` `/orders` `/gas` `/health` `/nfts` `/accounts` `/help` `/guide` `/setup`

## Channel Formatting

Adapt output to the user's messaging platform. Default to Telegram.

| Channel | Format | Limit | Notes |
|---------|--------|-------|-------|
| **Telegram** (default) | HTML via markdown. **bold**, `code`, tables OK | ~4000 chars | Link previews on |
| **Discord** | Full markdown, code blocks, embeds | ~2000 chars | Split long messages |
| **WhatsApp** | *bold*, _italic_, `code` only. No tables | ~4000 chars | Use bullet lists |
| **CLI / Agent** | Full markdown, tables, code blocks | No limit | Richest output |

When in doubt, prefer bullet lists over tables — they work everywhere.

## Safety Limits (from governance.json)

- Max per swap: **$100**
- Max daily volume: **$100**
- Max slippage: **5.0%**
- Min HBAR reserve: **5 HBAR** (on BOTH accounts)

## Entry Point

All commands: `./launch.sh <command>`

The app auto-detects agent mode via `isatty()` and auto-confirms. Use `--json` for structured output and `--yes` to skip prompts.

## On Startup

1. Check daemons (`daemon-status`) — restart if down
2. Check BOTH accounts' gas (HBAR >= 5)
3. Present portfolio for BOTH main and robot accounts
4. Note any changes since last interaction
