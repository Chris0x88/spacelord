#!/usr/bin/env python3
"""
Pacman Agent - Structured Swap Router for SaucerSwap V2
=======================================================

THE core product. No natural language. No guessing.
Takes structured inputs, picks the best route, calls tools, returns results.

Usage:
    agent = PacmanAgent()

    # Quote only (no execution)
    quote = agent.quote("USDC", "WBTC_HTS", 1.0)

    # Execute swap
    result = agent.swap("USDC", "WBTC_HTS", 1.0, mode="exact_in")

    # List available tokens
    tokens = agent.tokens()

    # Get route without quoting
    route = agent.route("USDC", "WBTC_HTS")
"""

import json
import logging
import os
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional, Dict, List

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("pacman_agent")

ROUTES_FILE = Path(__file__).parent / "routes.json"

# ---------------------------------------------------------------------------
# Data classes - the agent's API types
# ---------------------------------------------------------------------------

@dataclass
class Route:
    """A pre-computed route between two tokens."""
    src: str
    dst: str
    path: list          # ["USDC", "USDC_HTS", "WBTC_HTS"]
    hops: list          # detailed hop info from routes.json
    total_fee_percent: float
    num_hops: int

@dataclass
class Quote:
    """A priced route ready for execution."""
    route: Route
    amount_in: float
    amount_out: float       # estimated output
    min_amount_out: float   # after slippage
    mode: str               # "exact_in" or "exact_out"
    slippage_percent: float
    price_per_unit: float   # price of 1 unit of dst in src terms

@dataclass
class SwapResult:
    """Result of an executed swap."""
    success: bool
    tx_hash: str = ""
    amount_in: float = 0.0
    amount_out: float = 0.0
    gas_used: int = 0
    error: str = ""
    route_used: str = ""    # "USDC -> HBAR -> WBTC_HTS"

# ---------------------------------------------------------------------------
# Live Price Registry
# ---------------------------------------------------------------------------

class PriceRegistry:
    """Fetches and caches live USD prices for tokens."""
    def __init__(self, cache_ttl=120):
        self.url = "https://api.saucerswap.finance/v1/tokens"
        self._prices = {}
        self._last_fetch = 0
        self.cache_ttl = cache_ttl

    def get_price(self, token_id: str) -> Optional[float]:
        """Get live USD price for a token ID."""
        now = time.time()
        if now - self._last_fetch > self.cache_ttl:
            self._fetch()
        
        return self._prices.get(token_id)

    def _fetch(self):
        try:
            import requests
            resp = requests.get(self.url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            for t in data:
                if t.get("priceUsd"):
                    self._prices[t["id"]] = float(t["priceUsd"])
            self._last_fetch = time.time()
            logger.info(f"Refreshed {len(self._prices)} live prices")
        except Exception as e:
            logger.debug(f"Failed to fetch live prices: {e}")

# ---------------------------------------------------------------------------
# The Agent
# ---------------------------------------------------------------------------

class PacmanAgent:
    """
    Structured swap agent for SaucerSwap V2 on Hedera.
    
    Uses a 'Static Matrix' of routes and performs 'Live Selection' 
    by quoting candidates in real-time.
    """

    def __init__(self, routes_file: str = None, max_slippage: float = 0.01):
        self._routes_data = None
        self._tokens = None
        self._routes = None
        self._engine = None
        self.prices = PriceRegistry()
        self.max_slippage = max_slippage  # 1% default

        routes_path = Path(routes_file) if routes_file else ROUTES_FILE
        if not routes_path.exists():
            raise FileNotFoundError(
                f"Route table not found at {routes_path}. Run: python3 build_routes.py"
            )
        with open(routes_path) as f:
            self._routes_data = json.load(f)
        self._tokens = self._routes_data["tokens"]
        self._routes = self._routes_data["routes"]
        logger.info(f"Loaded {len(self._routes)} route candidates across {len(self._tokens)} tokens")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def tokens(self) -> Dict[str, dict]:
        """Return all tradeable tokens and their metadata."""
        return dict(self._tokens)

    def candidates(self, from_token: str, to_token: str) -> List[Route]:
        """
        Return all candidate routes from the static matrix.
        """
        from_token = self._resolve(from_token)
        to_token = self._resolve(to_token)

        key = f"{from_token}->{to_token}"
        candidates_data = self._routes.get(key, [])
        if not isinstance(candidates_data, list):
            # Compatibility for single-route matrix
            candidates_data = [candidates_data]

        routes = []
        for r in candidates_data:
            routes.append(Route(
                src=from_token,
                dst=to_token,
                path=r["path"],
                hops=r["hops"],
                total_fee_percent=r["total_fee_percent"],
                num_hops=r["num_hops"],
            ))
        return routes

    def route(self, from_token: str, to_token: str) -> Optional[Route]:
        """
        Legacy: returns the first candidate route.
        """
        cs = self.candidates(from_token, to_token)
        return cs[0] if cs else None

    def quote(self, from_token: str, to_token: str, amount: float,
              mode: str = "exact_in") -> Optional[Quote]:
        """
        Get live-priced quotes for ALL candidates and pick the BEST.
        """
        candidates = self.candidates(from_token, to_token)
        if not candidates:
            logger.error(f"No route candidates: {from_token} -> {to_token}")
            return None

        engine = self._get_engine()
        if not engine:
            logger.warning("No engine available (no private key). Returning first candidate static quote.")
            return Quote(
                route=candidates[0],
                amount_in=amount if mode == "exact_in" else 0,
                amount_out=0 if mode == "exact_in" else amount,
                min_amount_out=0,
                mode=mode,
                slippage_percent=self.max_slippage * 100,
                price_per_unit=0,
            )

        best_quote = None
        
        for rt in candidates:
            try:
                if rt.num_hops == 1:
                    amount_out_raw = self._quote_single_hop(engine, rt, amount, mode)
                else:
                    amount_out_raw = self._quote_multi_hop(engine, rt, amount, mode)

                if amount_out_raw is None:
                    continue

                hop = rt.hops[-1]
                decimals_out = hop["decimals_out"]
                amount_out = amount_out_raw / (10 ** decimals_out)
                min_out = amount_out * (1 - self.max_slippage)

                if mode == "exact_in":
                    price = amount / amount_out if amount_out > 0 else 0
                    q = Quote(
                        route=rt, amount_in=amount, amount_out=amount_out,
                        min_amount_out=min_out, mode=mode,
                        slippage_percent=self.max_slippage * 100,
                        price_per_unit=price,
                    )
                else:
                    # exact_out: amount is the desired output
                    hop_first = rt.hops[0]
                    decimals_in = hop_first["decimals_in"]
                    q = Quote(
                        route=rt, amount_in=amount_out, amount_out=amount,
                        min_amount_out=amount, mode=mode,
                        slippage_percent=self.max_slippage * 100,
                        price_per_unit=amount_out / amount if amount > 0 else 0,
                    )
                
                # Pick the one with HIGHEST output (for exact_in) or LOWEST input (for exact_out)
                if best_quote is None:
                    best_quote = q
                elif mode == "exact_in" and q.amount_out > best_quote.amount_out:
                    best_quote = q
                elif mode == "exact_out" and q.amount_in < best_quote.amount_in:
                    best_quote = q

            except Exception as e:
                logger.debug(f"Candidate quote failed (path {'->'.join(rt.path)}): {e}")

        if not best_quote:
            logger.error("All candidate quotes failed")
            return None
            
        return best_quote

    def swap(self, from_token: str, to_token: str, amount: float,
             mode: str = "exact_in", simulate: bool = False) -> SwapResult:
        """
        Execute a swap.

        Args:
            from_token: canonical name
            to_token:   canonical name
            amount:     the amount
            mode:       "exact_in" or "exact_out"
            simulate:   if True, quote only (no execution)

        Returns:
            SwapResult
        """
        rt = self.route(from_token, to_token)
        if not rt:
            return SwapResult(success=False, error=f"No route: {from_token} -> {to_token}")

        engine = self._get_engine()
        if not engine:
            return SwapResult(success=False, error="No swap engine (private key not configured)")

        route_str = " -> ".join(rt.path)

        # Get quote first
        q = self.quote(from_token, to_token, amount, mode)
        if not q:
            return SwapResult(success=False, error="Quote failed", route_used=route_str)

        if simulate:
            return SwapResult(
                success=True,
                tx_hash="SIMULATED",
                amount_in=q.amount_in,
                amount_out=q.amount_out,
                route_used=route_str,
            )

        # Execute hop by hop using the proven engine
        try:
            if rt.num_hops == 1:
                result = self._execute_single_hop(engine, rt, amount, mode)
            else:
                result = self._execute_multi_hop(engine, rt, amount, mode)

            result.route_used = route_str
            return result

        except Exception as e:
            logger.error(f"Swap execution failed: {e}")
            return SwapResult(success=False, error=str(e), route_used=route_str)

    def explain(self, from_token: str, to_token: str, amount: float = 1.0) -> str:
        """
        Human-readable explanation of the route with live selection info.
        """
        from_token = self._resolve(from_token)
        to_token = self._resolve(to_token)
        
        candidates = self.candidates(from_token, to_token)
        if not candidates:
            return f"No route found in Static Matrix: {from_token} -> {to_token}"

        # Get live prices
        meta_in = self._tokens.get(from_token, {})
        meta_out = self._tokens.get(to_token, {})
        
        lp_in = self.prices.get_price(meta_in.get("id", ""))
        lp_out = self.prices.get_price(meta_out.get("id", ""))
        
        # Fallback to matrix prices
        p_in = lp_in or meta_in.get("priceUsd")
        p_out = lp_out or meta_out.get("priceUsd")
        
        src_in = "LIVE" if lp_in else "MATRIX"
        src_out = "LIVE" if lp_out else "MATRIX"

        val_in_str = f" (~${amount * p_in:.2f} [{src_in}])" if p_in else ""
        
        lines = [
            f"Static Matrix: {len(candidates)} candidates found.",
            f"Input: {amount} {from_token}{val_in_str}",
            "-" * 40
        ]
        
        # Get live quote to see which candidate wins
        q = self.quote(from_token, to_token, amount)
        if q and q.amount_out > 0:
            lines.append(f"Winner (Live Selection): {' -> '.join(q.route.path)}")
            lines.append(f"Est. Output: ~{q.amount_out:.8f} {to_token}")
            if p_out:
                lines.append(f"Est. Value: ~${q.amount_out * p_out:.2f} [{src_out}]")
            lines.append(f"Total fee: {q.route.total_fee_percent}%")
            lines.append(f"Hops: {q.route.num_hops}")
        else:
            # Fallback to matrix info if quoting fails or returns 0
            # (common if no private key/engine is configured)
            rt = q.route if q else candidates[0]
            lines.append(f"Candidate (Matrix): {' -> '.join(rt.path)}")
            if p_in and p_out:
                est_out = (amount * p_in) / p_out
                lines.append(f"Est. Output: ~{est_out:.6f} {to_token} (Matrix)")
                lines.append(f"Est. Value: ~${est_out * p_out:.2f} (Matrix)")
            lines.append(f"Total fee: {rt.total_fee_percent}%")
            if not q or q.amount_out == 0:
                lines.append("Note: Live quoting unavailable (using matrix fallback)")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Internal: quoting
    # ------------------------------------------------------------------

    def _quote_single_hop(self, engine, rt, amount, mode):
        """Get quote for a single-hop route."""
        hop = rt.hops[0]
        from saucerswap_v2_client import hedera_id_to_evm
        addr_in = hedera_id_to_evm(hop["token_in_id"])
        addr_out = hedera_id_to_evm(hop["token_out_id"])
        raw_amount = int(amount * (10 ** hop["decimals_in"]))
        result = engine.client.get_quote_single(addr_in, addr_out, raw_amount, hop["fee"])
        return result["amountOut"]

    def _quote_multi_hop(self, engine, rt, amount, mode):
        """Get quote for a multi-hop route."""
        from saucerswap_v2_client import hedera_id_to_evm
        token_path = []
        fee_tiers = []
        for hop in rt.hops:
            if not token_path:
                token_path.append(hedera_id_to_evm(hop["token_in_id"]))
            token_path.append(hedera_id_to_evm(hop["token_out_id"]))
            fee_tiers.append(hop["fee"])

        raw_amount = int(amount * (10 ** rt.hops[0]["decimals_in"]))
        result = engine.client.get_quote_multi_hop(token_path, fee_tiers, raw_amount)
        return result["amount_out"]

    # ------------------------------------------------------------------
    # Internal: execution
    # ------------------------------------------------------------------

    def _execute_single_hop(self, engine, rt, amount, mode):
        """Execute single-hop swap via proven engine."""
        hop = rt.hops[0]
        return engine.swap(
            token_in_id=hop["token_in_id"],
            token_out_id=hop["token_out_id"],
            amount=amount,
            decimals_in=hop["decimals_in"],
            decimals_out=hop["decimals_out"],
            fee=hop["fee"],
            slippage=self.max_slippage,
            is_exact_input=(mode == "exact_in"),
        )

    def _execute_multi_hop(self, engine, rt, amount, mode):
        """
        Execute multi-hop swap.
        Uses the engine's multi-hop path encoding for atomic execution.
        """
        from saucerswap_v2_client import encode_path
        import time as _time

        # Build the full path
        path_ids = []
        path_fees = []
        for hop in rt.hops:
            if not path_ids:
                path_ids.append(hop["token_in_id"])
            path_ids.append(hop["token_out_id"])
            path_fees.append(hop["fee"])

        first_hop = rt.hops[0]
        last_hop = rt.hops[-1]
        is_hbar_in = first_hop["token_in_id"] == "0.0.1456986"
        is_hbar_out = last_hop["token_out_id"] == "0.0.1456986"

        raw_amount_in = int(amount * (10 ** first_hop["decimals_in"]))

        # Get quote for min output
        quote_out = self._quote_multi_hop(engine, rt, amount, mode)
        if quote_out is None:
            from btc_rebalancer_swap_engine import SwapResult as EngineResult
            return SwapResult(success=False, error="Multi-hop quote failed")

        min_out = int(quote_out * (1 - self.max_slippage))
        path_bytes = encode_path(path_ids, path_fees)
        deadline = int(_time.time() * 1000) + 600000  # 10 min, milliseconds

        # Build and send transaction using the engine's extended router
        from saucerswap_v2_client import hedera_id_to_evm

        # Handle allowance for non-HBAR input
        if not is_hbar_in:
            addr_in = hedera_id_to_evm(first_hop["token_in_id"])
            erc20_abi = [
                {"inputs":[{"name":"owner","type":"address"},{"name":"spender","type":"address"}],
                 "name":"allowance","outputs":[{"type":"uint256"}],"stateMutability":"view","type":"function"},
                {"inputs":[{"name":"spender","type":"address"},{"name":"amount","type":"uint256"}],
                 "name":"approve","outputs":[{"type":"bool"}],"stateMutability":"nonpayable","type":"function"}
            ]
            erc20 = engine.w3.eth.contract(address=addr_in, abi=erc20_abi)
            allowance = erc20.functions.allowance(engine.eoa, engine.client.router_address).call()
            if allowance < raw_amount_in:
                logger.info(f"Approving {first_hop['from']} for router...")
                tx = erc20.functions.approve(
                    engine.client.router_address, raw_amount_in * 10
                ).build_transaction({
                    "from": engine.eoa,
                    "nonce": engine.w3.eth.get_transaction_count(engine.eoa),
                    "gas": 150000,
                    "gasPrice": engine.w3.eth.gas_price,
                })
                signed = engine.w3.eth.account.sign_transaction(tx, engine.private_key)
                tx_hash = engine.w3.eth.send_raw_transaction(signed.raw_transaction)
                engine.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
                _time.sleep(3)

        # Build swap tx
        params = (path_bytes, engine.eoa, deadline, raw_amount_in, min_out)
        value = int(amount * 10**18) if is_hbar_in else 0

        tx = engine.router_extended.functions.exactInput(params).build_transaction({
            "from": engine.eoa,
            "value": value,
            "gas": 1500000,
            "gasPrice": engine.w3.eth.gas_price,
            "nonce": engine.w3.eth.get_transaction_count(engine.eoa),
            "chainId": engine.client.chain_id,
        })

        signed = engine.w3.eth.account.sign_transaction(tx, engine.private_key)
        tx_hash = engine.w3.eth.send_raw_transaction(signed.raw_transaction)
        logger.info(f"Multi-hop swap TX sent: {tx_hash.hex()}")

        receipt = engine.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        if receipt.status == 1:
            return SwapResult(
                success=True,
                tx_hash=tx_hash.hex(),
                amount_in=amount,
                amount_out=quote_out / (10 ** last_hop["decimals_out"]),
                gas_used=receipt.gasUsed,
            )
        else:
            return SwapResult(success=False, tx_hash=tx_hash.hex(), error="Transaction reverted")

    # ------------------------------------------------------------------
    # Internal: helpers
    # ------------------------------------------------------------------

    def _resolve(self, token: str) -> str:
        """Resolve token name to canonical form. Case-insensitive."""
        upper = token.upper()
        # Direct match
        if upper in self._tokens:
            return upper
        # Try common aliases
        for canon in self._tokens:
            if canon.upper() == upper:
                return canon
        return token  # Return as-is, will fail later if invalid

    def _get_engine(self):
        """Lazy-load the swap engine (needs private key)."""
        if self._engine is not None:
            return self._engine

        try:
            from btc_rebalancer_swap_engine import SaucerSwapV2Engine
            self._engine = SaucerSwapV2Engine()
            return self._engine
        except Exception as e:
            logger.warning(f"Could not initialize swap engine: {e}")
            self._engine = False  # Don't retry
            return None


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    from pacman_translator import resolve_token

    agent = PacmanAgent()

    # Interactive Mode (REPL)
    if len(sys.argv) < 2:
        print("="*60)
        print("🤖 PACMAN AGENT - AI-NATIVE (Brain v2 Matrix)")
        print("="*60)
        print("Commands: tokens, explain [from] [to] [amt], quote [from] [to] [amt], swap [from] [to] [amt], exit")
        print()
        
        while True:
            try:
                line = input("pacman> ").strip()
                if not line or line.lower() in ["exit", "quit"]:
                    break
                
                parts = line.split()
                cmd = parts[0].lower()
                args = parts[1:]

                if cmd == "tokens":
                    for name, meta in agent.tokens().items():
                        print(f"  {name:12s}  {meta['id']:16s}  {meta['decimals']} decimals")
                
                elif cmd in ["explain", "route", "quote", "swap"]:
                    if len(args) < 2:
                        print(f"Usage: {cmd} [from] [to] [amount]")
                        continue
                        
                    from_token = resolve_token(args[0]) or args[0]
                    to_token = resolve_token(args[1]) or args[1]
                    amount = float(args[2]) if len(args) > 2 else 1.0

                    if cmd in ["explain", "route"]:
                        print(agent.explain(from_token, to_token, amount))
                    
                    elif cmd == "quote":
                        q = agent.quote(from_token, to_token, amount)
                        if q:
                            print(f"Winner: {' -> '.join(q.route.path)}")
                            print(f"Send:   {q.amount_in} {q.route.src}")
                            print(f"Get:    ~{q.amount_out:.8f} {q.route.dst}")
                            print(f"Min:    {q.min_amount_out:.8f} {q.route.dst} (after {q.slippage_percent}% slippage)")
                            print(f"Fee:    {q.route.total_fee_percent}%")
                        else:
                            print("Quote failed")
                            
                    elif cmd == "swap":
                        result = agent.swap(from_token, to_token, amount)
                        if result.success:
                            print(f"SUCCESS: {result.tx_hash}")
                            print(f"Sent: {result.amount_in}, Got: {result.amount_out}")
                        else:
                            print(f"FAILED: {result.error}")
                else:
                    print(f"Unknown command: {cmd}")
            except KeyboardInterrupt:
                print("\nGoodbye!")
                break
            except Exception as e:
                print(f"Error: {e}")
        sys.exit(0)

    # One-shot Mode (CLI)
    cmd = sys.argv[1].lower()

    if cmd == "tokens":
        for name, meta in agent.tokens().items():
            print(f"  {name:12s}  {meta['id']:16s}  {meta['decimals']} decimals")

    elif cmd in ["explain", "route"] and len(sys.argv) >= 4:
        from_token = resolve_token(sys.argv[2]) or sys.argv[2]
        to_token = resolve_token(sys.argv[3]) or sys.argv[3]
        amount = float(sys.argv[4]) if len(sys.argv) > 4 else 1.0
        print(agent.explain(from_token, to_token, amount))

    elif cmd == "quote" and len(sys.argv) >= 4:
        from_token = resolve_token(sys.argv[2]) or sys.argv[2]
        to_token = resolve_token(sys.argv[3]) or sys.argv[3]
        amount = float(sys.argv[4]) if len(sys.argv) > 4 else 1.0
        q = agent.quote(from_token, to_token, amount)
        if q:
            print(f"Winner: {' -> '.join(q.route.path)}")
            print(f"Send:   {q.amount_in} {q.route.src}")
            print(f"Get:    ~{q.amount_out:.8f} {q.route.dst}")
            print(f"Min:    {q.min_amount_out:.8f} {q.route.dst} (after {q.slippage_percent}% slippage)")
            print(f"Fee:    {q.route.total_fee_percent}%")
        else:
            print("Quote failed")

    elif cmd == "swap" and len(sys.argv) >= 5:
        from_token = resolve_token(sys.argv[2]) or sys.argv[2]
        to_token = resolve_token(sys.argv[3]) or sys.argv[3]
        amount = float(sys.argv[4])
        result = agent.swap(from_token, to_token, amount)
        if result.success:
            print(f"SUCCESS: {result.tx_hash}")
            print(f"Sent: {result.amount_in}, Got: {result.amount_out}")
        else:
            print(f"FAILED: {result.error}")

    else:
        print(f"Unknown command: {cmd}")
        print("Usage: ./pacman [tokens|explain|quote|swap] [from] [to] [amount]")
