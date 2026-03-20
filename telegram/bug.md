# Pacman Agent Improvement: Token symbol case-insensitivity

## Issue
The agent (Pacman) currently passes raw user token symbols directly to the CLI. When the user requests `/price wbtc`, the CLI fails because it requires exact symbol matching (`WBTC_HTS`, `BTC`, or `BITCOIN`). The agent should normalize and map common aliases before invoking the CLI.

## Example
User: `/price wbtc` → Agent should internally use `BTC` or `WBTC_HTS`

## Expected Agent Behavior
Before executing any token-based CLI command, the agent should:
1. Normalize the token symbol to uppercase
2. Check known aliases in `tokens.json` (e.g., `wbtc` → `BTC` or `WBTC_HTS`)
3. If ambiguous, pick the most likely match (preferred tokens first)
4. Never fail with "Unknown token" for common variations

## Implementaion Hint
The agent has access to `data/tokens.json`. Load it and perform alias resolution in the command handler before calling `./launch.sh`.

## CLI Behavior
The CLI itself is correct — it expects exact symbols. The intelligence belongs in the agent layer.

