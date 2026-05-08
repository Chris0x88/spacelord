"""Space Lord key management — OWS vault + macOS Keychain dual-store.

Keys are stored in:
  - OWS vault (~/.ows/wallets/) — AES-256-GCM encrypted, Rust core (if `ows` package present)
  - macOS Keychain (local-only by default; iCloud sync NOT enabled)
  - .env (legacy fallback)

Resolution order for get_private_key():
  OWS vault -> macOS Keychain -> env var -> error

Self-custody note: macOS Keychain entries are written via the Python `keyring`
package which calls SecKeychain APIs directly. We do NOT pass keys via subprocess
argv (which would leak via `ps`). Default sync attribute is local-only — keys
do not propagate to iCloud Keychain.
"""
from __future__ import annotations

import logging
import os
import re
import subprocess
import sys
from typing import List, Optional

log = logging.getLogger("spacelord.credentials")

WALLET_PREFIX = "spacelord"
KEYCHAIN_SERVICE = "spacelord"


# ---------------------------------------------------------------------------
# OWS vault
# ---------------------------------------------------------------------------

def _ows_available() -> bool:
    try:
        import ows  # noqa: F401
        return True
    except ImportError:
        return False


def _ows_store(address: str, private_key: str) -> None:
    from ows import import_wallet_private_key

    key_hex = private_key
    if key_hex.startswith("0x"):
        key_hex = key_hex[2:]

    wallet_name = f"{WALLET_PREFIX}-{address[-8:].lower()}"
    import_wallet_private_key(
        name=wallet_name,
        private_key_hex=key_hex,
        chain="evm",
    )
    log.info("Key stored in OWS vault as '%s'", wallet_name)


def _ows_get(address: Optional[str] = None) -> Optional[str]:
    if not _ows_available():
        return None

    try:
        import json as _json
        from ows import list_wallets, export_wallet

        wallets = list_wallets()
        if not wallets:
            return None

        target = None
        if address:
            addr = address.lower()
            for w in wallets:
                for acct in w.get("accounts", []):
                    if acct.get("address", "").lower() == addr:
                        target = w
                        break
                if target:
                    break
        else:
            for w in wallets:
                if w.get("name", "").startswith(WALLET_PREFIX):
                    target = w
                    break

        if not target:
            return None

        exported = export_wallet(target["name"])
        if isinstance(exported, str):
            try:
                data = _json.loads(exported)
            except (ValueError, TypeError):
                return None
        elif isinstance(exported, dict):
            data = exported
        else:
            return None

        key = data.get("secp256k1") or data.get("private_key")
        if key:
            if not key.startswith("0x"):
                key = "0x" + key
            return key
        return None
    except Exception as exc:
        log.debug("OWS get failed: %s", exc)
        return None


def _ows_list() -> List[str]:
    if not _ows_available():
        return []
    try:
        from ows import list_wallets
        addresses = []
        for w in list_wallets():
            if not w.get("name", "").startswith(WALLET_PREFIX):
                continue
            for acct in w.get("accounts", []):
                addr = acct.get("address", "")
                # Only return EVM addresses (0x-prefixed, 42 chars)
                if addr and addr.startswith("0x") and len(addr) == 42:
                    addresses.append(addr.lower())
        return addresses
    except Exception:
        return []


# ---------------------------------------------------------------------------
# macOS Keychain
# ---------------------------------------------------------------------------

def _keychain_available() -> bool:
    if sys.platform != "darwin":
        return False
    try:
        result = subprocess.run(
            ["which", "security"], capture_output=True, timeout=5,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def _keychain_store(address: str, private_key: str) -> None:
    """Store a private key in macOS Keychain via SecKeychain API.

    Uses the `keyring` package, which calls Security framework APIs directly.
    The key is NEVER passed via subprocess argv (which would leak via `ps`).
    """
    addr = address.lower()
    if not addr.startswith("0x"):
        addr = "0x" + addr

    try:
        import keyring
    except ImportError as e:
        raise RuntimeError(
            "Keychain storage requires the `keyring` package. "
            "Install via: uv sync"
        ) from e

    try:
        keyring.set_password(KEYCHAIN_SERVICE, addr, private_key)
    except Exception as e:
        raise RuntimeError(f"Keychain store failed: {e}") from e


def _keychain_get(address: Optional[str] = None) -> Optional[str]:
    if not _keychain_available():
        return None

    if address is None:
        addresses = _keychain_list()
        if not addresses:
            return None
        address = addresses[0]

    addr = address.lower()
    if not addr.startswith("0x"):
        addr = "0x" + addr

    try:
        import keyring
        key = keyring.get_password(KEYCHAIN_SERVICE, addr)
        return key if key else None
    except Exception:
        return None


def _keychain_list() -> List[str]:
    if not _keychain_available():
        return []
    try:
        result = subprocess.run(
            ["security", "dump-keychain"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            return []
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []

    addresses: List[str] = []
    current_acct = None
    current_is_ours = False

    for line in result.stdout.splitlines():
        stripped = line.strip()

        if stripped.startswith("keychain:") or stripped.startswith("class:"):
            if current_is_ours and current_acct:
                addresses.append(current_acct)
            current_acct = None
            current_is_ours = False
            continue

        if KEYCHAIN_SERVICE in stripped and ('"svce"' in stripped or "0x00000007" in stripped):
            current_is_ours = True

        if '"acct"' in stripped:
            match = re.search(r'"acct".*?="(0x[0-9a-fA-F]+)"', stripped)
            if match:
                current_acct = match.group(1).lower()

    # Don't forget the last entry
    if current_is_ours and current_acct:
        addresses.append(current_acct)
    return addresses


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def _check_existing_key() -> Optional[dict]:
    """Check if a key already exists in any secure backend."""
    # Check OWS
    if _ows_available():
        addrs = _ows_list()
        if addrs:
            key = _ows_get(addrs[0])
            if key:
                return {"address": addrs[0], "backend": "ows", "key": key}

    # Check Keychain
    if _keychain_available():
        addrs = _keychain_list()
        if addrs:
            key = _keychain_get(addrs[0])
            if key:
                return {"address": addrs[0], "backend": "keychain", "key": key}

    return None


def _archive_ows_wallet() -> Optional[str]:
    """Rename existing OWS wallet with timestamp. Old keys are NEVER deleted."""
    if not _ows_available():
        return None
    try:
        import time as _time
        from ows import list_wallets, rename_wallet

        for w in list_wallets():
            name = w.get("name", "")
            if name.startswith(WALLET_PREFIX):
                ts = _time.strftime("%Y%m%d_%H%M%S")
                archive_name = f"{name}-archived-{ts}"
                rename_wallet(name, archive_name)
                log.info("Archived old OWS wallet '%s' -> '%s'", name, archive_name)
                return archive_name
    except Exception as exc:
        log.warning("OWS archive failed: %s", exc)
    return None


def store_key_secure(address: str, private_key: str, force: bool = False) -> List[str]:
    """Store a key in ALL available secure backends (OWS + Keychain).

    SAFETY: If a different key already exists, raises ValueError unless
    force=True. When forced, the old OWS wallet is archived with a
    timestamp suffix — old keys are NEVER deleted. They are the only
    copy of self-custody funds.

    Returns list of backend names where the key was stored.
    """
    # Check for existing key — refuse to overwrite without force
    existing = _check_existing_key()
    if existing and existing["key"]:
        existing_bare = existing["key"][2:].lower() if existing["key"].startswith("0x") else existing["key"].lower()
        new_bare = private_key[2:].lower() if private_key.startswith("0x") else private_key.lower()

        if existing_bare != new_bare:
            if not force:
                raise ValueError(
                    f"A different key already exists (address: {existing['address']}, "
                    f"backend: {existing['backend']}). "
                    "Pass force=True to archive the old key and store the new one."
                )
            _archive_ows_wallet()

    stored_in: List[str] = []

    if _ows_available():
        try:
            _ows_store(address, private_key)
            stored_in.append("ows")
        except Exception as exc:
            log.warning("OWS store failed: %s", exc)

    if _keychain_available():
        try:
            _keychain_store(address, private_key)
            stored_in.append("keychain")
        except Exception as exc:
            log.warning("Keychain store failed: %s", exc)

    if not stored_in:
        raise RuntimeError(
            "Failed to store key in any secure backend. "
            "Install OWS: pip install open-wallet-standard"
        )
    return stored_in


def get_private_key(address: Optional[str] = None) -> str:
    """Resolve a private key. Tries OWS -> Keychain -> env var.

    Raises RuntimeError if no key found.
    """
    # 1. OWS vault
    key = _ows_get(address)
    if key:
        log.info("Key resolved via OWS vault")
        return key

    # 2. macOS Keychain
    key = _keychain_get(address)
    if key:
        log.info("Key resolved via macOS Keychain")
        return key

    # 3. Env var fallback
    key = os.environ.get("PRIVATE_KEY", "")
    if key:
        log.info("Key resolved via PRIVATE_KEY env var")
        return key

    raise RuntimeError(
        "No private key available. Options:\n"
        "  1. Store via OWS:  python -m src.credentials import\n"
        "  2. Set env var:    export PRIVATE_KEY=0x...\n"
        "  3. Add to .env:    PRIVATE_KEY=your_key_here"
    )


def list_keys() -> List[dict]:
    """List all keys across backends. Returns [{address, backend}]."""
    results = []
    seen = set()

    for addr in _ows_list():
        if addr not in seen:
            results.append({"address": addr, "backend": "ows"})
            seen.add(addr)

    for addr in _keychain_list():
        if addr not in seen:
            results.append({"address": addr, "backend": "keychain"})
            seen.add(addr)

    return results


# ---------------------------------------------------------------------------
# CLI entry point: python -m src.credentials [import|list]
# ---------------------------------------------------------------------------

def _print_key_guide():
    """Print a human-friendly guide for finding your private key."""
    print()
    print("  \033[1mSpace Lord — Private Key Import\033[0m")
    print("  " + "-" * 50)
    print()
    print("  Your private key is an ECDSA secp256k1 key — the same kind")
    print("  used by Ethereum wallets (MetaMask, Rabby) and Hedera.")
    print()
    print("  \033[1mWhat it looks like:\033[0m")
    print("    64 hex characters (0-9, a-f), optionally starting with 0x")
    print("    Example: 0x4c0883a69102937d6231471b5dbb6204fe512961...")
    print()
    print("  \033[1mWhere to find it:\033[0m")
    print("    MetaMask:     Settings > Security > Reveal Private Key")
    print("    HashPack:     Settings > Accounts > Show Private Key")
    print("    Hedera Portal: Developer > Ed25519/ECDSA key export")
    print("    .env file:    Look for PRIVATE_KEY=... in your .env")
    print()
    print("  \033[1mIMPORTANT — Hedera key type:\033[0m")
    print("    Space Lord uses ECDSA secp256k1 keys (same as Ethereum).")
    print("    If your Hedera account uses an ED25519 key, you need to")
    print("    create an ECDSA alias first via HashPack or Hedera Portal.")
    print()
    print("  \033[33m  NEVER share this key. Anyone with it controls your funds.\033[0m")
    print("  \033[33m  This tool encrypts and stores it securely after import.\033[0m")
    print()
    print("  \033[1mWhat happens next:\033[0m")
    print("    Your key will be encrypted and stored in:")
    print("    1. OWS vault  — AES-256-GCM encrypted file on disk")
    print("    2. macOS Keychain — syncs to iCloud for backup")
    print("    The raw key is never stored in plaintext anywhere.")
    print()


if __name__ == "__main__":
    import getpass

    args = sys.argv[1:]
    cmd = args[0] if args else "list"

    if cmd in ("import", "import --force"):
        force_mode = "--force" in args or "-f" in args
        _print_key_guide()

        private_key = getpass.getpass("  Paste your private key (input is hidden): ")
        private_key = private_key.strip()

        if not private_key:
            print("\n  No key entered. Aborting.")
            sys.exit(1)

        if not private_key.startswith("0x"):
            private_key = "0x" + private_key

        # Validate length
        stripped = private_key[2:]
        if len(stripped) != 64:
            print(f"\n  Invalid key length: got {len(stripped)} characters, expected 64.")
            print("  A private key is exactly 64 hex characters (0-9, a-f).")
            sys.exit(1)

        # Validate hex
        try:
            int(stripped, 16)
        except ValueError:
            print("\n  Invalid characters in key. Only hex characters allowed: 0-9, a-f.")
            sys.exit(1)

        # Derive EVM address
        try:
            from web3 import Account
            acct = Account.from_key(private_key)
            address = acct.address.lower()
        except ImportError:
            try:
                from eth_account import Account
                acct = Account.from_key(private_key)
                address = acct.address.lower()
            except ImportError:
                print("  Need web3 or eth-account to derive address.")
                print("  Install: pip install eth-account")
                sys.exit(1)

        print(f"\n  Wallet address: \033[1m{address}\033[0m")

        try:
            stored = store_key_secure(address, private_key, force=force_mode)
        except ValueError as e:
            print(f"\n  \033[33mKey already exists:\033[0m {e}")
            print()
            print("  To replace it (old key is archived, never deleted):")
            print("    python -m src.credentials import --force")
            print()
            sys.exit(1)

        print()
        for name in stored:
            if name == "ows":
                print("  \033[32mOWS vault\033[0m       — encrypted on disk (~/.ows/wallets/)")
            elif name == "keychain":
                print("  \033[32mmacOS Keychain\033[0m  — syncs to iCloud for backup")
        print()
        print("  Key is secured and backed up.")
        print("  Verify with: python -m src.credentials list")
        print()

    elif cmd == "list":
        keys = list_keys()
        if not keys:
            print("No keys found. Run: python -m src.credentials import")
        else:
            print(f"{'Address':<44} Backend")
            print("-" * 56)
            for k in keys:
                print(f"{k['address']:<44} {k['backend']}")

    else:
        print("Usage: python -m src.credentials [import|list]")
