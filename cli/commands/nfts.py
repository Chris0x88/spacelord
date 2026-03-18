#!/usr/bin/env python3
"""
CLI Commands: NFT Viewing & Management
=======================================

Handles: listing NFTs, viewing metadata, downloading images.
Uses Hedera Mirror Node API for NFT data.
"""

import sys
import json as _json
import base64
import requests
from pathlib import Path
from cli.display import C
from src.logger import logger
from cli.commands.wallet import _safe_input, _is_auto_yes, _clean_args, _print_account_context


MIRROR_BASE = "https://mainnet-public.mirrornode.hedera.com"
MIRROR_TESTNET = "https://testnet.mirrornode.hedera.com"
IPFS_GATEWAYS = [
    "https://ipfs.io/ipfs/",
    "https://gateway.pinata.cloud/ipfs/",
    "https://cloudflare-ipfs.com/ipfs/",
]


def cmd_nfts(app, args):
    """
    View NFTs owned by the active account.
    Usage:
      nfts                          → list all NFTs
      nfts <token_id>               → list NFTs from specific collection
      nfts view <token_id> <serial> → view detailed metadata
      nfts download <token_id> <serial> → download NFT image
      nfts --json                   → structured JSON output
    """
    json_mode = "--json" in args
    clean = _clean_args(args)

    account_id = getattr(app, 'account_id', None) or app.executor.hedera_account_id
    network = getattr(app, 'network', 'mainnet')
    mirror = MIRROR_BASE if network == "mainnet" else MIRROR_TESTNET

    if not account_id or account_id == "Unknown":
        msg = "No active account. Run 'setup' first."
        if json_mode:
            print(_json.dumps({"error": msg}))
        else:
            print(f"  {C.ERR}✗{C.R} {msg}")
        return

    # Route subcommands
    if clean and clean[0].lower() == "download":
        _cmd_download(clean[1:], account_id, mirror, json_mode)
        return
    if clean and clean[0].lower() == "view":
        _cmd_view(clean[1:], account_id, mirror, json_mode)
        return

    # Filter by collection if token_id provided
    collection_filter = None
    if clean and clean[0].startswith("0.0."):
        collection_filter = clean[0]

    # Fetch NFTs from Mirror Node
    if not json_mode:
        _print_account_context(app)
        print(f"\n  {C.BOLD}NFT Collection{C.R}")
        print(f"  {C.CHROME}{'─' * 56}{C.R}")
        print(f"  {C.MUTED}Querying Mirror Node...{C.R}")

    nfts = _fetch_nfts(account_id, mirror, collection_filter)

    if nfts is None:
        msg = "Failed to fetch NFTs from Mirror Node"
        if json_mode:
            print(_json.dumps({"error": msg}))
        else:
            print(f"  {C.ERR}✗{C.R} {msg}")
        return

    if not nfts:
        if json_mode:
            print(_json.dumps({"account": account_id, "nfts": [], "count": 0}))
        else:
            print(f"  {C.MUTED}No NFTs found for this account.{C.R}")
        return

    if json_mode:
        # Structured JSON output
        result = {
            "account": account_id,
            "count": len(nfts),
            "nfts": []
        }
        for nft in nfts:
            entry = {
                "token_id": nft.get("token_id"),
                "serial_number": nft.get("serial_number"),
                "metadata": _decode_metadata_str(nft.get("metadata", "")),
            }
            result["nfts"].append(entry)
        print(_json.dumps(result, indent=2))
        return

    # Pretty display
    # Group by collection
    collections = {}
    for nft in nfts:
        tid = nft.get("token_id", "unknown")
        if tid not in collections:
            collections[tid] = []
        collections[tid].append(nft)

    print(f"  {C.OK}Found {len(nfts)} NFT(s) across {len(collections)} collection(s){C.R}\n")

    for tid, items in collections.items():
        # Try to get collection name
        col_name = _get_token_name(tid, mirror)
        label = f"{col_name} " if col_name else ""
        print(f"  {C.BOLD}{label}{C.ACCENT}({tid}){C.R}  —  {len(items)} item(s)")

        for nft in items[:10]:  # Show max 10 per collection
            serial = nft.get("serial_number", "?")
            meta_raw = nft.get("metadata", "")
            meta_str = _decode_metadata_str(meta_raw)

            # Try to parse metadata URI
            name = ""
            if meta_str:
                meta_obj = _fetch_metadata_json(meta_str)
                if meta_obj:
                    name = meta_obj.get("name", "")

            name_label = f"  {C.TEXT}{name}{C.R}" if name else ""
            print(f"    #{serial}{name_label}")

        if len(items) > 10:
            print(f"    {C.MUTED}... and {len(items) - 10} more{C.R}")
        print()

    print(f"  {C.MUTED}View details: {C.ACCENT}nfts view <token_id> <serial>{C.R}")
    print(f"  {C.MUTED}Download:     {C.ACCENT}nfts download <token_id> <serial>{C.R}")
    print()


def _cmd_view(args, account_id, mirror, json_mode):
    """View detailed metadata for a specific NFT."""
    if len(args) < 2:
        msg = "Usage: nfts view <token_id> <serial_number>"
        if json_mode:
            print(_json.dumps({"error": msg}))
        else:
            print(f"  {C.ERR}✗{C.R} {msg}")
        return

    token_id = args[0]
    try:
        serial = int(args[1])
    except ValueError:
        msg = f"Invalid serial number: {args[1]}"
        if json_mode:
            print(_json.dumps({"error": msg}))
        else:
            print(f"  {C.ERR}✗{C.R} {msg}")
        return

    nft_data = _fetch_single_nft(token_id, serial, mirror)
    if not nft_data:
        msg = f"NFT not found: {token_id} #{serial}"
        if json_mode:
            print(_json.dumps({"error": msg}))
        else:
            print(f"  {C.ERR}✗{C.R} {msg}")
        return

    meta_raw = nft_data.get("metadata", "")
    meta_str = _decode_metadata_str(meta_raw)
    meta_obj = _fetch_metadata_json(meta_str) if meta_str else None

    if json_mode:
        result = {
            "token_id": token_id,
            "serial_number": serial,
            "account_id": nft_data.get("account_id"),
            "metadata_uri": meta_str,
            "metadata": meta_obj,
        }
        print(_json.dumps(result, indent=2))
        return

    # Pretty display
    col_name = _get_token_name(token_id, mirror)
    print(f"\n  {C.BOLD}NFT Details{C.R}")
    print(f"  {C.CHROME}{'─' * 56}{C.R}")
    if col_name:
        print(f"  {C.BOLD}Collection:{C.R}  {col_name}")
    print(f"  {C.BOLD}Token ID:{C.R}    {token_id}")
    print(f"  {C.BOLD}Serial:{C.R}      #{serial}")
    print(f"  {C.BOLD}Owner:{C.R}       {nft_data.get('account_id', 'unknown')}")

    if meta_str:
        print(f"  {C.BOLD}Metadata:{C.R}    {meta_str[:80]}{'...' if len(meta_str) > 80 else ''}")

    if meta_obj:
        if meta_obj.get("name"):
            print(f"  {C.BOLD}Name:{C.R}        {meta_obj['name']}")
        if meta_obj.get("description"):
            desc = meta_obj['description'][:100]
            print(f"  {C.BOLD}Description:{C.R} {desc}{'...' if len(meta_obj['description']) > 100 else ''}")
        if meta_obj.get("image"):
            print(f"  {C.BOLD}Image:{C.R}       {meta_obj['image']}")
        attrs = meta_obj.get("attributes") or meta_obj.get("properties")
        if attrs and isinstance(attrs, list):
            print(f"\n  {C.BOLD}Attributes:{C.R}")
            for attr in attrs[:10]:
                if isinstance(attr, dict):
                    trait = attr.get("trait_type", attr.get("name", "?"))
                    val = attr.get("value", "?")
                    print(f"    {C.MUTED}{trait}:{C.R} {val}")

    print(f"\n  {C.MUTED}Download image: {C.ACCENT}nfts download {token_id} {serial}{C.R}")
    print()


def _cmd_download(args, account_id, mirror, json_mode):
    """Download NFT image to local file."""
    if len(args) < 2:
        msg = "Usage: nfts download <token_id> <serial_number>"
        if json_mode:
            print(_json.dumps({"error": msg}))
        else:
            print(f"  {C.ERR}✗{C.R} {msg}")
        return

    token_id = args[0]
    try:
        serial = int(args[1])
    except ValueError:
        msg = f"Invalid serial number: {args[1]}"
        if json_mode:
            print(_json.dumps({"error": msg}))
        else:
            print(f"  {C.ERR}✗{C.R} {msg}")
        return

    nft_data = _fetch_single_nft(token_id, serial, mirror)
    if not nft_data:
        msg = f"NFT not found: {token_id} #{serial}"
        if json_mode:
            print(_json.dumps({"error": msg}))
        else:
            print(f"  {C.ERR}✗{C.R} {msg}")
        return

    meta_str = _decode_metadata_str(nft_data.get("metadata", ""))
    meta_obj = _fetch_metadata_json(meta_str) if meta_str else None

    if not meta_obj or not meta_obj.get("image"):
        msg = "No image URL found in NFT metadata"
        if json_mode:
            print(_json.dumps({"error": msg, "metadata_uri": meta_str}))
        else:
            print(f"  {C.ERR}✗{C.R} {msg}")
        return

    image_url = meta_obj["image"]
    # Resolve IPFS URLs
    image_url = _resolve_ipfs(image_url)

    if not json_mode:
        print(f"  {C.MUTED}Downloading from: {image_url[:60]}...{C.R}")

    # Download
    try:
        resp = requests.get(image_url, timeout=30, stream=True)
        resp.raise_for_status()

        # Determine extension from content-type
        ct = resp.headers.get("Content-Type", "")
        ext = ".png"
        if "jpeg" in ct or "jpg" in ct:
            ext = ".jpg"
        elif "gif" in ct:
            ext = ".gif"
        elif "svg" in ct:
            ext = ".svg"
        elif "webp" in ct:
            ext = ".webp"

        # Save
        out_dir = Path("data/nft_images")
        out_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{token_id.replace('.', '_')}_{serial}{ext}"
        out_path = out_dir / filename

        with open(out_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)

        if json_mode:
            print(_json.dumps({
                "success": True,
                "token_id": token_id,
                "serial_number": serial,
                "file": str(out_path),
                "size_bytes": out_path.stat().st_size,
                "name": meta_obj.get("name", ""),
            }))
        else:
            size_kb = out_path.stat().st_size / 1024
            name = meta_obj.get("name", "")
            label = f" ({name})" if name else ""
            print(f"  {C.OK}✅ Downloaded{label}{C.R}")
            print(f"  {C.MUTED}File: {out_path} ({size_kb:.1f} KB){C.R}")

    except Exception as e:
        msg = f"Download failed: {e}"
        if json_mode:
            print(_json.dumps({"error": msg}))
        else:
            print(f"  {C.ERR}✗{C.R} {msg}")


# ---------------------------------------------------------------------------
# Mirror Node Helpers
# ---------------------------------------------------------------------------

def _fetch_nfts(account_id, mirror, collection_filter=None):
    """Fetch all NFTs for an account from Mirror Node."""
    try:
        url = f"{mirror}/api/v1/accounts/{account_id}/nfts"
        params = {"limit": 100}
        if collection_filter:
            params["token.id"] = collection_filter

        all_nfts = []
        while url:
            resp = requests.get(url, params=params, timeout=10)
            if resp.status_code != 200:
                logger.warning(f"Mirror Node NFT query failed: {resp.status_code}")
                return None
            data = resp.json()
            all_nfts.extend(data.get("nfts", []))
            # Handle pagination
            links = data.get("links", {})
            next_link = links.get("next")
            if next_link:
                url = f"{mirror}{next_link}"
                params = {}  # Next link includes params
            else:
                url = None
        return all_nfts
    except Exception as e:
        logger.error(f"NFT fetch error: {e}")
        return None


def _fetch_single_nft(token_id, serial, mirror):
    """Fetch a specific NFT by token ID and serial."""
    try:
        url = f"{mirror}/api/v1/tokens/{token_id}/nfts/{serial}"
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return None
        return resp.json()
    except Exception:
        return None


def _get_token_name(token_id, mirror):
    """Get token name/symbol from Mirror Node."""
    try:
        url = f"{mirror}/api/v1/tokens/{token_id}"
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            return data.get("name", "") or data.get("symbol", "")
    except Exception:
        pass
    return ""


def _decode_metadata_str(metadata_b64):
    """Decode base64 metadata to string (usually a URI)."""
    if not metadata_b64:
        return ""
    try:
        return base64.b64decode(metadata_b64).decode("utf-8", errors="replace").strip()
    except Exception:
        return metadata_b64


def _fetch_metadata_json(uri):
    """Fetch and parse JSON metadata from a URI (HTTP or IPFS)."""
    if not uri:
        return None
    url = _resolve_ipfs(uri)
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return None


def _resolve_ipfs(url):
    """Convert ipfs:// URLs to HTTP gateway URLs."""
    if url.startswith("ipfs://"):
        cid = url[7:]
        return IPFS_GATEWAYS[0] + cid
    return url
