# SaucerSwap Integration Comparison

> Space Lord vs hak-saucerswap-plugin (Hedera Agent Kit)

**Date:** 2026-03-23
**Their repo:** [hak-saucerswap-plugin](https://github.com/Chris0x88/hak-saucerswap-plugin)

---

## Summary

Fundamentally different architectures. Space Lord implements a local routing engine with direct smart contract calls. The HAK plugin wraps SaucerSwap's hosted REST API.

## hak-saucerswap-plugin

A TypeScript plugin for [Hedera Agent Kit](https://github.com/hashgraph/hedera-agent-kit). Clean, well-structured npm package with 6 tools (swap, quote, pools, liquidity, farms).

**Routing approach:**
1. Calls `api.saucerswap.finance/v1/swap/quote` for quotes
2. Takes the quote and builds a `ContractExecuteTransaction` calling `swapExactTokensForTokens`
3. Basic AMM math for price impact and slippage

**Characteristics:**
- Depends on SaucerSwap's hosted API for quotes, token resolution, and pool discovery
- No local pool registry — entirely API-driven
- No multi-hop pathfinding — delegates to the API
- No governance, safety limits, or whitelists
- No WHBAR handling or ERC20/HTS variant awareness
- Framework-locked to Hedera Agent Kit
- Has liquidity management (add/remove LP) and farming discovery — Space Lord has LP management as a separate plugin, farming discovery not yet implemented

## Space Lord

A standalone Python CLI application with a custom routing engine. 30+ commands across the full DeFi stack.

**Routing approach:**
1. Local pool registry (`pools_v2.json`) — no API dependency
2. Custom multi-hop pathfinding in `SpaceLordVariantRouter` — understands Hedera's dual-token system
3. Direct JSON-RPC calls to SaucerSwap smart contracts
4. WHBAR wrap/unwrap as explicit route steps
5. Governance enforcement before execution

**Characteristics:**
- No API dependency for routing — works even if SaucerSwap's API goes down
- Variant-aware (ERC20 vs HTS) — the other plugin doesn't handle this
- Multi-step routes with cost estimation and confidence scoring
- Framework-agnostic (CLI tool use, works with any agent)
- Full governance: per-swap limits, daily caps, slippage ceilings, transfer whitelists

## Side-by-Side

| | **hak-saucerswap-plugin** | **Space Lord** |
|---|---|---|
| **Routing** | SaucerSwap REST API | Local pool registry + direct contract calls |
| **API dependency** | Yes — `api.saucerswap.finance` | No — JSON-RPC to contracts directly |
| **Multi-hop** | Delegated to API | Custom pathfinding |
| **WHBAR handling** | None | Full wrap/unwrap routing |
| **ERC20/HTS variants** | Not addressed | Core feature |
| **Governance/safety** | None | Per-swap limits, daily caps, whitelists |
| **Scope** | SaucerSwap only (6 tools) | Full DeFi toolkit (30+ commands) |
| **Liquidity mgmt** | Yes (add/remove) | Yes (separate plugin) |
| **Farming** | Yes (discovery) | Not yet (easy addition) |
| **Framework** | Hedera Agent Kit (TypeScript) | Any agent via CLI (Python) |
| **Codebase** | ~1-2K LOC (focused plugin) | ~10K+ LOC (full application) |

## Conclusion

Not really competitors — different categories. The HAK plugin is a thin integration layer for a specific agent framework. Space Lord is a standalone application with its own routing engine, governance model, and training pipeline. The claim of "first open-source SaucerSwap V2 router" holds in the sense of local pathfinding without API dependency.
