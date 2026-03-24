# Space Lord Heartbeat

Scheduled via OpenClaw cron at 6 AM and 6 PM daily.
Execute these checks in order. If ALL pass, respond with `HEARTBEAT_OK`.
If any issue is found, send a concise alert to the user.

## Checks

- [ ] **Daemon health**: Run `./launch.sh daemon-status`
  - If not running → start with `./launch.sh daemon-start`, then report: "Daemons were down. Restarted."
  - If running → note PID, continue

- [ ] **HBAR gas reserve**: Run `./launch.sh balance --json`
  - Parse `hbar.balance` from JSON
  - If < 5 HBAR → ALERT: "Low gas: {balance} HBAR. You need >= 5 to transact."
  - If < 2 HBAR → CRITICAL: "Gas critically low at {balance} HBAR. Assets may be stranded."

- [ ] **Robot rebalancer**: Run `./launch.sh robot status --json`
  - Parse `signal.allocation_pct` and `signal.phase`
  - If signal phase changed since last check → report: "BTC model shifted to {phase}. Target allocation: {allocation_pct}%"
  - If robot should be running (funded > $5) but isn't → report
  - If portfolio $0 → skip silently (unfunded, not an error)

- [ ] **Limit orders**: Run `./launch.sh order list --json`
  - Check for orders with status "triggered" or "filled"
  - Report any triggered orders: "Order {id} triggered: {description}"

- [ ] **Daemon errors**: Run `tail -5 daemon_output.log`
  - Scan for ERROR, CRITICAL, Traceback, or exception patterns
  - Report if found: "Daemon errors detected — run `./launch.sh doctor` for details"

## Response Format

All clear:
```
HEARTBEAT_OK — Daemon up (PID {pid}), {hbar} HBAR, robot {status}, {n} open orders
```

Issues found:
```
HEARTBEAT_ALERT
- {issue 1}
- {issue 2}
```
