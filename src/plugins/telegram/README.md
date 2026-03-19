# Pacman Telegram Interceptor

Standalone FastAPI webhook server that gives Pacman a native Telegram interface. Slash commands and button clicks execute instantly via PacmanController (no LLM round-trip). Text messages can be forwarded to OpenClaw for conversational AI.

## Quick Start

### 1. Create a Bot

Talk to [@BotFather](https://t.me/BotFather) on Telegram:
- `/newbot` → name it → get your bot token
- `/setcommands` → paste:
  ```
  portfolio - Show your portfolio
  swap - Start a swap
  send - Send tokens
  price - Token prices
  status - Full dashboard
  history - Recent transactions
  tokens - Supported tokens
  gas - Gas reserve status
  setup - Configure wallet key
  health - System health
  help - Command list
  ```

### 2. Configure Environment

Add to your `.env`:
```bash
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...        # From BotFather
TELEGRAM_WEBHOOK_URL=https://your-domain.com # Public HTTPS URL
TELEGRAM_WEBHOOK_SECRET=random-secret-here   # Webhook validation
TELEGRAM_ALLOWED_USERS=5219304680            # Comma-separated Telegram user IDs
TELEGRAM_PORT=8443                           # Optional, default 8443
```

### 3. Start

```bash
./launch.sh telegram-start    # Starts server + registers webhook
./launch.sh telegram-status   # Check if running
./launch.sh telegram-stop     # Stop server + remove webhook
```

Or manually:
```bash
# Set webhook
python -m src.plugins.telegram.setup_webhook set

# Start server
uvicorn src.plugins.telegram.interceptor:app --host 0.0.0.0 --port 8443
```

## Architecture

```
Telegram → POST /webhook → Inbound Router
                              │
                ┌─────────────┼─────────────┐
                ▼             ▼             ▼
           Fast Lane     AI Lane      Ghost Tunnel
           (instant)     (OpenClaw)   (secure input)
                │             │             │
                ▼             ▼             ▼
        PacmanController  (Phase 2+)    .env write
```

### Fast Lane (no LLM)
Slash commands and button callbacks execute directly via PacmanController:
- `/balance`, `/portfolio` → `get_balances()`
- `/price [TOKEN]` → price_manager
- `/status` → full dashboard
- `/history` → execution_records
- `/gas` → HBAR reserve check
- `/tokens` → token registry
- `/setup` → Ghost Tunnel Mini App
- Swap flow: parse → route → confirm keyboard → execute
- Send flow: parse → whitelist check → confirm keyboard → execute

### Ghost Tunnel
Secure key input via Telegram Mini App. Keys entered through a masked password field, POSTed directly to the backend. Never appears in chat history.

- `POST /ghost` — receives encrypted key data
- `GET /mini-app/secure-input` — serves the Mini App HTML
- HMAC-SHA256 validation of Telegram initData
- Hardcoded field whitelist: PRIVATE_KEY, ROBOT_PRIVATE_KEY, PACMAN_API_SECRET

## File Map

| File | Lines | Purpose |
|------|-------|---------|
| `interceptor.py` | ~415 | FastAPI app, webhook endpoint, async execution |
| `router.py` | ~786 | Inbound routing, swap/send flows, slash commands |
| `formatters.py` | ~552 | HTML tables, receipts, keyboards, error messages |
| `ghost.py` | ~280 | Secure input endpoint + .env writer |
| `config.py` | ~57 | Environment variable loading |
| `setup_webhook.py` | ~100 | Webhook registration CLI |
| `mini_app/secure_input.html` | ~412 | Ghost tunnel frontend |

## Safety

All governance.json limits are inherited automatically:
- Max $100 per swap
- Max $100 daily volume
- 5% max slippage
- 5 HBAR minimum gas reserve
- Transfer whitelist enforced
- EVM addresses blocked

The interceptor calls PacmanController methods — it never talks to contracts directly.

## Troubleshooting

**Bot doesn't respond:**
- Check `./launch.sh telegram-status`
- Verify webhook: `python -m src.plugins.telegram.setup_webhook info`
- Check logs: `tail -f data/telegram.log`

**"Unauthorized" errors:**
- Verify TELEGRAM_ALLOWED_USERS contains your Telegram user ID
- Find your ID: message [@userinfobot](https://t.me/userinfobot)

**Swap fails:**
- Run `./launch.sh doctor` to check system health
- Check HBAR balance (need ≥5 for gas)
- Try a smaller amount
