# Bootstrap Context

## Channel Formatting

Adapt output to the user's messaging platform. Default to Telegram.

| Channel | Format | Limit | Notes |
|---------|--------|-------|-------|
| **Telegram** (default) | HTML subset via markdown. **bold**, `code`, tables OK | ~4000 chars | Link previews on |
| **Discord** | Full markdown, code blocks, embeds | ~2000 chars | Split long messages |
| **WhatsApp** | *bold*, _italic_, `code` only. No tables | ~4000 chars | Use bullet lists |
| **Slack** | *bold*, `code`, mrkdwn blocks | ~4000 chars | Bullet lists over tables |
| **Signal / iMessage** | Plain text + emoji only | ~4000 chars | No formatting |
| **CLI / Agent** | Full markdown, tables, code blocks | No limit | Richest output |

When in doubt, prefer bullet lists over tables — they work everywhere.

## Safety Limits (from governance.json)

- Max per swap: **$100**
- Max daily volume: **$100**
- Max slippage: **5.0%**
- Min HBAR reserve: **5 HBAR**

## Entry Point

All commands: `./launch.sh <command>`

No special flags needed. The app auto-detects agent mode via `isatty()` and auto-confirms. Agents and humans use the exact same command syntax.
