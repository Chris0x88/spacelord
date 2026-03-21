# Pacman Tools — Environment-Specific Configuration

## Entry Point
All CLI commands: `./launch.sh <command>`
Working directory: The pacman repository root (where launch.sh lives)

## Accounts
- **Main**: `HEDERA_ACCOUNT_ID` — user trading wallet
- **Robot**: `ROBOT_ACCOUNT_ID` — autonomous rebalancer (nickname: "Bitcoin Rebalancer Daemon")
- Switch with: `./launch.sh account switch <id_or_nickname>`

## Daemons
- Start: `./launch.sh daemon-start`
- Stop: `./launch.sh daemon-stop`
- Status: `./launch.sh daemon-status`
- Dashboard: http://127.0.0.1:8088

## HCS Topic
- Signal topic: `0.0.10371598`
- Check: `./launch.sh hcs status`

## Network
- Network: Hedera Mainnet
- DEX: SaucerSwap V2
- RPC: https://mainnet.hashio.io/v1

## Key Commands for Quick Reference
```
./launch.sh status --json         # Full portfolio + account info
./launch.sh balance --json        # Token balances with USD
./launch.sh robot status --json   # Rebalancer state
./launch.sh doctor                # System health check
./launch.sh account --json        # All known accounts
./launch.sh history               # Recent transactions
./launch.sh price bitcoin         # Live BTC price + model
```
