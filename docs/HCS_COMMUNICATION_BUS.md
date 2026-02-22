# HCS Communication Bus Architecture

## Overview

This document outlines the design principles and implementation strategy for building a **Hedera Consensus Service (HCS) communication bus** for AI agents in the Pacman ecosystem. The approach leverages **TOON 3.0** (Token-Oriented Object Notation) as a lossless compression protocol to achieve hyper-efficient agent-to-agent messaging.

---

## Key Concepts

### 1. TOON 3.0 - Lossless JSON Compression

**What it is:**  
TOON 3.0 is an officially standardized format (late 2025) that compresses JSON by removing braces and repetitive keys, reducing token usage by **30–60%** while maintaining full data fidelity.

**Why it matters:**
- **Cost efficiency:** Fewer tokens = lower API bills when sending data to/from AI models
- **Context optimization:** Packs more information into limited context windows
- **Network efficiency:** Smaller payloads on HCS mean lower fixed fees per message

**Example transformation:**

```json
{
  "from": "agent_A",
  "to": "agent_B",
  "type": "trade_signal",
  "payload": {
    "token": "WBTC",
    "action": "BUY",
    "amount": 1000
  }
}
```

↓ TOON 3.0 ↓

```
A:agent_A>B:agent_B|type:trade_signal|token:WBTC>action:BUY>amount:1000
```

### 2. HCS - Verifiable Message Bus

**What it is:**  
Hedera Consensus Service (HCS) provides a permanent, tamper-proof, ordered log of messages. Each message is anchored to the Hedera mainnet with a fixed fee of **$0.0001 per message**.

**Why HCS for AI agents:**
- **Fixed cost:** Unlike gas-based chains, HCS fees are predictable and near-zero
- **Finality:** Messages are consensus-secured and immutable
- **Ordering:** Guarantees message sequence, critical for multi-step agent workflows
- **Audit trail:** Complete, verifiable history of agent decisions

### 3. The Layered Architecture

```
┌─────────────────────────────────────────────┐
│   Interface Agents (User-Side)              │
│   • Lightweight, local                     │
│   • Human-friendly formats (JSON/NLP)      │
│   • Handles encryption/auth                │
└───────────────┬─────────────────────────────┘
                │ TOON-compressed streams
┌───────────────▼─────────────────────────────┐
│   Logic Layer (AI Kernels)                 │
│   • Dense, token-efficient                 │
│   • English/Code focused                   │
│   • Emits TOON, receives compressed       │
└───────────────┬─────────────────────────────┘
                │ HCS messages
┌───────────────▼─────────────────────────────┐
│   HCS (Hedera Consensus Service)           │
│   • Permanent, ordered, tamper-proof      │
│   • Fixed $0.0001 per message             │
│   • Verifiable anchor point               │
└─────────────────────────────────────────────┘
```

**Core principle:**  
Agents should not need 146 languages. Instead:
- **Logic kernels** use compressed TOON for internal communication
- **Interface agents** handle presentation/parsing for human interaction

---

## HCS Standards & Agent IDs

### HCS-14: Universal Agent IDs

A new standard for identifying AI agents on-chain:
- Format: `0.0.<agent_number>` (Hedera ID structure)
- Registered on the network with metadata endpoint
- Enables discoverability and permissioning

**Implementation note:**  
When building Pacman's agent swarm, assign each AI component a stable HCS-14 ID and broadcast capabilities on a dedicated topic.

---

## Implementation Guide

### Topic Design

**One topic per agent type** to avoid noise:
- `0.0.<topic_id>` format
- Example topics:
  - `price_feed_aggregator`
  - `trade_router`
  - `risk_manager`
  - `execution_engine`

### Message Structure (TOON-compressed)

```toon
# Basic envelope
src:<agent_id>>dst:<agent_id>|seq:<uint64>|ts:<timestamp>|type:<message_type>|body:<compressed_payload>

# Example: Trade execution request
src:0.0.1001>dst:0.0.1002|seq:12345|ts:1737412345|type:execute|body:token:WBTC>side:BUY>qty:1000>limit:67000

# Example: Price update broadcast
src:0.0.2001>dst:BROADCAST|seq:98765|ts:1737412400|type:price_update|body:pair:WBTC-USDC>bid:67010>ask:67020>ts:1737412399
```

### Compression Strategy

**What to compress:**
- Repetitive field names (use short keys: `t` instead of `token`)
- Numeric values (no quotes)
- Nested structures (flatten when possible)
- Common enums (pre-defined codes)

**What NOT to compress:**
- Critical metadata (agent IDs, sequence numbers, timestamps)
- Fields requiring human readability in audits
- Cryptographic signatures

**Implementation approach:**
```python
def toon_compress(data: dict) -> str:
    # 1. Replace long keys with short aliases
    key_map = {
        "token": "t",
        "action": "a",
        "amount": "q",
        "price": "p",
        "timestamp": "ts",
        "sequence": "seq",
        "from": "src",
        "to": "dst"
    }
    # 2. Remove braces, use > for object delimiters, | for field separators
    # 3. Numeric values as raw numbers (no quotes)
    # 4. Enums as single letters where safe
    pass
```

### Sequence Numbers & Idempotency

- Each agent must maintain **per-topic sequence numbers**
- HCS guarantees ordering, but duplicate messages can occur in edge cases
- Include `seq` in envelope and implement **idempotent processing**

### Error Handling

**TOON parsing failures:**
- Send NACK message with original `seq` and error code
- Do not crash the agent; log and continue

**HCS timeouts:**
- Set reasonable expectations: HCS finality ~3–7 seconds
- Implement async pipelines; don't block on single message

---

## Security Considerations

### Agent Authentication

- HCS messages are public; **never** include secrets in plaintext
- Use **pre-commit encryption** for sensitive payloads
- Consider **HCS-15** (encrypted message envelope) once standardized

### Input Validation

- Always validate TOON structure before processing
- Sanity-check numeric ranges (e.g., amounts cannot be > total supply)
- Replay protection: reject messages with old `seq` numbers per sender

### Access Control

- Use HCS topic permissions to restrict who can submit
- Agents should verify message signatures if sender authentication is required

---

## Performance Optimization

### Batching

- Multiple logical updates can be packed into one HCS message
- Use array notation: `body:[{...},{...}]`
- Balance batch size vs. latency requirements

### Compression Savings Target

- **Baseline (JSON):** ~200–500 tokens per complex trade signal
- **TOON 3.0:** ~80–200 tokens (40–60% reduction)
- **Impact:** Direct cost reduction on LLM API calls + faster processing

---

## Development Roadmap

**Phase 1: Core HCS Integration**
- Set up HCS client for Pacman (Node.js/Python)
- Implement TOON encoder/decoder library
- Create test topic and broadcast mock messages

**Phase 2: Agent Swarm**
- Issue HCS-14 IDs for Pacman's internal agents
- Design message schemas per agent type
- Implement sequence management and ACK/NACK protocol

**Phase 3: Compression Tuning**
- Profile token usage across agent interactions
- Optimize key aliasing for most common fields
- Benchmark against JSON baseline

**Phase 4: Production Hardening**
- Add encryption layer for sensitive data
- Implement monitoring for HCS health (latency, fees)
- Archive strategy for long-term message storage

---

## Why This Matters for Pacman

Pacman is building an **AI-driven trading agent** that needs to:
- Route trades efficiently (low latency)
- Exchange rich data (price feeds, risk signals)
- Stay within budget (avoid excessive LLM token costs)
- Maintain auditability (regulatory compliance)

**TOON on HCS** is tailor-made for this:
- **Fixed fees** on Hedera make high-frequency agent messaging affordable
- **Compressed messages** keep LLM context windows usable
- **Permanent log** provides audit trail required for financial operations
- **Layered design** lets Pacman's logic layer be dense/formal while interface remains user-friendly

This is exactly the architecture the community is converging on for "Agentic AI" on Hedera. Building it now positions Pacman at the forefront of the trend.

---

## References

- TOON 3.0 Specification (2025)
- HCS-14: Universal Agent Identifiers (Hedera Improvement Proposal)
- HCS Message Bus Patterns (Hedera Docs)
- Hedera Fee Schedule: $0.0001 per HCS message (fixed)

---

**Maintained by:** Pacman Engineering  
**Last updated:** 2026-02-22  
**Status:** Draft - Implementation pending
