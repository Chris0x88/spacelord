# Pacman Project Plan

**Last Updated:** 2026-04-05 AEST

## 🐛 Bug Fixes

### BUG-001: HCS broadcast_signal() sender_override mismatch
**Status:** ✅ Resolved (2026-05-13, commit 21f2b4c)
**Severity:** Medium (caused error log spam, non-fatal)
**Detected:** 2026-04-05 by heartbeat monitor

**Symptom:** HCS heartbeat broadcast failed every cycle with:
```
HcsManager.broadcast_signal() got an unexpected keyword argument 'sender_override'
```
264+ attempts, retrying every 3600s.

**Root Cause:** `src/controller.py` lazy-imported the legacy `src/plugins/hcs_manager.py`, whose `broadcast_signal()` lacks the `sender_override` kwarg. `src/plugins/power_law/bot.py` passes it on every heartbeat.

**Fix:** Option 1 applied — swapped the import in `src/controller.py` to `src.plugins.hcs.hcs_manager` (strict API superset; `broadcast_signal(..., sender_override=None)`). Drop-in, no other callers affected, 90/90 tests still pass.

---

### BUG-002: OpenClaw agent recites stale balances from MEMORY.md (memory poisoning)
**Status:** ✅ Resolved (2026-05-13)
**Severity:** High (agent reported fabricated balances to user — failure of "NEVER simulate" principle)
**Detected:** 2026-05-13 — user reported chat showing 41.56 HBAR / 5.70 USDC / 45.04 SAUCE for Main when mirror node showed 3.68 HBAR / 0 tokens.

**Symptom:** Agent answers "what's my balance?" by reciting values from `openclaw/MEMORY.md` instead of running `./launch.sh balance`. Values can be days stale.

**Root Cause:** `openclaw/SOUL.md` explicitly instructed: *"After balance checks → update Portfolio State (balances, USD totals, timestamp)"*. The agent followed instructions: it wrote balances to memory, then later sessions read them back as fact. Same pattern for Robot State.

**Fix:**
- `openclaw/SOUL.md` — replaced Memory Persistence section with a HARD RULE forbidding live state in memory.
- `openclaw/defaults/MEMORY.md` — removed Portfolio State / Robot State templates; added top-of-file HARD RULES block.
- `openclaw/scripts/memory-prune.py` (local-only) — removed "Portfolio State" / "Robot State" from the protected-headers keep-list so any future re-introduction gets archived out.

---

## 🎯 High Priority Initiatives

### 1. LayerZero USDT0 → Arbitrum Bridge (Hedera → Hyperliquid)
**Status:** Planned  
**Owner:** TBD  

**Objective:** Enable seamless cross-chain transfers of USDT0 from Hedera to Arbitrum, then to Hyperliquid for trading.

**Key Tasks:**
- [ ] Research LayerZero USDT0 contract architecture and bridge mechanics
- [ ] Integrate LayerZero messaging/endpoint into Pacman CLI
- [ ] Implement Hedera → Arbitrum bridge transaction flow
- [ ] Implement Arbitrum → Hyperliquid transfer path
- [ ] Add gas estimation and fee calculation for bridge operations
- [ ] Test on testnet (Hedera Testnet → Arbitrum Sepolia)
- [ ] Safety checks: bridge status monitoring, refund handling, failure recovery
- [ ] CLI commands: `pacman bridge layerzero usdt0 from:hedera to:hyperliquid`

**Dependencies:**
- LayerZero contract deployment on Hedera and Arbitrum
- USDT0 token contracts on both chains
- Hyperliquid deposit address handling

**Notes:**
- This is a high-value feature for arbitrage and liquidity management
- Consider speed vs cost tradeoffs (LayerZero is ~1-2 mins)
- Need to track bridge transaction status and receipts

---

### 2. OpenWallet Key Management Integration
**Status:** Planned  
**Owner:** TBD  

**Objective:** Integrate OpenWallet for secure, hardware-backed private key storage and transaction signing on Hedera.

**Key Tasks:**
- [ ] Evaluate OpenWallet API/SDK capabilities and authentication models
- [ ] Design key derivation and session management flow
- [ ] Implement OpenWallet connector module in `lib/` or `cli/`
- [ ] Add wallet connection command: `pacman wallet connect openwallet`
- [ ] Implement transaction signing delegation (wallet signs, CLI broadcasts)
- [ ] Support multiple wallet profiles (wallet A for trading, wallet B for staking)
- [ ] Add wallet status commands: balance, chain ID, account info
- [ ] Test with OpenWallet mobile app (Bluetooth/USB) and browser extension
- [ ] Documentation: setup guide, security considerations, troubleshooting

**Dependencies:**
- OpenWallet SDK/API availability for Python/macOS
- Hedera wallet address derivation compatibility (ED25519 keys)
- User device compatibility testing

**Security Requirements:**
- Private keys NEVER leave the OpenWallet device
- All signing happens on-device; CLI only gets raw signed transactions
- Session timeout and revocation mechanisms
- Clear user consent prompts for every transaction
- Audit trail of wallet-connected operations

**Notes:**
- This improves security posture vs local keystores
- Enables mobile-first workflows (phone signs, Mac broadcasts)
- Consider fallback to local keystore if OpenWallet unavailable

---

### 3. Power Law Floor Projection Tool
**Status:** Planned  
**Owner:** TBD  

**Objective:** Provide a command to estimate the future date when the Power Law model's floor price will reach a specified USD value (e.g., $66,000), aiding strategic planning.

**Key Tasks:**
- [ ] Extract the Power Law floor calculation from the robot module (deterministic formula based on time)
- [ ] Expose as a library function: `calc_floor(date) → usd`
- [ ] Implement projection via binary search or day-by-day iteration to find date where floor ≥ target
- [ ] Add CLI command: `./launch.sh powerlaw-projection --target <usd>` with output: "Floor reaches $X in approximately Y days (date)"
- [ ] Optionally integrate into `robot status` as: "Floor projection to $66k: ~<date>"
- [ ] Write unit tests verifying projection against historical floor values
- [ ] Document in TOOLS.md and AGENTS.md

**Dependencies:**
- Understand the exact model's time dependency (e.g., days since Bitcoin genesis/halving)
- Ensure calculation is deterministic and does not require live market data

**Notes:**
- Current floor (2026-03-29): $58,593.60; target $66–67k is ~12–14% higher.
- Without implementation, a rough estimate based on observed monthly growth (1–2%) suggests 7–12 months (Oct 2026 – Mar 2027). This is uncertain; use the tool for accuracy.

---

## 📋 Other Active Projects (Context)

See also:
- `MEMORY.md` for ongoing project context
- `docs/roadmap.md` (if exists) for longer-term vision
- `backups/` for historical project artifacts

---

## ✨ Contributing

Found an issue or want to help? Check `CONTRIBUTING.md` and open a PR!
