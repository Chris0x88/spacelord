# Pacman Bootstrap — Safety Limits & Startup

## Safety Limits (from governance.json)

| Limit | Value | Purpose |
|-------|-------|---------|
| Max single swap | **$100** | Prevent fat-finger trades |
| Max daily volume | **$100** | Rate-limit total exposure |
| Max slippage | **5.0%** | Reject trades with excessive price impact |
| Min HBAR reserve | **5 HBAR** | Always keep gas on BOTH accounts |

These are enforced by the CLI. You cannot override them. If a user asks to exceed a limit, explain why the limit exists and suggest they talk to the developer.

## Entry Point

All commands: `./launch.sh <command>`

The app auto-detects agent mode via `isatty()` and auto-confirms. No special flags required — `--json` and `--yes` are accepted but optional.

## On Startup

1. Check daemons (`daemon-status`) — restart if down
2. Check BOTH accounts' gas (HBAR >= 5)
3. Present portfolio for BOTH main and robot accounts
4. Note any changes since last interaction
