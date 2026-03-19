#!/usr/bin/env python3
"""
Knowledge Harvester — Convert incidents, antipatterns, and feedback into training data
=======================================================================================

Outputs:
  training_data/preference_pairs.jsonl   — DPO format (chosen vs rejected)
  training_data/error_fix_pairs.jsonl    — Error diagnosis training data
  training_data/instruction_pairs.jsonl  — SFT pairs (appended from live interactions + backfill)

Usage:
  python3 scripts/harvest_knowledge.py              # Full harvest
  python3 scripts/harvest_knowledge.py --backfill   # Also backfill from execution records
  python3 scripts/harvest_knowledge.py --stats       # Show training data statistics

All output files are gitignored via training_data/.
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).parent.parent
KNOWLEDGE_DIR = ROOT / "data" / "knowledge"
INCIDENTS_DIR = KNOWLEDGE_DIR / "incidents"
PATTERNS_DIR = KNOWLEDGE_DIR / "patterns"
ANTIPATTERNS_DIR = KNOWLEDGE_DIR / "antipatterns"
FEEDBACK_DIR = ROOT / "FEEDBACK"
EXECUTION_DIR = ROOT / "execution_records"
TRAINING_DIR = ROOT / "training_data"

DPO_FILE = TRAINING_DIR / "preference_pairs.jsonl"
ERROR_FIX_FILE = TRAINING_DIR / "error_fix_pairs.jsonl"
SFT_FILE = TRAINING_DIR / "instruction_pairs.jsonl"

# System prompt for all training data (compact)
SYSTEM_PROMPT = (
    "You are driving the Pacman Hedera trading CLI. "
    "Commands: swap <amt> <FROM> for <TO>, balance, send <amt> <TOKEN> to <ACCOUNT>, "
    "price <TOKEN>, associate <TOKEN>, account switch <ID>, robot status, history. "
    "Use token tickers (HBAR, USDC, WBTC, SAUCE, USDC[hts]). "
    "V2 is the only routing protocol. Never simulate. "
    "Safety limits: $100 max swap, $100 daily, 5% max slippage."
)


def harvest_incidents():
    """Convert incident reports to DPO preference pairs + error-fix pairs."""
    if not INCIDENTS_DIR.exists():
        return 0, 0

    dpo_count = 0
    ef_count = 0

    for f in sorted(INCIDENTS_DIR.glob("*.json")):
        try:
            inc = json.loads(f.read_text())
        except Exception:
            continue

        # --- DPO pair: wrong behavior vs correct resolution ---
        if inc.get("root_cause") and inc.get("resolution"):
            prompt = f"Incident: {inc.get('title', '')}\nContext: {inc.get('description', '')}"

            # The resolution is the "chosen" response
            chosen = inc["resolution"]

            # The root cause behavior is the "rejected" response
            rejected = inc["root_cause"]

            dpo_entry = {
                "prompt": prompt,
                "chosen": chosen,
                "rejected": rejected,
                "metadata": {
                    "source": f"incident/{inc.get('id', f.stem)}",
                    "category": inc.get("category", "unknown"),
                    "tags": inc.get("tags", []),
                    "ts": inc.get("date", "unknown"),
                }
            }
            _append_jsonl(DPO_FILE, dpo_entry)
            dpo_count += 1

        # --- Error-fix pair: diagnosis training ---
        if inc.get("agent_lesson"):
            ef_entry = {
                "error_description": inc.get("description", ""),
                "wrong_diagnosis": inc.get("root_cause", ""),
                "correct_diagnosis": inc.get("resolution", ""),
                "lesson": inc.get("agent_lesson", ""),
                "prevention": inc.get("prevention", ""),
                "metadata": {
                    "source": f"incident/{inc.get('id', f.stem)}",
                    "tags": inc.get("tags", []),
                }
            }
            _append_jsonl(ERROR_FIX_FILE, ef_entry)
            ef_count += 1

    return dpo_count, ef_count


def harvest_antipatterns():
    """Convert antipatterns to DPO preference pairs."""
    if not ANTIPATTERNS_DIR.exists():
        return 0

    count = 0
    for f in sorted(ANTIPATTERNS_DIR.glob("*.json")):
        try:
            ap = json.loads(f.read_text())
        except Exception:
            continue

        if ap.get("wrong_behavior") and ap.get("correct_behavior"):
            dpo_entry = {
                "prompt": f"Task: {ap.get('title', '')}\nContext: {ap.get('description', '')}",
                "chosen": ap["correct_behavior"],
                "rejected": ap["wrong_behavior"],
                "metadata": {
                    "source": f"antipattern/{ap.get('id', f.stem)}",
                    "category": ap.get("category", "unknown"),
                    "tags": ap.get("tags", []),
                }
            }
            _append_jsonl(DPO_FILE, dpo_entry)
            count += 1

    return count


def harvest_patterns():
    """Convert patterns to SFT instruction pairs (correct behavior examples)."""
    if not PATTERNS_DIR.exists():
        return 0

    count = 0
    for f in sorted(PATTERNS_DIR.glob("*.json")):
        try:
            pat = json.loads(f.read_text())
        except Exception:
            continue

        if pat.get("tree") or pat.get("description"):
            steps = "\n".join(pat.get("tree", []))
            sft_entry = {
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"How should I handle: {pat.get('title', '')}?"},
                    {"role": "assistant", "content": f"{pat.get('description', '')}\n\nDecision tree:\n{steps}"},
                ],
                "metadata": {
                    "source": f"pattern/{pat.get('id', f.stem)}",
                    "category": pat.get("category", "unknown"),
                    "tags": pat.get("tags", []),
                }
            }
            _append_jsonl(SFT_FILE, sft_entry)
            count += 1

    return count


def backfill_from_executions():
    """Convert historical execution_records/*.json into SFT training pairs.

    Each execution record becomes an instruction pair showing what a successful
    command looks like: input → output.
    """
    if not EXECUTION_DIR.exists():
        return 0

    count = 0
    for f in sorted(EXECUTION_DIR.glob("exec_*.json")):
        try:
            rec = json.loads(f.read_text())
        except Exception:
            continue

        if not rec.get("success"):
            continue  # Only train on successes for SFT

        route = rec.get("route", {})
        from_tok = route.get("from", "?")
        to_tok = route.get("to", "?")
        amount_in = rec.get("amount_token", 0)
        amount_out = rec.get("to_amount_token", 0)
        protocol = rec.get("protocol", "V2")
        mode = rec.get("mode", "LIVE")

        if mode == "SIMULATION":
            continue  # Don't train on simulations

        # Reconstruct the likely user command
        user_cmd = f"swap {amount_in} {from_tok} for {to_tok}"

        # Reconstruct what the app would have shown
        results = rec.get("results", [])
        tx_hash = results[0].get("tx_hash", "?") if results else "?"
        gas_hbar = rec.get("gas_cost_hbar", 0)
        amount_usd = rec.get("amount_usd", 0)

        assistant_output = (
            f"Swapped {amount_in:.6f} {from_tok} → {amount_out:.6f} {to_tok}\n"
            f"Tx: {tx_hash}\n"
            f"Gas: {gas_hbar:.4f} HBAR | Value: ${amount_usd:.2f} | Protocol: {protocol}"
        )

        sft_entry = {
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_cmd},
                {"role": "assistant", "content": assistant_output},
            ],
            "metadata": {
                "source": f"execution/{f.stem}",
                "ts": rec.get("timestamp", "unknown"),
                "mode": mode,
                "protocol": protocol,
                "success": True,
                "amount_usd": amount_usd,
            }
        }
        _append_jsonl(SFT_FILE, sft_entry)
        count += 1

    return count


def show_stats():
    """Show training data statistics."""
    print("\n📊 Training Data Statistics")
    print("=" * 50)
    for name, path in [
        ("SFT Instruction Pairs", SFT_FILE),
        ("DPO Preference Pairs", DPO_FILE),
        ("Error-Fix Pairs", ERROR_FIX_FILE),
        ("Live Executions", TRAINING_DIR / "live_executions.jsonl"),
        ("Agent Interactions", ROOT / "logs" / "agent_interactions.jsonl"),
    ]:
        if path.exists():
            lines = sum(1 for _ in open(path))
            size_kb = path.stat().st_size / 1024
            print(f"  {name:.<35} {lines:>5} entries  ({size_kb:.1f} KB)")
        else:
            print(f"  {name:.<35}     0 entries  (not created)")

    # Knowledge base stats
    print(f"\n📚 Knowledge Base")
    print("=" * 50)
    for name, path in [
        ("Incidents", INCIDENTS_DIR),
        ("Patterns", PATTERNS_DIR),
        ("Anti-patterns", ANTIPATTERNS_DIR),
    ]:
        if path.exists():
            count = len(list(path.glob("*.json")))
            print(f"  {name:.<35} {count:>5} files")
        else:
            print(f"  {name:.<35}     0 files")

    # Feedback logs
    if FEEDBACK_DIR.exists():
        count = len(list(FEEDBACK_DIR.glob("*.md")))
        print(f"  {'Feedback transcripts':.<35} {count:>5} files")
    print()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _append_jsonl(path: Path, entry: dict):
    """Append a single JSON entry to a JSONL file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(entry, default=str) + "\n")


def _dedupe_jsonl(path: Path):
    """Remove exact duplicate lines from a JSONL file."""
    if not path.exists():
        return
    lines = path.read_text().strip().split("\n")
    seen = set()
    unique = []
    for line in lines:
        if line not in seen:
            seen.add(line)
            unique.append(line)
    if len(unique) < len(lines):
        path.write_text("\n".join(unique) + "\n")
        print(f"  Deduped {path.name}: {len(lines)} → {len(unique)}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    TRAINING_DIR.mkdir(exist_ok=True)

    if "--stats" in sys.argv:
        show_stats()
        return

    print("🔄 Harvesting knowledge into training data...\n")

    # Harvest from knowledge base
    dpo, ef = harvest_incidents()
    print(f"  Incidents  → {dpo} DPO pairs, {ef} error-fix pairs")

    ap = harvest_antipatterns()
    print(f"  Antipatterns → {ap} DPO pairs")

    pat = harvest_patterns()
    print(f"  Patterns   → {pat} SFT instruction pairs")

    # Backfill from execution history
    if "--backfill" in sys.argv:
        bf = backfill_from_executions()
        print(f"  Executions → {bf} SFT instruction pairs (backfilled)")

    # Dedupe all output files
    print("\n🧹 Deduplicating...")
    for f in [DPO_FILE, ERROR_FIX_FILE, SFT_FILE]:
        _dedupe_jsonl(f)

    print()
    show_stats()


if __name__ == "__main__":
    main()
