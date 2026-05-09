# Spacelord Rebuild Plan

> **Status:** drafted 2026-05-09 against Spacelord HEAD `3ac9131` (post v1.0 hardening). This is a **forward-looking architecture document for the next-generation rewrite**, not a refactor of the current repo. Current repo ships v1.0 on 2026-05-13 as-is. The rebuild starts after launch.
>
> Read `memory/project_status_handoff.md` first for "what exists today." This doc is "what should exist next."

---

## 0. Why rebuild instead of refactor

The current repo is **not in fact too large** — 26.5K LOC of working domain logic is the moat (router, executor, OWS keychain, V1+V2 swap routing, limit orders, Power Law robot, forecast, Patch Network). Throwing that away would be self-harm.

What is wrong is the **shell around the core**:

1. **Module seams are blurred.** `src/controller.py` is a facade over routing, balance, broadcast, and CLI dispatch. `lib/` is a grab-bag of integration code. There is no clean adapter layer for exchanges (SaucerSwap, future Solana/HyperLiquid) — every cross-chain ambition will need that seam.
2. **Tests rotted silently.** Before today's CI commit, 10 of 105 tracked tests had been broken for weeks. Nothing ran them.
3. **No harness contract.** Today's CLI is a tightly-coupled REPL. Future harnesses (Claude Code subprocess, Codex CLI, your own agent harness) all hit the same untyped CLI surface and parse text. There is no JSON tool-call layer.
4. **No UI abstraction.** Telegram, terminal, future web all need the same "show user a transaction confirmation" — today there's only `lib/tg_format.py` and `print()`.

The rebuild keeps the working logic but rewrites the shell with **deliberate seams** so each one can evolve independently and an agent (Claude Code) can keep developing it without hand-holding.

The **HyperLiquid_Bot/agent-cli** repo is the floor reference, not the ceiling. Concrete patterns to copy: tiny `adapters/` interface (199 LOC, mock + real), `agent/tools.py` with READ-auto / WRITE-approval split, `guardian/` as the observability layer, and the `telegram/` registry+menu+approval triplet. Things to do better: a real **template-driven UI schema**, an explicit **harness contract**, and **per-skill memory** so agents don't relearn the project every session.

---

## 1. North Stars (carry forward)

These do not change in the rebuild:

- **Self-custody.** Keys, execution, AI stack live local. No custodial fallback.
- **NEVER SIMULATE the swap path.** Live execution always. `eth_call` pre-flight is "dry-run," a separate concept.
- **Don't change token IDs without explicit permission.** Mainnet token IDs are hardened path-mapping primitives.
- **Public repo is generic; personal layer is local.** Templated configs, gitignored runtime state.
- **Compatibility targets:** Claude Code, Codex CLI, and a future home-grown harness — equally first-class.
- **MCP / local LLMs / HCS:** deferred for hardware/cost reasons, not philosophy. Architecture must keep these reachable.

---

## 2. Architecture: the seams

The rebuild has **seven seams**, each with a single responsibility and a small contract:

```
┌────────────────────────────────────────────────────────────────────┐
│                         HARNESSES                                  │
│   Claude Code   │   Codex CLI   │   Own harness   │   Telegram     │
└───────┬────────────┬────────────────┬────────────────┬─────────────┘
        │            │                │                │
        └────────────┴───── HARNESS CONTRACT ──────────┘
                            (JSON tool-call protocol)
                                   │
                                   ▼
                          ┌────────────────┐
                          │  TOOL REGISTRY │  READ-auto / WRITE-approval
                          │  (agent layer) │  Typed input + output
                          └────────┬───────┘
                                   │
                  ┌────────────────┼────────────────┐
                  ▼                ▼                ▼
            ┌──────────┐    ┌──────────┐    ┌──────────┐
            │ ENGINES  │    │ GUARDIAN │    │   UI     │
            │ (logic)  │◄──►│ (safety, │    │ (schema  │
            │          │    │ gates,   │    │  + renderers)
            │          │    │ drift)   │    │          │
            └─────┬────┘    └─────┬────┘    └──────────┘
                  │               │
                  ▼               ▼
            ┌────────────────────────┐
            │      ADAPTERS          │
            │ Hedera │ Solana │ HL   │  Mock for tests
            └─────────┬──────────────┘
                      ▼
                 Real chains
```

**The rule:** each seam has a `__init__.py` that re-exports its public surface. Higher seams import only from lower-seam public surfaces. Lower seams never import from higher seams. CI enforces this with a 30-line import-graph linter.

---

## 3. Module layout

The exact directory layout for the rebuild repo. Sized targets in parentheses are *budgets*, not measurements (so the "constantly self-developed by Claude Code" goal stays honest — small files, single responsibility).

```
spacelord-v2/
├── adapters/                  (~500 LOC budget; thin)
│   ├── base.py                Abstract Adapter protocol (Pydantic models, async methods)
│   ├── hedera.py              Hedera adapter (wraps current src/executor + lib/saucerswap)
│   ├── solana.py              Stubbed; raises NotImplemented(planned: v2.x)
│   ├── hyperliquid.py         Stubbed; raises NotImplemented(planned: v2.x)
│   └── mock.py                Test double; deterministic responses
│
├── engines/                   (~6K LOC; the brain)
│   ├── router.py              Pathfinding (port of current src/router.py)
│   ├── pricing.py             Quote engines (port of lib/v2_liquidity, v1_saucerswap)
│   ├── limit_orders.py        Order daemon (port of src/limit_orders.py)
│   ├── power_law.py           Rebalancer (port of src/plugins/power_law/)
│   ├── forecast.py            Power Law projection
│   └── translator.py          NL → Intent (port of src/translator.py)
│
├── guardian/                  (~1K LOC; the safety layer)
│   ├── gates.py               Per-call gates (rate, daily-limit, whitelist, governance)
│   ├── drift.py               Detects when expected vs actual diverges (post-trade)
│   ├── knowns.py              Hardened ID registry (token IDs, contract addrs)
│   ├── friction.py            User-facing safety prompts (re-confirm, cooldowns)
│   └── cartographer.py        Logs the decision path for every WRITE op
│
├── agent/                     (~2K LOC; harness-agnostic tool layer)
│   ├── tools.py               JSON Schema for every tool (read + write)
│   ├── registry.py            Maps tool name → engine call + guardian gate
│   ├── execute.py             Single entry point: execute_tool(name, args, harness_ctx)
│   ├── approval.py            WRITE tools route through approval before execute
│   └── ui_emitter.py          Tools return UI cards (see §6) instead of strings
│
├── ui/                        (~800 LOC; template schema + renderers)
│   ├── schema.py              Pydantic models: ConfirmSwapCard, BalanceCard, etc.
│   ├── render_terminal.py     Renders cards as boxed text for REPL / Claude Code
│   ├── render_telegram.py     Renders cards as Telegram messages + inline keyboards
│   ├── render_json.py         Renders cards as raw JSON (for own-harness, future web)
│   └── templates/             One .py per card type; pure data + render rules
│
├── harness/                   (~600 LOC; the protocol)
│   ├── contract.py            JSON spec: tool_call, tool_result, ui_card envelope
│   ├── claude_code.py         Adapter for Claude Code (subprocess + slash-command surface)
│   ├── codex.py               Adapter for Codex CLI
│   ├── interactive.py         REPL adapter (current launch.sh interactive mode)
│   └── stdio.py               Generic stdio adapter for own-harness
│
├── cli/                       (~1.5K LOC; user-facing entry)
│   ├── main.py                Dispatcher (tiny — just routes to harness adapter)
│   └── commands/              One file per top-level command, each <200 LOC
│       ├── swap.py
│       ├── balance.py
│       └── ...
│
├── telegram/                  (~3K LOC; one harness)
│   ├── bot.py                 Telegram entry (long-poll or webhook)
│   ├── router.py              Inbound message → tool name + args (HL pattern)
│   ├── menu.py                Persistent menu / inline keyboards
│   ├── approval.py            WRITE-tool approval flow
│   └── memory.py              Per-chat short-term context
│
├── daemon/                    (~2K LOC; long-running)
│   ├── orders.py              Limit-order ticker
│   ├── robot.py               Power Law rebalancer ticker
│   └── supervisor.py          Process manager (restart, health)
│
├── common/                    (~1K LOC)
│   ├── models.py              Top-level Pydantic models (Token, Pool, Route, Order, ...)
│   ├── config.py              Layered config (env → local → defaults)
│   ├── crypto.py              OWS / keychain integration (port of src/credentials.py)
│   └── errors.py              Typed errors (port of src/errors.py)
│
├── tests/
│   ├── conftest.py            Autouse simulate-mode safety net
│   ├── unit/                  Test one module in isolation; use mock adapter
│   ├── integration/           Test seam boundaries (engine ↔ adapter, agent ↔ engine)
│   └── live/                  Opt-in via SPACELORD_LIVE_TESTS=true; gitignored copy in tests/local/
│
├── docs/
│   ├── architecture.md        This doc, but living
│   ├── adapters.md            How to write a new adapter
│   ├── tools.md               How to add a new agent tool
│   ├── ui.md                  How to add a new UI card
│   └── harnesses.md           How to add a new harness adapter
│
└── data/                      (templated; gitignored personal copies)
    └── templates/
```

**Why these budgets:** every file under ~300 LOC, every package under ~3K LOC, total under ~20K LOC. That's the size where Claude Code can read a whole module in one tool call, hold the relevant context, and edit it without thrashing.

---

## 4. The harness contract — making Claude Code, Codex, and your own harness all work

The current CLI is text-in/text-out. That's why every harness has to parse output. The rebuild defines a **strict JSON envelope** that any harness can speak.

Single contract (`harness/contract.py`):

```python
class ToolCall(BaseModel):
    tool: str                  # e.g. "swap"
    args: dict[str, Any]       # validated against agent.tools schema
    request_id: str            # uuid; pairs request → response
    harness: str               # "claude_code" | "codex" | "telegram" | "interactive" | "stdio"
    confirmed: bool = False    # WRITE tools: True only after approval

class ToolResult(BaseModel):
    request_id: str
    ok: bool
    ui_cards: list[UICard] = []  # see §6
    raw: dict[str, Any] | None   # only for harnesses that want it
    error: ErrorDetail | None

class ApprovalRequest(BaseModel):
    request_id: str
    tool: str
    args: dict[str, Any]
    ui_card: UICard            # the human-readable confirmation
    approve_id: str            # echoed back in a confirmed ToolCall
```

**What this gives you:**

- A new harness = ~150 LOC adapter that translates harness-native input to `ToolCall` and `ToolResult` to harness-native output. Adding "Codex CLI" or "your own harness" stops being an architectural question.
- Claude Code reads tool definitions from `agent.tools.schema()`, calls `execute_tool(tool_call)`, gets a structured `ToolResult` back. No prompt-stuffing, no fragile parsing.
- Telegram bot is just a harness adapter that turns inbound messages into `ToolCall`s and renders `ui_cards` via `render_telegram`.
- The interactive REPL (current `launch.sh`) becomes another harness adapter that uses `render_terminal`.

**Approval flow (agent-friendly):** WRITE tools (`swap`, `transfer`, `bridge`, `approve`) are dispatched as a `ToolCall(confirmed=False)`. The registry returns `ApprovalRequest` with a UI card. The harness shows it (Telegram inline keyboard, terminal prompt, Claude Code asks user). User approves → harness re-sends `ToolCall(confirmed=True, approve_id=...)`. **Same code path for every harness.**

---

## 5. The Spacelord router (port of HL's pattern, upgraded)

HL's `telegram/router.py` does this: inbound message → match against a registry of command patterns → emit a tool call. It works because the telegram bot is just **one harness over a tool layer**, not its own logic.

The Spacelord rebuild promotes this to first class:

```python
# engines/router.py is the SWAP router (existing — pathfinding).
# telegram/router.py is the COMMAND router (new) — different concept, different file.

# telegram/router.py
COMMANDS = [
    Command(pattern=r"swap (\d+\.?\d*) (\w+) (?:to|for) (\w+)",
            tool="swap",
            map_args=lambda m: {"amount": m[1], "from": m[2], "to": m[3]}),
    Command(pattern=r"balance",
            tool="balance",
            map_args=lambda _: {}),
    # ... declarative, all in one file
]

def route(message: str) -> ToolCall | None:
    for cmd in COMMANDS:
        if m := re.match(cmd.pattern, message):
            return ToolCall(tool=cmd.tool, args=cmd.map_args(m), ...)
    return None  # falls through to LLM agent if configured
```

**What this gives you over the current state:**

- The earlier "Telegram fast-lane" attempt failed because OpenClaw was in the path. Without OpenClaw (which the rebuild eliminates), the fast-lane is just `telegram/router.py` calling `agent/execute.py`.
- Slash commands in Claude Code, voice commands via Telegram, typed commands in Codex — same routing primitive in three different harness adapters.
- Adding a new command = appending one entry to a list. No surgery in three places.

---

## 6. Adaptive UI without MCP — template schema + renderers

You want adaptive GUI for things like transaction confirmations but don't want to commit to MCP yet. The right answer is a **typed UI schema** with **per-channel renderers**. MCP becomes one more renderer later, optionally.

```python
# ui/schema.py
class ConfirmSwapCard(BaseModel):
    kind: Literal["confirm_swap"] = "confirm_swap"
    from_token: str
    from_amount_human: str            # "12.34 USDC"
    to_token: str
    to_amount_estimated: str          # "0.0042 WBTC"
    fee_path: list[FeeStep]           # ordered fee/route hops
    risks: list[str]                  # ["price impact 1.2%", ...]
    approve_id: str                   # UUID echoed in approval

class BalanceCard(BaseModel):
    kind: Literal["balance"] = "balance"
    rows: list[BalanceRow]
    total_usd: str

# ui/render_terminal.py — turns ConfirmSwapCard into a boxed text block
# ui/render_telegram.py — turns it into Markdown + InlineKeyboardMarkup
# ui/render_json.py — turns it into raw JSON for own-harness / future web
```

**Why this is "adaptive enough" without MCP:**

- One Pydantic model per UI concept. Adding a new card = one file in `ui/templates/` + a render rule per renderer that cares.
- The renderer is per-harness. Telegram gets buttons, terminal gets a box, web (when it exists) gets JSON.
- An LLM agent can _generate_ a `ConfirmSwapCard` instance and pass it to the harness; the harness picks the renderer. That's the "adaptive" part — the data is the same, the surface adapts.
- When MCP-style adaptive UI matures, it becomes `ui/render_mcp.py` — a fourth renderer, no architectural shift required.

The two starter cards to build first: `ConfirmSwapCard` and `BalanceCard`. Everything else (`ApprovalCard`, `ErrorCard`, `OrderListCard`, `ForecastCard`) follows the same pattern.

---

## 7. Test discipline

The current repo's pytest pass rate (90/105) is the floor. The rebuild's expectation is **>95% on a tracked suite of 250+ tests**, with three tiers:

- **`tests/unit/`** — one module under test, all dependencies mocked via `adapters/mock.py`. Fast (`<5s` for the full unit suite). Run on every commit. **Target: 200+ tests.**
- **`tests/integration/`** — exercise a seam boundary (e.g. engine + adapter, agent + engine). Hits sim-mode adapter only. Run on every PR. **Target: 40+ tests.**
- **`tests/live/`** — opt-in via `SPACELORD_LIVE_TESTS=true`, gitignored copy in `tests/local/`. Runs against mainnet with capped amounts. Run manually before any release tag. **Target: 10–20 tests.**

The conftest's autouse `_force_simulation_mode` fixture stays. CI runs unit + integration, never live. Coverage gate set at 70% to start, raised at each minor version.

**`guardian/` gets its own test suite** (in `tests/unit/guardian/`) at 100% line coverage from day one — that's the safety layer; it can't be the part that rots.

---

## 8. Phased migration — concrete weeks

This is **post-launch** work. Launch v1.0 first (2026-05-13), watch it for a week, then start.

### Phase 0 — fork the new repo (1 day, week of 2026-05-19)

- New repo `spacelord-v2` (private at first). New worktree.
- Copy `adapters/`, `agent/`, `harness/`, `ui/`, `guardian/`, `engines/`, `common/` directory shells with `__init__.py` placeholders and `NotImplementedError`.
- Copy this `REBUILD_PLAN.md` to `spacelord-v2/docs/architecture.md`.
- Set up the same pytest scaffold + CI from `5ca89da`. Add ruff strict mode (no `continue-on-error`).

### Phase 1 — port the core engines (~2 weeks)

In dependency order. Each port is one PR, tests-first:

1. `common/models.py` (Token, Pool, Route, Order, AccountId — Pydantic v2)
2. `adapters/base.py` + `adapters/mock.py` (interface + test double; lock the contract here)
3. `adapters/hedera.py` (wrapping current `src/executor.py` + `lib/saucerswap.py`)
4. `engines/router.py` (port `src/router.py`, no behaviour change, full test coverage)
5. `engines/pricing.py` (port `lib/v2_liquidity` + `lib/v1_saucerswap`)
6. `engines/translator.py` (port `src/translator.py`, fix the 6 currently-failing translator tests)
7. `common/crypto.py` (port `src/credentials.py` — the OWS keychain integration)

Exit criteria: a script that does an HBAR → USDC swap end-to-end on mainnet, going through the new stack, succeeds.

### Phase 2 — agent + harness layer (~1 week)

1. `agent/tools.py` — define schemas for the 8 core tools (`swap`, `transfer`, `balance`, `approve`, `route_quote`, `limit_order_create`, `limit_order_cancel`, `forecast`).
2. `agent/registry.py` + `agent/execute.py` — the dispatcher.
3. `agent/approval.py` — WRITE-tool approval flow.
4. `harness/contract.py` — the JSON envelope.
5. `harness/interactive.py` — REPL adapter (replaces current `cli/main.py` interactive loop).
6. `harness/claude_code.py` — Claude Code skill files + tool definitions.
7. Smoke test: run a swap from the REPL via the new agent layer.

Exit criteria: the existing CLI commands all work, but they're now thin wrappers over the agent layer.

### Phase 3 — UI cards + Telegram (~1 week)

1. `ui/schema.py` — `ConfirmSwapCard`, `BalanceCard`, `ApprovalCard`, `ErrorCard`.
2. `ui/render_terminal.py` — replaces every `print()` in CLI with a card render.
3. `ui/render_telegram.py` — Markdown + inline keyboards.
4. `telegram/bot.py` + `telegram/router.py` + `telegram/approval.py` — the Telegram harness, fully on the new stack.
5. `harness/codex.py` — Codex CLI adapter (low priority but lock the seam now).

Exit criteria: same swap, executed three ways (REPL, Telegram, Claude Code slash), all rendering cards.

### Phase 4 — daemons, guardian, observability (~1 week)

1. `daemon/orders.py` (port limit-order daemon).
2. `daemon/robot.py` (port Power Law).
3. `guardian/gates.py` (port governance / whitelist / daily-limit checks).
4. `guardian/cartographer.py` — every WRITE op writes a structured decision log.
5. `guardian/drift.py` — post-trade variance check (expected vs actual).

Exit criteria: launch readiness for v2.0.

### Phase 5 — cross-chain (open-ended, post-v2.0)

1. `adapters/hyperliquid.py` (the easier one — Arbitrum bridge or direct).
2. `adapters/solana.py`.
3. New engine: `engines/cross_chain_router.py` — picks the right adapter for an intent.

---

## 9. Agent-friendly working rules (so Claude Code can actually self-develop this)

This is what makes "constantly self-developed by Claude Code" real, not aspirational:

1. **Every package has a `CLAUDE.md`.** ~150 lines. Explains the package's job, its public surface, and what NOT to touch. Loaded automatically when Claude Code edits files in that package.
2. **Every file under 300 LOC.** Larger means split. CI lints this with a one-line guard.
3. **No god-objects.** No `Controller` that knows about routing, signing, balance, and Telegram. Each seam owns its thing.
4. **Type-checked at boundaries.** Pydantic at every seam. mypy strict on `agent/`, `harness/`, `adapters/base.py`, `ui/schema.py` — the contract surfaces.
5. **Tests are the spec.** A new feature lands as a failing test first, then the implementation. (Hard rule for `guardian/`; aspirational for everything else.)
6. **One thing per commit.** No bundling. The commit message is the design doc.
7. **Per-skill `SKILL.md` files.** Drop the 1158-line monolith. Split into ~12 progressive-disclosure skills mapped to tools (per [HL's `telegram/CLAUDE.md` pattern]).
8. **`.local.md` overrides.** Every package can have a per-environment `.local.md` (gitignored) with personal settings, paths, account IDs.
9. **Decision logs in `guardian/cartographer.py`.** Every WRITE op writes one JSON line: `{ts, tool, args, decision_path, gate_results, outcome}`. Future-you (and future Claude Code) read these to understand "why did the bot do X."
10. **No backwards-compatibility shims for v1→v2.** Rebuild is a clean break. If you need a v1 piece, port it deliberately.

---

## 10. What this is NOT

To prevent scope drift:

- **Not an MCP migration.** MCP is opt-in via `harness/mcp.py` later. Not a v2.0 dependency.
- **Not a local-LLM project.** Hardware deferral stands. The LLM brain is OpenRouter / Anthropic API for now; that's a config knob, not architecture.
- **Not a UI framework.** The UI schema is data; renderers are dumb. No React, no widget toolkit. JSON in, surface out.
- **Not a microservice rewrite.** Single repo, single Python process. The seams are module boundaries, not network boundaries.
- **Not OpenClaw-compatible.** Clean break. If a future OpenClaw wants in, it writes a `harness/openclaw.py` adapter.

---

## 11. Open questions for you

- **New repo name?** `spacelord-v2`, `spacelord-core`, something else? Branding implications.
- **Public from day 0, or private until v2.0 ships?** I'd recommend private until phase 2 (agent layer working), then public so contributors can read the architecture doc.
- **Codex CLI as a first-class harness from phase 2, or phase 3?** Phase 3 is faster but means a week without Codex compatibility.
- **Telegram chat-router pattern: regex-based (HL style, simple) or LLM-fallback hybrid (regex first, LLM only for misses)?** Hybrid is more powerful but doubles the surface area.
- **Live test runner: Hedera testnet or capped-mainnet?** Mainnet catches more, costs more. Testnet is cheaper but pool liquidity is fake.
- **`guardian/cartographer.py` log destination:** local JSONL only, or also push to Hedera Mirror for tamper-evident provenance? The latter is the self-custody-flavoured answer; ~50 LOC extra.

Decide before phase 0. Each affects how phase 1 is structured.

---

**End of plan.** Update at the end of every phase; mark phases complete here, link to the PR(s) that delivered each.
