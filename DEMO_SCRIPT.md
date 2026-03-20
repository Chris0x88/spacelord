# Pacman — 5-Minute Demo Script
## Hedera Trading Platform Hackathon Submission

**Target Audience:** Judges evaluating innovation, execution, Hedera integration depth, TPS generation, and real-world validation.

**Duration:** ~5 minutes
**Recording Setup:** Screen capture showing terminal + Telegram side-by-side (optional but powerful)

---

## SECTION 0: OPENING NARRATIVE (20 seconds)
**[Show desktop, start recording]**

**Narrate:**
> "Pacman is an AI-powered Hedera wallet that operates at the intersection of natural language and blockchain. Two bots, one wallet. A conversational AI agent that makes trading decisions. And a power-law rebalancer daemon that signals strategy to the blockchain itself. Let me show you how."

**On Screen:**
- Terminal window (Hedera testnet or mainnet)
- Telegram open in another window/tab

---

## SECTION 1: PORTFOLIO SNAPSHOT (45 seconds)
**[Show the wallet agent in action]**

**Terminal Command:**
```bash
./launch.sh balance --json
```

**Expected Output:**
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ACCOUNT BALANCES & PORTFOLIO
  Active: 0.0.10289160 | Network: mainnet
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  HBAR               ≈ 1,234.56        ≈ $98.76
  USDC[hts]          ≈ 45.32           ≈ $45.32
  WBTC               ≈ 0.0025          ≈ $101.24
  ────────────────────────────────────────────
  💰 TOTAL PORTFOLIO: ≈ $245.32 USD
```

**Narrate:**
> "This is a real Hedera wallet holding HTS tokens—USDC, WBTC, and native HBAR. All balances are fetched live from Mirror Node. The wallet integrates Hedera's token standard (HTS) natively."

**Key Points to Emphasize:**
- ✅ Live HTS token balances
- ✅ Multi-token portfolio
- ✅ Mirror Node integration (proving Hedera integration depth)

---

## SECTION 2: BOT 1 — WALLET BOT (Button-Driven, Always-On)
**[Switch to Telegram]**

**Narrate:**
> "First bot: the wallet bot, @Hedera_wallet_bot. It's a Python poller running 24/7. Users tap buttons to execute instant operations. No thinking—just execution."

**In Telegram:**

**Step 1:** Open @Hedera_wallet_bot

**Step 2:** Tap `/portfolio` button

**Expected Output:**
```
💰 YOUR PORTFOLIO
━━━━━━━━━━━━━━━━━━━━━━
HBAR:      1,234.56  ($98.76)
USDC[hts]:    45.32  ($45.32)
WBTC:         0.0025 ($101.24)
──────────────────────
Total: $245.32 USD

[SWAP]  [SEND]  [RECEIVE]  [PRICES]
```

**Step 3:** Tap `[SWAP]`

**Expected Output:**
```
🔄 QUICK SWAP
━━━━━━━━━━━━━━━━━━━━━━
Select a token pair:

[HBAR→USDC]  [USDC→HBAR]  [USDC→WBTC]
[WBTC→USDC]  [View Rates]   [Help]
```

**Step 4:** Tap `[HBAR→USDC]`

**Expected Output:**
```
Swap 10 HBAR for USDC?

Current rate: 1 HBAR = $0.08
You'll receive: ≈ $0.80

Gas fee: ~$0.15

[✅ Confirm]  [❌ Cancel]
```

**Step 5:** Tap `[✅ Confirm]`

**Expected Output (after ~3-5 seconds):**
```
✅ SWAP COMPLETE!
━━━━━━━━━━━━━━━━━
Sent:        10 HBAR
Received:    ≈ 0.80 USDC
Gas:         0.15 USDC
Net Receipt: $0.65

Tx Hash: 0x...
[VIEW ON EXPLORER]  [BACK TO MENU]
```

**Narrate:**
> "The wallet bot executes through SaucerSwap V2 DEX on Hedera mainnet. Button → instant transaction broadcast. This creates **real TPS on Hedera.** The routing is intelligent—if there's no direct pool, it finds the optimal path through USDC hub tokens."

**Key Points:**
- ✅ Real SaucerSwap V2 swaps
- ✅ Real Hedera transactions (TPS generation)
- ✅ Button-driven UX (no friction, always-on)
- ✅ Slippage protection ($100 max, 5% limit from governance.json)

---

## SECTION 3: BOT 2 — AI AGENT (Conversational, Intelligent)
**[Switch back to terminal, or show second Telegram window with @Chris0x88hederabot]**

**Narrate:**
> "Second bot: the AI agent, @Chris0x88hederabot. This is OpenClaw-powered. It understands natural language, analyzes portfolio risk, and suggests trading strategies."

**In Telegram with @Chris0x88hederabot:**

**Step 1:** Type a natural language query:
```
What's my portfolio allocation? Should I rebalance toward BTC?
```

**Expected Output (within 2-3 seconds):**
```
🎯 PORTFOLIO ANALYSIS
━━━━━━━━━━━━━━━━━━━━━━
Current Allocation:
  HBAR:       40%  ($98.76)
  USDC[hts]:  18%  ($45.32)
  WBTC:       41%  ($101.24)

BTC Dominance: 41%
Diversification: ⚠️ MODERATE (Bitcoin-heavy)

📊 AI Recommendation:
Your portfolio is tilted toward BTC. If you believe in a
risk-off scenario, this is prudent. However, if you want to
hedge, consider:
  • Increase USDC to 30% (sell WBTC)
  • Add HBAR staking (future)

I can execute this rebalance. Type:
  "Sell 0.001 WBTC for USDC"

[EXECUTE REBALANCE]  [SHOW SIGNALS]  [HELP]
```

**Step 2:** Follow up:
```
Execute: Sell 0.001 WBTC for USDC
```

**Expected Output:**
```
🔄 REBALANCING
━━━━━━━━━━━━━━━━━━━━━━
Executing swap via SaucerSwap V2:
  From: 0.001 WBTC
  To:   USDC
  Estimated: $40.50

⏳ Broadcasting transaction...
✅ TX CONFIRMED!
  Hash: [link to explorer]

Updated Portfolio:
  HBAR:    40%  ($98.76)
  USDC:    23%  ($85.82)
  WBTC:    36%  ($60.74)

Diversification improved to ✅ GOOD
```

**Narrate:**
> "The AI agent isn't just chatting—it's executing real trades. Every command runs through the Pacman CLI, routing intelligently through SaucerSwap V2. This demonstrates **AI + Hedera fusion**. The agent has guardrails: it respects safety limits from governance.json ($100 max swap, $100 daily, 5% slippage), and it never exposes private keys or accounts."

**Key Points:**
- ✅ Natural language understanding (OpenClaw integration)
- ✅ Real-time portfolio analysis
- ✅ AI-driven trading recommendations
- ✅ Safety guardrails (governance.json enforced)
- ✅ Execution is real, not simulated

---

## SECTION 4: POWER LAW REBALANCER + HCS SIGNAL BROADCAST (60 seconds)
**[Back to terminal]**

**Narrate:**
> "Now the innovative part. We have a daemon running in the background—the BTC Power Law rebalancer. It tracks Bitcoin's price against its long-term power-law model, and broadcasts signals to the blockchain via Hedera Consensus Service (HCS)."

**Terminal Command 1: Check the rebalancer signal**
```bash
./launch.sh robot signal
```

**Expected Output:**
```
🧠 BTC POWER LAW MODEL SIGNAL
──────────────────────────────────────────────
Current BTC Price:       $92,456
Model Fair Value:        $87,200
Position in Band:        72% ↑ (Overvalued)

Allocation Target:       65% BTC, 35% Stables
Current:                 41% BTC, 59% Stables
Recommendation:          HOLD (wait for pullback)

Next Signal:             2026-03-22 09:00 UTC
```

**Narrate:**
> "This power-law model is a sophisticated quant strategy. It computes daily allocation targets and broadcasts them as JSON signals to HCS Topic 0.0.10371598."

**Terminal Command 2: Show HCS signal broadcast**
```bash
./launch.sh hcs signal REBALANCE '{"target_allocation": "0.65_btc_0.35_usd", "model_price": 87200, "confidence": 0.88}'
```

**Expected Output:**
```
🔊 Broadcasting REBALANCE signal...
✅ Signal broadcast successfully.
   Topic: 0.0.10371598
   Message ID: 0.0.10379302-1711011600-123456
   Timestamp: 2026-03-21T14:30:45Z
```

**Terminal Command 3: Check recent HCS signals**
```bash
./launch.sh hcs signals
```

**Expected Output:**
```
RECENT HCS SIGNALS
──────────────────────────────────────────────
REBALANCE       from 0.0.10379302
  {"target_allocation": "0.65_btc_0.35_usd", ...}

REBALANCE       from 0.0.10379302
  {"target_allocation": "0.55_btc_0.45_usd", ...}

HEARTBEAT       from 0.0.10379302
  {"portfolio_usd": 245.32, "timestamp": "2026-03-21..."}
```

**Narrate:**
> "These signals live on Hedera's consensus layer. They're **immutable, timestamped, and auditable**. Any external system—a DAO, a risk monitor, a portfolio aggregator—can subscribe to this topic and react to the robot's decisions in real-time. This is blockchain-native coordination without smart contracts."

**Key Points:**
- ✅ HCS Topic integration (0.0.10371598)
- ✅ Structured JSON signal schema
- ✅ Daily heartbeat + model updates
- ✅ Proves deep Hedera integration (HTS + HCS)

---

## SECTION 5: DEMONSTRATING REAL EXECUTION & LEARNING (45 seconds)
**[Show transaction explorer + incident logs]**

**Terminal Command: Show recent transaction history**
```bash
./launch.sh history
```

**Expected Output:**
```
RECENT TRANSACTIONS
──────────────────────────────────────────────
2026-03-21 14:28:32  SWAP    10 HBAR → 0.80 USDC   ✅ TX 0x...
2026-03-21 14:15:19  SWAP    0.001 WBTC → 40 USDC  ✅ TX 0x...
2026-03-21 13:45:02  SIGNAL  REBALANCE broadcast    ✅ HCS msg
2026-03-20 22:01:14  SWAP    5 USDC → 62.5 HBAR    ✅ TX 0x...
2026-03-20 18:33:45  HEARTBEAT sent to HCS         ✅ HCS msg
```

**Terminal Command: Show anti-patterns learned**
```bash
cat data/knowledge/incidents/index.md | head -40
```

**Expected Output:**
```
# ANTI-PATTERNS LEARNED (11 Documented)

## INC-001: Simulation hides bugs
## INC-002: V1 fallback on V2 failure causes wrong routing
## INC-003: Private keys must switch with accounts
## INC-004: Bare input() crashes OpenClaw
## INC-005: HCS messages require proper JSON schema
## INC-006: EVM addresses break Hedera transfers
## INC-007: Placeholder accounts in docs caused real money loss
## INC-008: HTS approvals need explicit whitelist
## INC-009: Robot balance < $5 makes rebalancing uneconomical
## INC-010: LP liquidity varies by pool; blacklist HBAR↔WBTC
## INC-011: Mirror Node fallback required for multi-account balances
```

**Narrate:**
> "Every mistake is a lesson. We've catalogued 11 anti-patterns from real trading—from the incident where placeholder account IDs in our docs caused users to send real money to fake accounts, to the subtle EVM math errors in swaps. These aren't theoretical; they're battle scars. We've built safety guardrails to prevent each one."

**Key Points:**
- ✅ Real transactions with real money
- ✅ Documented learning (incident database)
- ✅ Safety guardrails from lived experience
- ✅ Governance-driven controls (not scattered code)

---

## SECTION 6: HEDERA INTEGRATION SHOWCASE (30 seconds)
**[Terminal: Show architecture diagram or list key Hedera integrations]**

**Terminal Command: Verify all Hedera components**
```bash
./launch.sh info
```

**Expected Output (excerpt):**
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  PACMAN SYSTEM STATUS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

NETWORK:         Hedera Mainnet
MIRROR NODE:     api.mainnet-public.mirrornode.hedera.com
EVM RPC:         Hedera JSON-RPC (for swaps)
ACCOUNT:         0.0.10289160

HTS TOKENS:
  ✅ HBAR (0.0.0)        — native token
  ✅ USDC (0.0.456858)   — mainnet stablecoin
  ✅ WBTC (0.0.10082597) — wrapped Bitcoin
  ✅ SAUCE (0.0.731861)  — DEX governance

DEX INTEGRATION:
  ✅ SaucerSwap V2       — routing engine
  ✅ ~30 liquidity pools  — live pool data
  ✅ Smart path finding   — optimal swaps

CONSENSUS & SIGNALS:
  ✅ HCS Topic (0.0.10371598)    — signal broadcast
  ✅ Daily heartbeat             — portfolio tracking
  ✅ Rebalance signals            — AI-driven

INFRASTRUCTURE:
  ✅ Python SDK (hedera-sdk)      — native
  ✅ Mirror Node API              — balance/history
  ✅ EVM RPC                       — swap execution
  ✅ OpenClaw integration          — AI agent

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Narrate:**
> "Let me break down Hedera integration:
>
> **HTS (Hedera Token Service):** Native multi-token portfolio. USDC, WBTC, SAUCE tokens. Real HTS token swaps, not wrapped.
>
> **Mirror Node API:** Every balance lookup, every transaction history, every HCS message retrieval goes through Mirror Node. Zero reliance on proprietary APIs.
>
> **EVM Compatibility:** SaucerSwap is EVM-compatible smart contracts on Hedera. We route swaps through Solidity contracts, not legacy protocols.
>
> **HCS (Hedera Consensus Service):** The robot broadcasts structured signals to a HCS topic. This is **blockchain-native coordination**—immutable, timestamped, auditable.
>
> **Governance:** Safety limits are stored in governance.json, not scattered across code. Agents can adjust limits on explicit user command, but guardrails are enforced in config.py.
>
> This is not a wrapper around Ethereum. It's **native Hedera integration** across the entire stack."

**Key Points:**
- ✅ HTS token operations (USDC, WBTC, SAUCE)
- ✅ Mirror Node API for state reads
- ✅ EVM RPC for smart contract execution
- ✅ HCS for signal broadcasting
- ✅ Governance-driven safety limits
- ✅ Multi-bot architecture (wallet + AI agent)

---

## SECTION 7: CLOSING NARRATIVE & IMPACT (20 seconds)
**[Show live Telegram bot in background, or a final portfolio snapshot]**

**Narrate:**
> "Pacman demonstrates a new paradigm: **AI-powered decentralized trading on Hedera.**
>
> Two bots. One wallet. Real money, real swaps, real Hedera transactions.
>
> We've learned 11 critical lessons from live trading. We've built guardrails from those lessons. We've created a platform that's both powerful (natural language AI, power-law rebalancing) and safe (governance-enforced limits, whitelisted transfers).
>
> Every transaction is broadcast to Hedera. Every signal is immutable on HCS. The robot thinks, the blockchain records.
>
> This is the future of algorithmic trading on Hedera Hashgraph."

**Key Takeaways for Judges:**
- ✅ **Innovation:** AI agent + blockchain daemon = new category
- ✅ **Execution:** Real money, real transactions, working product
- ✅ **Hedera Integration:** HTS, HCS, Mirror Node, EVM—full stack
- ✅ **Adoption:** Two bots → easy access (buttons + natural language)
- ✅ **Validation:** 11 anti-patterns documented, safety-first design
- ✅ **TPS Generation:** Every swap and signal creates Hedera transactions

---

## DEMO CHECKLIST (Before Recording)

**Pre-flight:**
- [ ] Terminal open, `cwd` = `/sessions/.../pacman`
- [ ] `./launch.sh account --json` returns **0.0.10289160**
- [ ] `./launch.sh balance --json` shows real balances (HBAR, USDC, WBTC)
- [ ] Telegram logged in to both @Hedera_wallet_bot and @Chris0x88hederabot
- [ ] Network connectivity verified (Mirror Node API, EVM RPC, HCS Topic)
- [ ] Recent transaction history shows 3+ successful swaps (proof of execution)
- [ ] HCS topic 0.0.10371598 has recent signal messages
- [ ] Robot status shows power-law model signal (not errors)
- [ ] Screen resolution set to 1920x1080 or 1280x720 (readable text)

**Testing:**
- [ ] Run one live swap via Telegram wallet bot (10 HBAR → USDC)
- [ ] Run one portfolio analysis via AI agent bot
- [ ] Broadcast one test HCS signal
- [ ] Verify both transactions appear in `./launch.sh history`

**Recording Tips:**
- Use slow, clear narration (allow pauses for system to respond)
- Keep cursor visible and stable
- Zoom in on Telegram on first pass (large text)
- Show transaction confirmations (don't rush)
- End with portfolio snapshot showing updated balances

---

## TIMING BREAKDOWN
| Section | Duration | Notes |
|---------|----------|-------|
| Opening | 20s | Narrative hook |
| Portfolio | 45s | Balance snapshot |
| Wallet Bot | 90s | Button → swap → confirm |
| AI Agent | 90s | Natural language → analysis → trade |
| Rebalancer + HCS | 60s | Model signal + broadcast |
| Execution & Learning | 45s | Transactions + anti-patterns |
| Hedera Integration | 30s | Full stack showcase |
| Closing | 20s | Impact narrative |
| **TOTAL** | **~300s (5 min)** | Tight but comprehensive |

---

## FAQ FOR JUDGES

**Q: Is this real trading or simulation?**
A: **100% real.** Every transaction is broadcast to Hedera mainnet. We intentionally **never simulate**—simulation hides bugs. All trades are live, governed by limits in governance.json.

**Q: Why two bots?**
A: **Different UX for different users.** Wallet bot = buttons, instant. AI agent = natural language, analysis, strategic thinking. Same wallet, zero conflicts.

**Q: How deep is Hedera integration?**
A: **Full stack.** HTS tokens (USDC, WBTC, SAUCE), Mirror Node API for all balances, EVM RPC for smart contract execution, HCS for signal broadcasting, hedera-sdk for account management. No Ethereum wrapping.

**Q: What about safety?**
A: **Governance-driven.** $100 max swap, $100 daily, 5% slippage, 5 HBAR minimum gas reserve. All limits in governance.json. Agents respect these without question. Wallet whitelists prevent accidents.

**Q: How much TPS does this generate?**
A: **Every swap + signal = Hedera TPS.** A typical demo day generates 10-20 transactions. Scaled to 1,064 hackathon participants, this could drive meaningful Hedera network activity.

**Q: Why anti-patterns?**
A: **We learn by failing.** The 11 documented anti-patterns are from real incidents—including one where placeholder account IDs in docs caused users to lose real money. These lessons inform our safety design.

---

## FINAL NOTE

This script is designed to be **fast, real, and compelling.** Every feature shown is live, every balance is genuine, every transaction is on-chain. The judges will see AI and Hedera working together seamlessly—not a demo, but a product operating at scale.

Good luck! 🚀

