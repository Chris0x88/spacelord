#!/usr/bin/env python3
"""
Pacman History - Execution Recording & Retrieval
=================================================

Records swap, V1 swap, staking, and transfer executions to JSON files.
Also appends to the JSONL training log for AI model fine-tuning.

Extracted from PacmanExecutor to keep the executor focused on swap execution.
"""

import json
import time
from pathlib import Path
from typing import List
from src.logger import logger

# Path for the AI training data JSONL log — one record per execution
TRAINING_FILE = Path(__file__).parent.parent / "training_data" / "live_executions.jsonl"


def record_execution(route, token_amount: float, results: list, simulate: bool,
                     eoa: str, network: str, recordings_dir: Path,
                     get_token_decimals_fn, get_hbar_price_fn):
    """Record execution details for AI training."""
    from lib.prices import price_manager

    # Determine Price
    if route.from_variant in ["HBAR", "0.0.0"]:
        usd_price = price_manager.get_hbar_price()
        decimals = 8
    else:
        decimals = get_token_decimals_fn(route.from_variant)

        token_id = route.from_variant  # Attempt to use as ID if it is one

        try:
            with open("data/tokens.json") as f:
                tdata = json.load(f)
                meta = tdata.get(route.from_variant)
                if meta:
                    token_id = meta.get("id", token_id)
        except:
            pass

        usd_price = price_manager.get_price(token_id)

    # Record both amounts for history
    actual_amount_token = token_amount
    if results and decimals > 0:
        raw_in = results[0].amount_in_raw
        if raw_in > 0:
            actual_amount_token = raw_in / (10 ** decimals)

    actual_to_amount_token = 0.0
    if results:
        to_decimals = get_token_decimals_fn(route.to_variant)
        raw_out = results[-1].amount_out_raw
        if raw_out > 0 and to_decimals > 0:
            actual_to_amount_token = raw_out / (10 ** to_decimals)

    actual_usd = actual_amount_token * usd_price if usd_price > 0 else 0
    total_gas = sum(r.gas_used for r in results)
    total_gas_hbar = sum(r.gas_cost_hbar for r in results)

    record = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "mode": "SIMULATION" if simulate else "LIVE",
        "route": {
            "from": route.from_variant,
            "to": route.to_variant,
            "steps": len(route.steps),
            "total_cost_hbar": route.total_cost_hbar,
            "hashpack_visible": route.hashpack_visible
        },
        "amount_token": actual_amount_token,
        "to_amount_token": actual_to_amount_token,
        "amount_usd": round(actual_usd, 2),
        "gas_used": total_gas,
        "gas_cost_hbar": total_gas_hbar,
        "results": [r.to_dict() for r in results],
        "success": all(r.success for r in results),
        "account": eoa,
        "network": network
    }

    filename = f"exec_{time.strftime('%Y%m%d_%H%M%S')}_{route.from_variant}_to_{route.to_variant}.json"
    filepath = recordings_dir / filename
    with open(filepath, 'w') as f:
        json.dump(record, f, indent=2)

    logger.info(f"\n📝 Execution recorded: {filepath}")

    # Also append to JSONL training log (used for AI model fine-tuning)
    try:
        TRAINING_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(TRAINING_FILE, 'a') as f:
            f.write(json.dumps(record) + "\n")
    except Exception as e:
        logger.debug(f"Training log write failed (non-fatal): {e}")


def record_v1_execution(from_sym: str, to_sym: str, amount_hbar: float,
                        res, simulate: bool, eoa: str, network: str,
                        recordings_dir: Path):
    """Record V1 execution to history (mirrors V2 format)."""
    # Convert to_amount_token from raw if it's HexBytes (should be int now, but safety first)
    raw_to = res.amount_out_raw
    if hasattr(raw_to, "hex"):
        try:
            raw_to = int(raw_to.hex(), 16)
        except:
            raw_to = 0

    # Get correct decimals for to_token
    to_decimals = 8
    try:
        with open("data/tokens.json") as f:
            tdata = json.load(f)
            # Try to find decimals by symbol or ID
            meta = tdata.get(to_sym)
            if meta:
                to_decimals = meta.get("decimals", 8)
            else:
                # Search by ID
                for m in tdata.values():
                    if m.get("id") == to_sym:
                        to_decimals = m.get("decimals", 8)
                        break
    except:
        pass

    record = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "mode": "SIMULATION" if simulate else "LIVE",
        "protocol": "V1",
        "route": {
            "from": from_sym,
            "to": to_sym,
            "protocol": "V1",
            "steps": 1,
            "total_cost_hbar": amount_hbar,
            "hashpack_visible": False
        },
        "amount_token": amount_hbar,
        "to_amount_token": raw_to / 10**to_decimals if isinstance(raw_to, (int, float)) and raw_to > 0 else 0,
        "amount_usd": round(amount_hbar * res.hbar_usd_price, 2) if res.hbar_usd_price > 0 else 0,
        "gas_used": res.gas_used,
        "gas_cost_hbar": res.gas_cost_hbar,
        "results": [res.to_dict()],
        "success": res.success,
        "account": eoa,
        "network": network
    }

    filename = f"exec_{time.strftime('%Y%m%d_%H%M%S')}_{from_sym}_to_{to_sym}_V1.json"
    filepath = recordings_dir / filename
    with open(filepath, 'w') as f:
        json.dump(record, f, indent=2)

    logger.info(f"   📝 V1 Execution recorded: {filepath}")


def record_staking_transaction(mode: str, node_id: int, tx_id: str, success: bool,
                               eoa: str, network: str, recordings_dir: Path,
                               error: str = None):
    """Record staking/unstaking operation to history."""
    record = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "mode": mode,  # "STAKE" or "UNSTAKE"
        "route": {
            "from": "HBAR",
            "to": f"Node {node_id}" if node_id != -1 else "Unstaked",
            "steps": []
        },
        "amount_token": 0,
        "to_amount_token": 0,
        "amount_usd": 0,
        "gas_used": 0,
        "gas_cost_hbar": 0,
        "success": success,
        "tx_id": tx_id,
        "error": error,
        "account": eoa,
        "network": network
    }

    filename = f"exec_{time.strftime('%Y%m%d_%H%M%S')}_{mode.lower()}.json"

    # Ensure dir exists
    recordings_dir.mkdir(parents=True, exist_ok=True)
    filepath = recordings_dir / filename

    with open(filepath, 'w') as f:
        json.dump(record, f, indent=2)


def record_transfer_execution(res: dict, eoa: str, network: str, recordings_dir: Path):
    """Record HBAR/HTS transfer to local history."""
    record = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "mode": "SIMULATION" if res.get("tx_hash", "").startswith("SIMULATED") else "LIVE",
        "type": "TRANSFER",
        "protocol": "NATIVE",
        "route": {
            "from": eoa,
            "to": res.get("recipient", "Unknown"),
            "protocol": "NATIVE",
            "steps": 1,
            "total_cost_hbar": res.get("amount", 0) if res.get("symbol") == "HBAR" else 0
        },
        "amount_token": res.get("amount", 0),
        "symbol": res.get("symbol"),
        "to_amount_token": res.get("amount", 0),
        "to_symbol": res.get("symbol"),
        "amount_usd": 0,
        "gas_used": res.get("gas_used", 0),
        "success": res.get("success", False),
        "memo": res.get("memo"),
        "tx_hash": res.get("tx_hash"),
        "account": eoa,
        "network": network
    }

    try:
        filename = f"exec_{time.strftime('%Y%m%d_%H%M%S')}_{res.get('symbol')}_transfer.json"
        record_path = recordings_dir / filename
        with open(record_path, "w") as f:
            json.dump(record, f, indent=4)
    except Exception as e:
        logger.debug(f"Transfer recording failed: {e}")


def get_execution_history(recordings_dir: Path, limit: int = 10) -> list:
    """Retrieve recent execution records."""
    if not recordings_dir.exists():
        return []
    files = sorted(recordings_dir.glob("exec_*.json"), reverse=True)
    history = []
    for f in files[:limit]:
        try:
            with open(f) as file:
                history.append(json.load(file))
        except:
            continue
    return history
