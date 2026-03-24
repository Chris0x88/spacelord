# Contributing to Space Lord

Space Lord is an open-source self-custody AI wallet for Hedera. Contributions are welcome — whether it's new plugins, bug fixes, documentation, or trading strategies.

## Quick Setup

```bash
git clone https://github.com/Chris0x88/spacelord.git
cd spacelord
./launch.sh init        # First-run wizard (creates .env, sets up keys)
./launch.sh balance     # Verify everything works
```

Prerequisites: Python 3.10+, macOS or Linux. `uv` is installed automatically.

## Project Structure

```
src/              Core trading engine (controller, router, executor)
cli/              CLI dispatcher and command handlers
lib/              External integrations (SaucerSwap, Telegram, prices)
data/             Configuration, pool registries, templates
openclaw/         AI agent workspace and SKILL files
src/plugins/      Plugin system (daemons, bots, services)
src/core/         Plugin base class, API server, service framework
tests/            Test suites
scripts/          Utility scripts
```

## Adding a Plugin

Plugins extend Space Lord with new background services. Every plugin inherits from `BasePlugin`:

```python
# src/plugins/my_plugin/plugin.py
from src.core.base_plugin import BasePlugin

class MyPlugin(BasePlugin):
    def __init__(self, app):
        super().__init__(app, name="my-plugin")

    def run_loop(self):
        # Your logic here — called repeatedly while running
        # BasePlugin handles threading, error recovery, and health reporting
        pass
```

Plugins are auto-discovered by `src/core/plugin_manager.py` from `src/plugins/`.

**Rules:**
- Plugins must NOT import each other. Communicate through the Controller or event bus.
- Never hard-code account IDs. Use `self.app.config` for account discovery.
- Keep secrets in `.env`, operational config in `data/governance.json`.

## Adding a CLI Command

1. Create a handler in `cli/commands/your_feature.py`
2. Register it in `cli/main.py` in the `COMMANDS` dict
3. The handler receives the `SpaceLordController` instance

## Safety Rules

These are non-negotiable for a project handling real money:

- **`data/governance.json`** is the single source of truth for safety limits. Never scatter limits across config files.
- **Never simulate.** `simulate_mode` defaults to `False`. Tests override explicitly.
- **Transfer whitelists** are the most important safety feature. All transfers require whitelisted destinations.
- **Never fabricate account IDs** in examples or tests. Agents have sent real money to fake accounts.
- **V2 is the primary protocol.** V1 is legacy, explicit command only, never a fallback.
- Always use `_safe_input()` instead of bare `input()` — bare input crashes in non-interactive mode.

## Running Tests

```bash
./launch.sh verify      # Run full test suite (simulation mode)
```

Tests run in simulation mode and never execute real transactions.

## Security

See [SECURITY.md](SECURITY.md) for vulnerability reporting and security policies.

## License

MIT — see [LICENSE](LICENSE) for details.
