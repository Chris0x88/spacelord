import json
import math
from pathlib import Path
from cli.display import C

def _calculate_pool_stats(pool: dict) -> tuple[float, float]:
    """Calculate TVL (USD) and instantaneous Price (TokenB / TokenA) from pool data."""
    try:
        ta = pool.get("tokenA", {})
        tb = pool.get("tokenB", {})
        
        # Calculate TVL
        tvl = 0.0
        amount_a = int(pool.get("amountA", 0))
        amount_b = int(pool.get("amountB", 0))
        price_a_usd = float(ta.get("priceUsd", 0.0))
        price_b_usd = float(tb.get("priceUsd", 0.0))
        dec_a = ta.get("decimals", 6)
        dec_b = tb.get("decimals", 6)
        
        tvl += (amount_a / (10**dec_a)) * price_a_usd
        tvl += (amount_b / (10**dec_b)) * price_b_usd
        
        # Calculate Price from tickCurrent (1.0001^tick * 10^(decA - decB))
        tick = pool.get("tickCurrent")
        price_b_per_a = 0.0
        if tick is not None:
            raw_price = 1.0001 ** tick
            price_b_per_a = raw_price * (10 ** (dec_a - dec_b))

        return tvl, price_b_per_a
    except Exception:
        return 0.0, 0.0

def _get_tick_spacing(fee: int) -> int:
    """Uniswap V3 standard tick spacings."""
    if fee == 500: return 10
    if fee == 3000: return 60
    if fee == 10000: return 200
    return 60

def cmd_pool_deposit(app, args):
    """
    Deposit tokens into a V2 liquidity pool.
    Usage (Interactive): pool-deposit
    Usage (Direct): pool-deposit <token0> <token1> <amount0> <amount1> <fee_tier> <tick_lower> <tick_upper> [--dry-run]
    """
    dry_run = "--dry-run" in args
    args = [a for a in args if a != "--dry-run"]
    
    if len(args) == 0:
        # --- NEW POOL-CENTRIC INTERACTIVE WIZARD ---
        print(f"\n  {C.ACCENT}🌊{C.R} V2 Liquidity Setup (Pool Discovery)")
        print(f"  {C.CHROME}{'─' * 80}{C.R}")
        
        query = input(f"  Search Pool by Token Symbol (e.g., HBAR, USDC): ").strip().upper()
        if not query:
            return

        # Load cached pools
        raw_path = Path("data/pacman_data_raw.json")
        if not raw_path.exists():
            print(f"  {C.ERR}✗{C.R} Pool data not found. Please wait 60s and try again, or run python -m scripts.refresh_data")
            return
            
        try:
            with open(raw_path) as f:
                pools = json.load(f)
        except Exception as e:
            print(f"  {C.ERR}✗{C.R} Error reading pool data: {e}")
            return
            
        # Filter and Score matches
        matches = []
        for p in pools:
            ta = p.get("tokenA", {})
            tb = p.get("tokenB", {})
            sym_a = ta.get("symbol", "").upper()
            sym_b = tb.get("symbol", "").upper()
            
            if query in sym_a or query in sym_b:
                tvl, current_price = _calculate_pool_stats(p)
                # Getting USD equivalent of Token A
                price_a_usd = float(ta.get("priceUsd", 0.0))
                price_b_usd = float(tb.get("priceUsd", 0.0))
                
                # The "Current Price" is TokenB per TokenA. 
                # So we show the USD value of 1 TokenA to give context.
                token_a_usd = price_a_usd 
                
                matches.append({
                    "pool": p,
                    "sym_a": sym_a,
                    "sym_b": sym_b,
                    "tvl": tvl,
                    "price": current_price,
                    "token_a_usd": token_a_usd,
                    "fee": p.get("fee", 3000)
                })
                
        if not matches:
            print(f"  {C.WARN}⚠{C.R} No pools found matching '{query}'.")
            return
            
        # Sort by TVL descending
        matches.sort(key=lambda x: x["tvl"], reverse=True)
        
        print(f"\n  {C.BOLD}Matching Pools (Sorted by TVL):{C.R}")
        print(f"  {C.CHROME}{'ID':<4} | {'Pair':<15} | {'Fee':<6} | {'TVL':<12} | {'Current Price':<17} | {'USD Equiv':<10}{C.R}")
        print(f"  {C.CHROME}{'-'*80}{C.R}")
        
        for i, m in enumerate(matches[:10]): # Show top 10
            fee_pct = f"{m['fee']/10000:.2f}%"
            tvl_str = f"${m['tvl']:,.0f}" if m['tvl'] > 0 else "N/A"
            price_str = f"{m['price']:.4g} {m['sym_b'][:5]}" if m['price'] > 0 else "N/A"
            usd_str = f"${m['token_a_usd']:.4f}" if m['token_a_usd'] > 0 else "N/A"
            pair_str = f"{m['sym_a']}/{m['sym_b']}"
            print(f"  [{i+1:<2}] | {pair_str:<15} | {fee_pct:<6} | {tvl_str:<12} | {price_str:<17} | {usd_str:<10}")
            
        choice = input(f"\n  Select Pool (1-{min(10, len(matches))}) or 'q' to quit: ").strip()
        if choice.lower() == 'q' or not choice.isdigit(): return
        
        idx = int(choice) - 1
        if idx < 0 or idx >= len(matches):
            print(f"  {C.ERR}✗{C.R} Invalid choice.")
            return
            
        selected = matches[idx]
        pool = selected["pool"]
        token0_sym = selected["sym_a"]
        token1_sym = selected["sym_b"]
        token0_id = pool.get("tokenA", {}).get("id")
        token1_id = pool.get("tokenB", {}).get("id")
        fee = selected["fee"]
        tick_current = pool.get("tickCurrent", 0)
        tick_spacing = _get_tick_spacing(fee)
        
        print(f"\n  {C.ACCENT}▶{C.R} Selected: {C.BOLD}{token0_sym}/{token1_sym} ({fee/10000:.2f}% Fee){C.R}")
        print(f"  {C.MUTED}Current tick: {tick_current} (Price: {selected['price']:.4g} {token1_sym} per {token0_sym}){C.R}")
        
        try:
            # First, ask for the range
            print(f"\n  {C.BOLD}Step 1: Select Price Range{C.R}")
            print(f"  {C.MUTED}Note: Your chosen range bounds determining the required ratio of tokens.{C.R}")
            print(f"  {C.MUTED}If you only provide one token amount, you will provide single-sided liquidity.{C.R}")
            print(f"  [1] +/- 2%  (Standard Concentrated)")
            print(f"  [2] +/- 5%  (Wide Concentrated)")
            print(f"  [3] +/- 10% (Very Wide)")
            print(f"  [4] Full Range (-887220 to 887220)")
            print(f"  [5] Custom Ticks")
            
            range_choice = input(f"  Range Choice (1-5): ").strip()
            
            if range_choice == "4":
                tick_lower, tick_upper = -887220, 887220
            elif range_choice in ["1", "2", "3"]:
                pct = 0.02 if range_choice == "1" else (0.05 if range_choice == "2" else 0.10)
                tick_delta = int(math.log(1 + pct) / math.log(1.0001))
                raw_lower = tick_current - tick_delta
                raw_upper = tick_current + tick_delta
                tick_lower = (raw_lower // tick_spacing) * tick_spacing
                tick_upper = (raw_upper // tick_spacing) * tick_spacing
                tick_lower = max(-887220, tick_lower)
                tick_upper = min(887220, tick_upper)
            elif range_choice == "5":
                tick_lower = int(input(f"  Tick Lower (multiple of {tick_spacing}): ").strip())
                tick_upper = int(input(f"  Tick Upper (multiple of {tick_spacing}): ").strip())
            else:
                print(f"  {C.ERR}✗{C.R} Invalid choice.")
                return

            # Step 2: Smart single-token input
            # Determine which token to ask for based on the current tick's position in the range.
            # If fully below: only token0 (out-of-range, single-sided)
            # If fully above: only token1 (out-of-range, single-sided)
            # If in range: ask for whichever the user wants to anchor, derive the other.
            print(f"")
            print(f"  {C.BOLD}Step 2: Enter Your Primary Token Amount{C.R}")
            
            is_below_range = tick_current < tick_lower
            is_above_range = tick_current >= tick_upper
            is_in_range = not is_below_range and not is_above_range

            if is_below_range:
                print(f"  {C.MUTED}Current price is below your range → Single-sided {token0_sym} only.{C.R}")
                amount0 = float(input(f"  Amount of {token0_sym:<10}: ").strip())
                amount1 = 0.0
            elif is_above_range:
                print(f"  {C.MUTED}Current price is above your range → Single-sided {token1_sym} only.{C.R}")
                amount0 = 0.0
                amount1 = float(input(f"  Amount of {token1_sym:<10}: ").strip())
            else:
                # In-range: ask for the first token only, derive the second
                print(f"  {C.MUTED}Enter your anchor amount; the other token is auto-calculated from the range.{C.R}")
                anchor_input = input(f"  Amount of {token0_sym:<10} (anchor): ").strip()
                amount0 = float(anchor_input)
                amount1 = 0.0  # Will be derived
            
            if amount0 == 0 and amount1 == 0:
                print(f"  {C.ERR}✗{C.R} You must provide at least one token amount.")
                return

            # Keep token0 and token1 as the human-readable symbols for the confirmation display
            token0 = token0_sym
            token1 = token1_sym

        except ValueError:
            print(f"  {C.ERR}✗{C.R} Invalid numeric input.")
            return
            
    elif len(args) < 7:
        print(f"  {C.ERR}✗{C.R} Usage: {C.BOLD}pool-deposit <token0> <token1> <amount0> <amount1> <fee> <tickLower> <tickUpper> [--dry-run]{C.R}")
        return
    else:
        # Direct command line mode (unchanged)
        token0, token1 = args[0], args[1]
        try:
            amount0 = float(args[2])
            amount1 = float(args[3])
            fee = int(args[4])
            tick_lower = int(args[5])
            tick_upper = int(args[6])
        except ValueError:
            print(f"  {C.ERR}✗{C.R} Invalid numeric arguments.")
            return

    # Estimate the derived amount for display in confirmation
    # (Controller will recalculate this precisely before sending)
    try:
        import json as _json, math as _math
        from pathlib import Path as _Path
        _raw_path = _Path("data/pacman_data_raw.json")
        _pool_tick = tick_lower  # fallback
        if _raw_path.exists():
            _pools = _json.load(open(_raw_path))
            for _p in _pools:
                _ta, _tb = _p.get("tokenA", {}), _p.get("tokenB", {})
                if {_ta.get("symbol", "").upper(), _tb.get("symbol", "").upper()} == {token0.upper(), token1.upper()}:
                    if _p.get("fee") == fee:
                        _pool_tick = _p.get("tickCurrent", tick_lower)
                        break
        _sqrt_p  = _math.sqrt(1.0001 ** _pool_tick)
        _sqrt_pa = _math.sqrt(1.0001 ** tick_lower)
        _sqrt_pb = _math.sqrt(1.0001 ** tick_upper)
        # In-range estimate: derive amount1 from amount0
        if amount0 > 0 and amount1 == 0 and tick_lower <= _pool_tick < tick_upper:
            _liq = amount0 / (1.0/_sqrt_p - 1.0/_sqrt_pb)
            _est1 = _liq * (_sqrt_p - _sqrt_pa)
            est_label = f"~{_est1:.4f} {token1} (auto-estimated)"
        elif amount1 > 0 and amount0 == 0 and tick_lower <= _pool_tick < tick_upper:
            _liq = amount1 / (_sqrt_p - _sqrt_pa)
            _est0 = _liq * (1.0/_sqrt_p - 1.0/_sqrt_pb)
            est_label = f"~{_est0:.4f} {token0} (auto-estimated) + {amount1} {token1}"
        else:
            est_label = f"{amount0} {token0} + {amount1} {token1}"
    except Exception:
        est_label = f"{amount0} {token0} + {amount1} {token1}"

    print(f"\n  {C.ACCENT}🌊{C.R} V2 Pool Deposit: {token0}/{token1} at {fee/10000:.2f}% fee tier")
    print(f"  {C.MUTED}Range: [{tick_lower}, {tick_upper}] | Deposit: {est_label}{C.R}")

    if dry_run:
        print(f"  {C.WARN}⚠  SIMULATION MODE{C.R}")

    if app.config.require_confirmation and not dry_run:
        confirm = input(f"  Confirm? {C.MUTED}(y/n){C.R} ").strip().lower()
        if confirm not in ["y", "yes"]:
            print(f"  {C.MUTED}Cancelled.{C.R}")
            return

    try:
        tx_hash = app.add_liquidity(token0, token1, fee, tick_lower, tick_upper, amount0, amount1, dry_run=dry_run)
        print(f"\n  {C.OK}✅ Success!{C.R}")
        if not dry_run:
            print(f"  {C.MUTED}TxHash: {C.TEXT}{tx_hash}{C.R}")
            print(f"  {C.MUTED}Explorer: {C.TEXT}https://hashscan.io/{app.network}/transaction/{tx_hash}{C.R}")
    except Exception as e:
        print(f"\n  {C.ERR}✗{C.R} FAILED: {str(e)}")


def cmd_pool_withdraw(app, args):
    """
    Withdraw liquidity from a V2 pool.
    Usage (Interactive): pool-withdraw
    Usage (Direct):      pool-withdraw <nft_id> <liquidity_amount> [--dry-run]
    """
    import math as _math, json as _json

    dry_run = "--dry-run" in args
    clean_args = [a for a in args if a != "--dry-run"]

    nft_id = None
    liquidity = None

    if len(clean_args) >= 2:
        # Direct mode — args provided on command line
        try:
            nft_id = int(clean_args[0])
            liquidity = int(clean_args[1])
        except ValueError:
            print(f"  {C.ERR}✗{C.R} Invalid numeric arguments.")
            return
    else:
        # Interactive wizard — fetch live positions from chain
        print(f"\n  {C.ACCENT}🌊{C.R} V2 Pool Withdraw (Position Selector)")
        print(f"  {C.CHROME}{'─' * 72}{C.R}")
        print(f"  {C.MUTED}Fetching your active liquidity positions...{C.R}")

        try:
            positions = app.get_liquidity_positions()
        except Exception as e:
            print(f"  {C.ERR}✗{C.R} Failed to fetch positions: {e}")
            return

        if not positions:
            print(f"  {C.WARN}⚠  No active V2 liquidity positions found.{C.R}")
            return

        # Load token names
        tokens_data = {}
        try:
            with open("data/tokens.json") as f:
                tokens_data = _json.load(f)
        except Exception:
            pass

        def evm_to_id(addr):
            return f"0.0.{int(addr.lower(), 16)}"

        def get_sym(tid):
            if tid == "0.0.1456986": return "HBAR"
            for _, m in tokens_data.items():
                if m.get("id") == tid:
                    return m.get("symbol", tid)
            return tid

        print(f"\n  {C.BOLD}Your Active Positions:{C.R}")
        print(f"  {C.CHROME}{'─' * 72}{C.R}")

        for i, pos in enumerate(positions):
            t0_sym = get_sym(evm_to_id(pos['token0']))
            t1_sym = get_sym(evm_to_id(pos['token1']))
            pair = f"{t0_sym}/{t1_sym}"
            fee_pct = pos['fee'] / 10000
            tick_lower  = pos.get('tick_lower', 0)
            tick_upper  = pos.get('tick_upper', 0)
            tick_current = pos.get('tick_current', tick_lower)
            in_range = tick_lower <= tick_current < tick_upper
            range_icon = f"{C.OK}●{C.R}" if in_range else f"{C.WARN}○{C.R}"
            liq = pos.get('liquidity', 0)

            # V3 estimated holdings
            est_t0, est_t1 = 0.0, 0.0
            try:
                sqp  = _math.sqrt(1.0001 ** tick_current)
                sqpa = _math.sqrt(1.0001 ** tick_lower)
                sqpb = _math.sqrt(1.0001 ** tick_upper)
                if sqpa > sqpb: sqpa, sqpb = sqpb, sqpa
                if tick_current < tick_lower:
                    est_t0 = liq * (1.0/sqpa - 1.0/sqpb) / 1e8
                elif tick_current >= tick_upper:
                    est_t1 = liq * (sqpb - sqpa) / 1e8
                else:
                    est_t0 = liq * (1.0/sqp - 1.0/sqpb) / 1e8
                    est_t1 = liq * (sqp - sqpa) / 1e8
            except Exception:
                pass

            t0_str = f"~{est_t0:.4f} {t0_sym}" if est_t0 > 0 else ""
            t1_str = f"~{est_t1:.4f} {t1_sym}" if est_t1 > 0 else ""
            holdings = " + ".join(filter(None, [t0_str, t1_str])) or "—"

            print(f"  [{i+1}] NFT #{pos['id']}  {C.ACCENT}{pair}{C.R} @ {fee_pct:.2f}%  {range_icon}")
            print(f"      Ticks: [{tick_lower:,} → {tick_upper:,}]  (current: {tick_current:,})")
            print(f"      Est. Holdings: {C.TEXT}{holdings}{C.R}   Liquidity: {liq:,}")
            print()

        choice = input(f"  Select Position (1-{len(positions)}) or 'q' to quit: ").strip()
        if choice.lower() == 'q' or not choice.isdigit():
            return

        idx = int(choice) - 1
        if idx < 0 or idx >= len(positions):
            print(f"  {C.ERR}✗{C.R} Invalid choice.")
            return

        pos = positions[idx]
        nft_id = pos['id']
        total_liq = pos['liquidity']

        print(f"\n  {C.BOLD}How much liquidity to remove?{C.R}")
        print(f"  {C.MUTED}Total available: {total_liq:,}{C.R}")
        print(f"  [1] 100%  (full withdrawal)")
        print(f"  [2]  50%")
        print(f"  [3] Custom amount")
        pct = input("  Choice (1-3): ").strip()

        if pct == "1":
            liquidity = total_liq
        elif pct == "2":
            liquidity = total_liq // 2
        elif pct == "3":
            try:
                liquidity = int(input(f"  Amount (max {total_liq:,}): ").strip())
            except ValueError:
                print(f"  {C.ERR}✗{C.R} Invalid amount.")
                return
        else:
            print(f"  {C.ERR}✗{C.R} Invalid choice.")
            return

    pct_of_total = f" ({liquidity / pos['liquidity'] * 100:.0f}%)" if nft_id and 'liquidity' in locals().get('pos', {}) else ""
    print(f"\n  {C.ACCENT}🌊{C.R} V2 Pool Withdraw: NFT #{nft_id} | Removing {liquidity:,} liquidity units{pct_of_total}")

    if dry_run:
        print(f"  {C.WARN}⚠  SIMULATION MODE{C.R}")

    if app.config.require_confirmation and not dry_run:
        confirm = input(f"  Confirm? {C.MUTED}(y/n){C.R} ").strip().lower()
        if confirm not in ["y", "yes"]:
            print(f"  {C.MUTED}Cancelled.{C.R}")
            return

    try:
        tx_hashes = app.remove_liquidity(nft_id, liquidity, dry_run=dry_run)
        print(f"\n  {C.OK}✅ Success!{C.R}")
        if not dry_run:
            print(f"  {C.MUTED}DecreaseLiquidity: {C.TEXT}{tx_hashes[0]}{C.R}")
            print(f"  {C.MUTED}Collect:           {C.TEXT}{tx_hashes[1]}{C.R}")
            print(f"  {C.MUTED}Explorer: {C.TEXT}https://hashscan.io/{app.network}/transaction/{tx_hashes[0]}{C.R}")
    except Exception as e:
        print(f"\n  {C.ERR}✗{C.R} FAILED: {str(e)}")

def cmd_lp_positions(app, args):
    """
    Dedicated command to view active V2 Liquidity positions.
    Usage: lp
    """
    from cli.display import show_balance
    print(f"\n  {C.ACCENT}🌊{C.R} Querying live LP positions...")
    try:
        positions = app.get_liquidity_positions()
        # show_balance has the logic to render positions if passed
        show_balance(app.executor, lp_positions=positions)
    except Exception as e:
        print(f"  {C.ERR}✗{C.R} Error fetching LP positions: {e}")

def cmd_lp_positions(app, args):
    """
    Dedicated command to view active V2 Liquidity positions (NFTs only).
    Usage: lp  |  positions
    """
    import math as _math, json as _json

    print(f"\n  {C.BOLD}{C.ACCENT}V2 LIQUIDITY POSITIONS{C.R}")
    print(f"  {C.CHROME}{'─' * 72}{C.R}")
    print(f"  {C.MUTED}Fetching active positions from chain...{C.R}")

    try:
        positions = app.get_liquidity_positions()
    except Exception as e:
        print(f"  {C.ERR}✗{C.R} Error: {e}")
        return

    if not positions:
        print(f"  {C.WARN}⚠  No active V2 LP positions found.{C.R}")
        print(f"  {C.MUTED}Run 'pool-deposit' to create a position.{C.R}\n")
        return

    # Load token names
    tokens_data = {}
    try:
        with open("data/tokens.json") as f:
            tokens_data = _json.load(f)
    except Exception:
        pass

    def evm_to_id(addr):
        return f"0.0.{int(addr.lower(), 16)}"

    def get_sym(tid):
        if tid == "0.0.1456986": return "HBAR"
        for _, m in tokens_data.items():
            if m.get("id") == tid:
                return m.get("symbol", tid)
        return tid

    for pos in positions:
        t0_sym = get_sym(evm_to_id(pos['token0']))
        t1_sym = get_sym(evm_to_id(pos['token1']))
        pair = f"{t0_sym}/{t1_sym}"
        fee_pct = pos['fee'] / 10000
        tick_lower  = pos.get('tick_lower', 0)
        tick_upper  = pos.get('tick_upper', 0)
        tick_current = pos.get('tick_current', tick_lower)
        in_range = tick_lower <= tick_current < tick_upper
        range_icon  = f"{C.OK}●{C.R}" if in_range else f"{C.WARN}○{C.R}"
        range_label = "In Range" if in_range else "Out of Range"
        liq = pos.get('liquidity', 0)

        # V3 estimated underlying token amounts
        est_t0, est_t1 = 0.0, 0.0
        try:
            sqp  = _math.sqrt(1.0001 ** tick_current)
            sqpa = _math.sqrt(1.0001 ** tick_lower)
            sqpb = _math.sqrt(1.0001 ** tick_upper)
            if sqpa > sqpb: sqpa, sqpb = sqpb, sqpa
            if tick_current < tick_lower:
                est_t0 = liq * (1.0/sqpa - 1.0/sqpb) / 1e8
            elif tick_current >= tick_upper:
                est_t1 = liq * (sqpb - sqpa) / 1e8
            else:
                est_t0 = liq * (1.0/sqp - 1.0/sqpb) / 1e8
                est_t1 = liq * (sqp - sqpa) / 1e8
        except Exception:
            pass

        t0_str = f"~{est_t0:.4f} {t0_sym}" if est_t0 > 0 else ""
        t1_str = f"~{est_t1:.4f} {t1_sym}" if est_t1 > 0 else ""
        holdings = " + ".join(filter(None, [t0_str, t1_str])) or "—"

        print(f"\n  {C.BOLD}{C.TEXT}NFT #{pos['id']}{C.R}  {C.ACCENT}{pair}{C.R}  Fee: {C.TEXT}{fee_pct:.2f}%{C.R}  {range_icon} {C.MUTED}{range_label}{C.R}")
        print(f"  {C.CHROME}{'─' * 56}{C.R}")
        print(f"  {C.MUTED}Tick Range:{C.R} {C.TEXT}[{tick_lower:,} → {tick_upper:,}]{C.R}  {C.MUTED}Current: {tick_current:,}{C.R}")
        print(f"  {C.MUTED}Est. Holdings:{C.R} {C.TEXT}{holdings}{C.R}")
        print(f"  {C.MUTED}Liquidity Units:{C.R} {C.TEXT}{liq:,}{C.R}")

    print(f"\n  {C.MUTED}Run 'pool-withdraw' to remove liquidity from a position.{C.R}\n")
