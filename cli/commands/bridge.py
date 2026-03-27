"""
Bridge USDT0 to another chain via LayerZero.

Usage:
    bridge <amount> USDT0 <chain> --to <address>
    bridge status <tx_hash>
    bridge whitelist add <chain> <address> <label>
    bridge whitelist list
"""
import json
import logging
import re
from pathlib import Path

from cli.commands.wallet import _safe_input, _clean_args, _print_account_context
from cli.display import C

logger = logging.getLogger("spacelord.cli.bridge")


def cmd_bridge(app, args):
    """Handle bridge commands."""
    clean = _clean_args(args)
    json_mode = "--json" in args

    if not clean:
        _print_help()
        return

    subcmd = clean[0].lower()

    if subcmd == "status":
        _handle_status(app, clean[1:], json_mode)
    elif subcmd == "whitelist":
        _handle_whitelist(clean[1:], json_mode)
    else:
        _handle_bridge(app, clean, args, json_mode)


def _handle_bridge(app, clean, raw_args, json_mode):
    """Bridge USDT0: bridge <amount> USDT0 <chain> --to <address>"""
    from lib.bridge_usdt0 import USDT0Bridge

    _print_account_context(app)

    if len(clean) < 3:
        print(f"  {C.ERR}Usage: bridge <amount> USDT0 <chain> --to <address>{C.R}")
        return

    try:
        amount = float(clean[0])
    except ValueError:
        print(f"  {C.ERR}Invalid amount: {clean[0]}{C.R}")
        return

    token = clean[1].upper()
    if token != "USDT0":
        print(f"  {C.ERR}Only USDT0 bridging is supported. Got: {token}{C.R}")
        return

    dest_chain = clean[2].lower()

    recipient = None
    for i, a in enumerate(raw_args):
        if a == "--to" and i + 1 < len(raw_args):
            recipient = raw_args[i + 1]
            break

    if not recipient:
        print(f"  {C.ERR}Missing --to <address>. Destination address required.{C.R}")
        return

    bridge = USDT0Bridge(app.executor)

    quote = bridge.quote(amount, dest_chain)
    if not quote["success"]:
        print(f"  {C.ERR}Quote failed: {quote['error']}{C.R}")
        return

    print(f"\n  Bridge {amount:.2f} USDT0 -> {dest_chain.title()}")
    print(f"  Estimated received: {quote['estimated_received']:.2f} USDT0")
    print(f"  LayerZero fee: ~{quote['native_fee_hbar']:.4f} HBAR")
    print(f"  Destination: {recipient}")
    print(f"  Estimated arrival: 30s-3min\n")

    confirm = _safe_input("  Confirm bridge? (y/n): ", raw_args, default="y")
    if confirm.lower() not in ("y", "yes"):
        print(f"  {C.WARN}Cancelled.{C.R}")
        return

    result = bridge.bridge(amount, dest_chain, recipient)

    if json_mode:
        print(json.dumps(result, indent=2))
        return

    if result["success"]:
        print(f"\n  {C.OK}✓ Bridged {result['amount_sent']:.2f} USDT0 -> {result['dest_chain']}{C.R}")
        print(f"  TX: {result['tx_hash']}")
        print(f"  Fee: {result['native_fee_hbar']:.4f} HBAR")
        print(f"  Check status: bridge status {result['tx_hash']}")
    else:
        print(f"\n  {C.ERR}✗ Bridge failed: {result['error']}{C.R}")

    _log_bridge(result, amount, dest_chain, recipient, app)


def _handle_status(app, args, json_mode):
    """Check bridge delivery status."""
    from lib.bridge_usdt0 import USDT0Bridge

    if not args:
        print(f"  {C.ERR}Usage: bridge status <tx_hash>{C.R}")
        return

    tx_hash = args[0]
    bridge = USDT0Bridge(app.executor)
    status = bridge.check_status(tx_hash)

    if json_mode:
        print(json.dumps(status, indent=2))
        return

    s = status.get("status", "unknown")
    color = C.OK if s == "delivered" else C.WARN if s in ("pending", "inflight") else C.ERR
    print(f"\n  LayerZero Status: {color}{s}{C.R}")
    if status.get("dst_tx_hash"):
        print(f"  Destination TX: {status['dst_tx_hash']}")
    if s == "pending":
        print(f"  Estimated: 30s-3min. Check: https://scan.layerzero.network/tx/{tx_hash}")


def _handle_whitelist(args, json_mode):
    """Manage bridge whitelist."""
    settings_path = Path(__file__).parent.parent.parent / "data" / "settings.json"

    if not args:
        args = ["list"]

    subcmd = args[0].lower()

    if subcmd == "list":
        with open(settings_path) as f:
            settings = json.load(f)
        whitelist = settings.get("bridge_whitelist", [])
        if not whitelist:
            print(f"  {C.WARN}No bridge whitelist entries.{C.R}")
            print(f"  Add one: bridge whitelist add <chain> <address> <label>")
            return
        for entry in whitelist:
            print(f"  {entry['chain']}: {entry['address']} ({entry.get('label', '')})")

    elif subcmd == "add" and len(args) >= 4:
        chain = args[1].lower()
        address = args[2]
        label = " ".join(args[3:])

        if address.startswith("0.0."):
            print(f"  {C.ERR}Bridge destinations must be EVM addresses (0x...), not Hedera IDs{C.R}")
            return
        if not re.match(r"^0x[0-9a-fA-F]{40}$", address):
            print(f"  {C.ERR}Invalid EVM address: {address}{C.R}")
            return

        with open(settings_path) as f:
            settings = json.load(f)

        whitelist = settings.setdefault("bridge_whitelist", [])
        existing = [e for e in whitelist if e.get("address", "").lower() == address.lower() and e.get("chain") == chain]
        if existing:
            print(f"  {C.WARN}Already whitelisted.{C.R}")
            return

        whitelist.append({"chain": chain, "address": address, "label": label})
        with open(settings_path, "w") as f:
            json.dump(settings, f, indent=2)
        print(f"  {C.OK}✓ Added {address} ({label}) for {chain}{C.R}")

    else:
        print(f"  {C.ERR}Usage: bridge whitelist add <chain> <address> <label>{C.R}")


def _log_bridge(result, amount, dest_chain, recipient, app):
    """Log bridge operation to training data."""
    log_path = Path(__file__).parent.parent.parent / "training_data" / "live_executions.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    import datetime
    entry = {
        "type": "bridge",
        "protocol": "layerzero_usdt0",
        "amount": amount,
        "source_chain": "hedera",
        "dest_chain": dest_chain,
        "recipient": recipient,
        "tx_hash": result.get("tx_hash", ""),
        "lz_message_guid": result.get("lz_message_guid", ""),
        "native_fee_hbar": result.get("native_fee_hbar", 0),
        "success": result.get("success", False),
        "error": result.get("error", ""),
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "account": getattr(app.executor, "hedera_account_id", ""),
    }
    with open(log_path, "a") as f:
        f.write(json.dumps(entry) + "\n")


def _print_help():
    print("""
  Bridge USDT0 across chains via LayerZero

  Usage:
    bridge <amount> USDT0 <chain> --to <address>
    bridge status <tx_hash>
    bridge whitelist list
    bridge whitelist add <chain> <address> <label>

  Supported chains: arbitrum
  Destinations must be whitelisted first.

  Example:
    bridge whitelist add arbitrum 0xYour...Addr My Arb Wallet
    bridge 50 USDT0 arbitrum --to 0xYour...Addr
    bridge status 0xabc123...
""")
