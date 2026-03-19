"""
Pacman Controller - Headless Trading SDK
=========================================

The PacmanController class orchestrates the business logic:
- Configuration (PacmanConfig)
- Routing (PacmanVariantRouter)
- Execution (PacmanExecutor)

It is designed to be imported by CLIs, Daemons, or Web APIs.
"""

import logging
import requests
from typing import Optional, Dict, Tuple

from src.config import PacmanConfig
from src.logger import logger
from src.errors import PacmanError, ConfigurationError
from src.executor import PacmanExecutor, ExecutionResult
from src.router import PacmanVariantRouter, VariantRoute
from lib.prices import price_manager

class PacmanController:
    """
    Main controller class for Pacman.
    """

    def __init__(self, config_path: str = "config.yaml"):
        """Initialize the application components."""
        self._ensure_data_templates()
        try:
            self.config = PacmanConfig.from_env()

            # Key resolution: if active account is the robot, use robot's key
            # This is critical for oneshot mode where each CLI invocation is a
            # fresh process — reload_wallet() only runs for interactive switches.
            if (self.config.hedera_account_id
                    and self.config.hedera_account_id == self.config.robot_account_id
                    and self.config.robot_private_key):
                logger.info(f"[Init] Using robot key for {self.config.robot_account_id}")
                self.config.private_key = self.config.robot_private_key

            self.executor = PacmanExecutor(self.config)
            self.router = PacmanVariantRouter(price_manager=price_manager)
            self.router.load_pools() # Build routing graph from cached data
            
            # Record account details for display
            self.account_id = self.config.hedera_account_id
            self.network = self.config.network
            self._account_manager = None
            self._limit_engine = None
            
        except ConfigurationError as e:
            logger.error(f"Configuration error: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize PacmanApp: {e}")
            raise

    def _ensure_data_templates(self):
        """Copy .template.json files to .json if they do not exist (first boot)."""
        import shutil
        from pathlib import Path
        data_dir = Path(__file__).parent.parent / "data"
        
        if not data_dir.exists():
            data_dir.mkdir(parents=True, exist_ok=True)
            
        for template_path in data_dir.glob("*.template.json"):
            target_name = template_path.name.replace(".template.json", ".json")
            target_path = data_dir / target_name
            if not target_path.exists():
                logger.info(f"Initializing {target_name} from template...")
                shutil.copy2(template_path, target_path)

    def reload_wallet(self, hard_reset: bool = False):
        """
        Full account context switch — hot-reload credentials and reset all
        account-specific state without restarting the process.

        Steps:
          1. Stop limit order daemon (old account's orders must not fire)
          2. Re-read .env into os.environ
          3. Rebuild config + executor with new credentials
          4. Reset account manager and limit engine references
          5. Clear accounts.json and orders.json (so old orders don't fire for new account)
          6. Restart limit order daemon if it was enabled
        """
        import json
        from dotenv import load_dotenv
        from pathlib import Path

        # 1. Stop the limit order daemon before swapping credentials
        if self._limit_engine is not None and self._limit_engine.is_running:
            logger.info("[Reload] Stopping limit order daemon...")
            self._limit_engine.stop_monitor()
        was_daemon_enabled = False
        if self._limit_engine is not None:
            was_daemon_enabled = self._limit_engine._daemon_enabled

        # 2. Re-read .env
        env_path = Path(__file__).resolve().parent.parent / ".env"
        load_dotenv(dotenv_path=env_path, override=True)

        # 3. Rebuild core components
        self.config = PacmanConfig.from_env()

        # Key resolution: if the active account is the robot, use robot's key
        if (self.config.hedera_account_id == self.config.robot_account_id
                and self.config.robot_private_key):
            logger.info(f"[Reload] Switching to robot key for {self.config.robot_account_id}")
            self.config.private_key = self.config.robot_private_key

        self.executor = PacmanExecutor(self.config)
        self.account_id = self.config.hedera_account_id
        self.network = self.config.network

        # 4. Reset lazy-init references
        self._account_manager = None
        self._limit_engine = None

        # 5. Clear historical state if this is a hard reset (completely new private key)
        if hard_reset:
            accounts_path = Path(__file__).resolve().parent.parent / "data" / "accounts.json"
            try:
                with open(accounts_path, "w") as f:
                    json.dump([], f, indent=2)
                logger.info("[Reload] Cleared accounts.json for new key")
            except Exception as e:
                logger.warning(f"[Reload] Could not clear accounts.json: {e}")

            orders_path = Path(__file__).resolve().parent.parent / "data" / "orders.json"
            try:
                with open(orders_path, "w") as f:
                    json.dump([], f, indent=2)
                logger.info("[Reload] Cleared orders.json for new key")
            except Exception as e:
                logger.warning(f"[Reload] Could not clear orders.json: {e}")

        logger.info(f"[Reload] Wallet reloaded → {self.account_id}")

        # 6. Restart limit order daemon if it was running (now against new account)
        if was_daemon_enabled:
            try:
                logger.info("[Reload] Re-starting limit order daemon for new account...")
                self.limit_engine.start_monitor(self)
            except Exception as e:
                logger.warning(f"[Reload] Could not restart daemon: {e}")

    def get_balances(self, token_highlights: list = None, account_id: str = None) -> Dict[str, float]:
        """Fetch all non-zero token balances for the account."""
        if account_id:
            from lib.saucerswap import hedera_id_to_evm
            target_eoa = hedera_id_to_evm(account_id)
            # Make sure we use the eoa_override property of the executor to fetch from mirror node
            return self.executor.get_balances(token_highlights=token_highlights, eoa_override=target_eoa)
        return self.executor.get_balances(token_highlights=token_highlights)

    def get_all_account_balances(self) -> Dict[str, Dict[str, float]]:
        """Fetch balances for all configured accounts (main + robot)."""
        results = {}
        # Main account
        main_id = self.config.hedera_account_id or "Current"
        results[main_id] = self.get_balances()
        
        # Robot account
        if self.config.robot_account_id and self.config.robot_account_id != self.config.hedera_account_id:
            results[self.config.robot_account_id] = self.get_balances(account_id=self.config.robot_account_id)
            
        return results

    def get_aggregated_balances(self) -> Dict[str, float]:
        """Sum up balances across all accounts."""
        all_bal = self.get_all_account_balances()
        aggregated = {}
        for acct_id, balances in all_bal.items():
            for sym, bal in balances.items():
                aggregated[sym] = aggregated.get(sym, 0.0) + bal
        return aggregated

    def resolve_token_id(self, symbol: str) -> Optional[str]:
        """Resolve a token symbol to a Hedera ID."""
        return self.executor._get_token_id(symbol)

    def get_route(self, from_token: str, to_token: str, amount: float, mode: str = "exact_in") -> Optional[VariantRoute]:
        """
        Recommend the best route between variants.
        """
        # Clean inputs
        from_token = from_token.upper()
        to_token = to_token.upper()

        logger.debug(f"Routing request: {from_token} -> {to_token} (Amount: {amount}, Mode: {mode})")

        # 1. Calculate USD Value (Estimated) for Routing logic
        # For exact_in, amount is in from_token. For exact_out, amount is in to_token.
        basis_token = from_token if mode == "exact_in" else to_token
        usd_value = amount
        
        try:
            meta = self.router._get_token_meta(basis_token)
            token_id = meta["id"] if meta and "id" in meta else None
            
            if not token_id and basis_token in ["HBAR", "0.0.0", "WHBAR"]:
                token_id = "0.0.0"

            if token_id:
                if price_manager.hbar_price == 0:
                    price_manager.reload()
                
                # Get price from manager
                if token_id == "0.0.0":
                    price = price_manager.get_hbar_price()
                else:
                    price = price_manager.get_price(token_id)
                
                if price > 0:
                    usd_value = amount * price
        except Exception as e:
            logger.warning(f"Failed to calculate USD value for routing: {e}")

        # Router calculates fee impact in HBAR using this USD value
        return self.router.recommend_route(
            from_variant=from_token,
            to_variant=to_token,
            user_preference="auto",
            volume_usd=usd_value
        )

    def swap(self, from_token: str, to_token: str, amount: float, mode: str = "exact_in", account_id: str = None) -> ExecutionResult:
        """
        Execute a swap.
        """
        route = self.get_route(from_token, to_token, amount, mode=mode)
        if not route or route.output_format == "ERROR" or len(route.steps) == 0:
            raise PacmanError(f"No route found for {from_token} -> {to_token}")

        # Execution using the refactored raw_amount parameter
        return self.executor.execute_swap(
            route=route,
            raw_amount=amount,
            mode=mode,
            account_id_override=account_id
        )

    def transfer(self, token_symbol: str, amount: float, recipient: str, memo: str = None) -> dict:
        """
        Send tokens to another address.
        """
        from lib.transfers import execute_transfer
        return execute_transfer(self.executor, token_symbol, amount, recipient, memo=memo)

    def get_history(self, limit: int = 10):
        """Get execution history."""
        return self.executor.get_execution_history(limit)

    def toggle_verbose(self, enabled: bool = None):
        """Toggle debug logging."""
        from src.logger import set_verbose
        if enabled is not None:
             self.config.debug = enabled
        else:
             self.config.debug = not self.config.debug
             
        set_verbose(self.config.debug)
        return self.config.debug

    def resolve_account_id(self, eoa: str) -> Optional[str]:
        """
        Query Mirror Node to find the Hedera Account ID associated with an EVM EOA.
        Returns the '0.0.xxx' ID or None if not found.
        """
        if not eoa or not eoa.startswith("0x"):
            return None

        network = self.config.network
        base_url = "https://mainnet-public.mirrornode.hedera.com" if network == "mainnet" else "https://testnet.mirrornode.hedera.com"
        url = f"{base_url}/api/v1/accounts/{eoa}"

        try:
            logger.debug(f"Discovering Hedera ID for {eoa}...")
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return data.get("account")
            elif response.status_code == 404:
                logger.warning(f"Account {eoa} not found on Mirror Node. might be new/uninitialized.")
                return None
            else:
                logger.error(f"Mirror Node error ({response.status_code}): {response.text}")
                return None
        except Exception as e:
            logger.error(f"Failed to resolve account ID: {e}")
            return None

    @property
    def account_manager(self):
        """Lazy initialization of the AccountManager plugin with dynamic operator sync."""
        if self._account_manager is None:
            from src.plugins.account_manager import AccountManager
            self._account_manager = AccountManager(network=self.network)
        
        # Always sync operator if we have a key, preventing freezeWith desyncs
        # after a user runs 'setup' and switches accounts in the same session.
        if self.config.private_key:
            pk = self.config.private_key.reveal()
            clean_pk = pk.replace("0x", "")
            if len(clean_pk) == 64 and self.account_id and "." in str(self.account_id):
                try:
                    # Only update if the operator actually changed
                    if not hasattr(self._account_manager, 'operator_id') or self._account_manager.operator_id != self.account_id:
                        self._account_manager.set_operator(self.account_id, pk)
                except RuntimeError:
                    pass  # SDK not installed — basic operations still work
                except Exception as e:
                    from src.logger import logger
                    logger.warning(f"Could not sync operator with ID '{self.account_id}': {e}")
            del pk
            
        return self._account_manager

    @property
    def hcs_manager(self):
        """Lazy initialization of the HCSManager plugin (walled garden signal broadcasts)."""
        if not hasattr(self, '_hcs_manager') or self._hcs_manager is None:
            from src.plugins.hcs_manager import HcsManager
            self._hcs_manager = HcsManager(self)
        return self._hcs_manager

    @property
    def hcs10_agent(self):
        """Lazy initialization of the HCS-10 OpenConvAI agent (agent-to-agent messaging)."""
        if not hasattr(self, '_hcs10_agent') or self._hcs10_agent is None:
            from src.plugins.hcs10.plugin import Hcs10Agent
            self._hcs10_agent = Hcs10Agent(self)
        return self._hcs10_agent

    @property
    def limit_engine(self):
        """Lazy initialization of the LimitOrderEngine."""
        if self._limit_engine is None:
            from src.limit_orders import LimitOrderEngine
            self._limit_engine = LimitOrderEngine()
                
        return self._limit_engine

    def create_new_account(self, initial_balance: float = 1.0, alias_key: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
        """
        Create a completely new Hedera account.
        If alias_key is provided (hex string), it creates an account using that key (EVM Alias).
        Otherwise, it generates a fresh key pair.
        The creation is funded by the current operator account.
        """
        return self.account_manager.create_account(
            initial_balance_hbar=initial_balance,
            alias_key=alias_key
        )

    def create_sub_account(self, initial_balance: float = 1.0, nickname: str = "", purpose: Optional[str] = None) -> Optional[str]:
        """
        Create a new derived sub-account using the main private key.
        """
        return self.account_manager.create_sub_account(
            initial_balance_hbar=initial_balance, 
            nickname=nickname,
            purpose=purpose
        )

    def rename_account(self, account_id: str, nickname: str) -> bool:
        """Update the nickname for a known account in the local registry."""
        return self.account_manager.rename_account(account_id, nickname)

    def get_known_accounts(self) -> list:
        """Get the list of known account IDs from the local registry."""
        return self.account_manager.get_known_accounts()

    def associate_token(self, token_id: str) -> bool:
        """Associate a token with the current operator account."""
        return self.account_manager.associate_token(token_id)

    @property
    def liquidity_manager(self):
        """Lazy initialization of the V2LiquidityManager."""
        if not hasattr(self, '_liquidity_manager') or self._liquidity_manager is None:
            from lib.v2_liquidity import V2LiquidityManager
            pk = self.config.private_key.reveal() if self.config.private_key else None
            self._liquidity_manager = V2LiquidityManager(
                w3=self.executor.w3, 
                network=self.network, 
                private_key=pk
            )
            if pk:
                del pk
        return self._liquidity_manager

    def _calculate_v2_amounts(self, tick_current: int, tick_lower: int, tick_upper: int, amount0: int, amount1: int) -> tuple[int, int]:
        """
        Estimate required amount0 and amount1 for a given tick range.
        Handles one-sided or unoptimized two-sided inputs by calculating the correct ratio.
        All inputs and outputs are in raw integer amounts.
        """
        import math
        
        # Sqrt prices
        sqrt_p = math.sqrt(1.0001 ** tick_current)
        sqrt_pa = math.sqrt(1.0001 ** tick_lower)
        sqrt_pb = math.sqrt(1.0001 ** tick_upper)

        if sqrt_pa > sqrt_pb:
            sqrt_pa, sqrt_pb = sqrt_pb, sqrt_pa

        # If user only provided amount0
        if amount0 > 0 and amount1 == 0:
            if tick_current < tick_lower:
                # Fully below range: only token0 is needed
                liquidity = amount0 / (1.0 / sqrt_pa - 1.0 / sqrt_pb)
                calc_amount1 = 0
            elif tick_current >= tick_upper:
                # Fully above range: only token1 is needed (impossible to provide amount0)
                liquidity = 0
                calc_amount1 = 0 
            else:
                # In range
                liquidity = amount0 / (1.0 / sqrt_p - 1.0 / sqrt_pb)
                calc_amount1 = liquidity * (sqrt_p - sqrt_pa)
            return amount0, int(calc_amount1)

        # If user only provided amount1
        elif amount1 > 0 and amount0 == 0:
            if tick_current < tick_lower:
                # Fully below: only token0 needed
                liquidity = 0
                calc_amount0 = 0
            elif tick_current >= tick_upper:
                # Fully above: only token1 needed
                liquidity = amount1 / (sqrt_pb - sqrt_pa)
                calc_amount0 = 0
            else:
                # In range
                liquidity = amount1 / (sqrt_p - sqrt_pa)
                calc_amount0 = liquidity * (1.0 / sqrt_p - 1.0 / sqrt_pb)
            return int(calc_amount0), amount1

        # Two-sided input: Calculate liquidity for both and take the minimum (safest bound)
        else:
            if tick_current < tick_lower:
                liq0 = amount0 / (1.0 / sqrt_pa - 1.0 / sqrt_pb)
                liq1 = float('inf')  # Token 1 not needed
            elif tick_current >= tick_upper:
                liq0 = float('inf')  # Token 0 not needed
                liq1 = amount1 / (sqrt_pb - sqrt_pa)
            else:
                liq0 = amount0 / (1.0 / sqrt_p - 1.0 / sqrt_pb)
                liq1 = amount1 / (sqrt_p - sqrt_pa)
                
            liquidity = min(liq0, liq1)
            
            # Recalculate optimal amounts based on the limiting liquidity
            if tick_current < tick_lower:
                calc_amount0 = liquidity * (1.0 / sqrt_pa - 1.0 / sqrt_pb)
                calc_amount1 = 0
            elif tick_current >= tick_upper:
                calc_amount0 = 0
                calc_amount1 = liquidity * (sqrt_pb - sqrt_pa)
            else:
                calc_amount0 = liquidity * (1.0 / sqrt_p - 1.0 / sqrt_pb)
                calc_amount1 = liquidity * (sqrt_p - sqrt_pa)

            return int(calc_amount0), int(calc_amount1)

    def add_liquidity(self, token0: str, token1: str, fee: int, tick_lower: int, tick_upper: int, amount0: float, amount1: float, dry_run: bool = False) -> str:
        """
        Add liquidity to a V2 Pool (creates a new NFT position).

        HBAR HANDLING:
          WHBAR is a routing mechanism, not a user-facing asset.
          When HBAR is one of the tokens, we pass the native tinybar
          amount as `hbar_value_raw` to V2LiquidityManager, which
          uses multicall + refundETH and the Hedera-scaled tx `value`.
          We do NOT manually call WHBAR.deposit() beforehand.
        """
        t0_id = self.resolve_token_id(token0.upper())
        t1_id = self.resolve_token_id(token1.upper())
        if not t0_id or not t1_id:
            raise PacmanError("Invalid token symbols or IDs.")


        t0_decimals = self.executor._get_token_decimals(t0_id)
        t1_decimals = self.executor._get_token_decimals(t1_id)

        raw0 = int(float(amount0) * 10 ** t0_decimals)
        raw1 = int(float(amount1) * 10 ** t1_decimals)

        # Lookup LIVE current tick for the pool to derive optimal amounts.
        # CRITICAL: Native HBAR (0.0.0) is stored as WHBAR in pool data and contract.
        WHBAR_ID = self.liquidity_manager.whbar_id
        _lookup_id0 = WHBAR_ID if t0_id == "0.0.0" else t0_id
        _lookup_id1 = WHBAR_ID if t1_id == "0.0.0" else t1_id
        pool_tick = 0
        try:
            from lib.saucerswap import get_pool_address, POOL_ABI
            pool_addr = get_pool_address(self.executor.w3, _lookup_id0, _lookup_id1, fee, self.network)
            pool_contract = self.executor.w3.eth.contract(address=pool_addr, abi=POOL_ABI)
            pool_tick = pool_contract.functions.slot0().call()[1]
            logger.info(f"Live pool tick from chain: {pool_tick}")
        except Exception as e:
            logger.warning(f"Chain slot0 fallback: {e}")
            try:
                import json
                from pathlib import Path
                raw_path = Path("data/pacman_data_raw.json")
                if raw_path.exists():
                    pools = json.load(open(raw_path))
                    for p in pools:
                        pool_ids = {p.get("tokenA", {}).get("id"), p.get("tokenB", {}).get("id")}
                        if pool_ids == {_lookup_id0, _lookup_id1} and p.get("fee") == fee:
                            pool_tick = p.get("tickCurrent", 0)
                            break
            except Exception:
                pass


        opt_raw0, opt_raw1 = self._calculate_v2_amounts(pool_tick, tick_lower, tick_upper, raw0, raw1)
        
        # IMPORTANT: For new V3 positions, always use 0 for amountMin.
        # Any non-zero amountMin against a live pool will fail with 'Price slippage check'
        # if the pool tick has moved even slightly between quote and execution.
        amount0_min = 0
        amount1_min = 0

        is_native0 = (t0_id == "0.0.0")
        is_native1 = (t1_id == "0.0.0")
        WHBAR_ID = self.liquidity_manager.whbar_id

        # Replace the internal token ID with WHBAR for path purposes
        if is_native0:
            t0_id = WHBAR_ID
        if is_native1:
            t1_id = WHBAR_ID

        # Add configurable padding to the auto-derived amounts to act as a buffer for EVM 256-bit fixed point truncation differences.
        # This prevents 'MF' (EVM math needs fractions more than python float provided).
        # We MUST NOT pad the anchor side, otherwise the EVM will try to pull more tokens than the user intended/holds.
        # Plan: Use 2% buffer as per documentation recommendation for one-sided deposits.
        padding_multiplier = 1.02 
        if raw0 == 0 and raw1 > 0:
            opt_raw0 = max(1, int(opt_raw0 * padding_multiplier))
        elif raw1 == 0 and raw0 > 0:
            opt_raw1 = max(1, int(opt_raw1 * padding_multiplier))

        # MINT FEE: ~0.5 HBAR (50,000,000 tinybar). Required by SaucerSwap V2 Factory.
        MINT_FEE = 50_000_000 
        hbar_value_raw = MINT_FEE
        if is_native0:
            hbar_value_raw += opt_raw0
        elif is_native1:
            hbar_value_raw += opt_raw1
            
        # Only approve the non-HBAR side (HBAR goes as tx value, not ERC20)
        # NB: _ensure_lp_approval is self-contained in v2_liquidity.py — does NOT touch swap engine
        # Approval must happen BEFORE the simulation (dry_run) too so the allowance is set
        logger.info(f"Approving tokens for PositionManager...")
        if not is_native0:
            self.liquidity_manager._ensure_lp_approval(t0_id, opt_raw0)
        if not is_native1:
            self.liquidity_manager._ensure_lp_approval(t1_id, opt_raw1)

        # Ensure NFT Association before Minting
        # EVM V3 Minting reverts with TB:FT if the recipient hasn't associated the LP NFT token ID
        nft_token_id = "0.0.4054027" if self.network == "mainnet" else "0.0.4054027"
        if not self.executor.check_token_association(nft_token_id):
            logger.info(f"   ⚠️  LP NFT {nft_token_id} not associated. Attempting auto-association...")
            if not self.executor.associate_token(nft_token_id):
                raise RuntimeError(f"Failed to auto-associate LP NFT {nft_token_id}. Minting will fail.")

        logger.info(f"Minting position for {t0_id}/{t1_id}...")
        return self.liquidity_manager.add_liquidity(
            token0_id=t0_id, token1_id=t1_id, fee=fee,
            tick_lower=tick_lower, tick_upper=tick_upper,
            amount0_desired=opt_raw0, amount1_desired=opt_raw1,
            amount0_min=amount0_min, amount1_min=amount1_min,
            hbar_value_raw=hbar_value_raw,
            dry_run=dry_run,
        )

    def remove_liquidity(self, token_id: int, liquidity: int, dry_run: bool = False) -> list[str]:
        """Remove liquidity and collect tokens."""
        logger.info(f"Removing liquidity for Position {token_id}...")
        return self.liquidity_manager.remove_liquidity(
            token_id=int(token_id),
            liquidity=int(liquidity),
            dry_run=dry_run
        )





    def approve_pool(self, pool_data: dict, protocol: str = "v2"):
        """
        Add a pool to the local approved registry.
        """
        import json
        from pathlib import Path
        
        protocol = protocol.lower()
        reg_file = "data/pools_v2.json" if protocol == "v2" else "data/pools_v1.json"
        reg_path = Path(reg_file)
        
        # 1. Load existing
        registry = []
        if reg_path.exists():
            with open(reg_path) as f:
                registry = json.load(f)
                
        # 2. Check if already exists
        pool_id = pool_data.get("contractId")
        if any(p.get("contractId") == pool_id for p in registry):
            logger.info(f"Pool {pool_id} already in {protocol} registry.")
            # Still sync tokens in case they are missing from tokens.json
            self._sync_pool_tokens(pool_data)
            return False

        # 3. Convert format if needed
        # Expected: {contractId, tokenA, tokenB, fee, label}
        fee = pool_data.get("fee")
        if protocol == "v1" and fee is None:
            fee = 3000 # Default V1 fee
        tokenA_meta = pool_data.get("tokenA", {})
        tokenB_meta = pool_data.get("tokenB", {})
        
        symA = tokenA_meta.get("symbol") if isinstance(tokenA_meta, dict) else None
        symB = tokenB_meta.get("symbol") if isinstance(tokenB_meta, dict) else None
        idA = tokenA_meta.get("id") if isinstance(tokenA_meta, dict) else tokenA_meta
        idB = tokenB_meta.get("id") if isinstance(tokenB_meta, dict) else tokenB_meta

        # Fallback symbol resolution from tokens.json
        if not symA or not symB:
            try:
                tokens_path = Path("data/tokens.json")
                if tokens_path.exists():
                    with open(tokens_path) as f:
                        tokens = json.load(f)
                        if not symA: symA = tokens.get(idA, {}).get("symbol")
                        if not symB: symB = tokens.get(idB, {}).get("symbol")
            except Exception:
                pass

        label = pool_data.get("label")
        if not label:
            label = f"{symA or idA}/{symB or idB}"

        entry = {
            "contractId": pool_id,
            "tokenA": idA,
            "tokenB": idB,
            "fee": fee,
            "label": label
        }
        
        registry.append(entry)
        
        # 4. Save
        with open(reg_path, "w") as f:
            json.dump(registry, f, indent=4)
        
        # 5. Sync tokens to main registry
        self._sync_pool_tokens(pool_data)

        logger.info(f"Approved {protocol} pool: {entry['label']} ({pool_id})")
        self.router.load_pools() # Reload graph
        return True

    def _sync_pool_tokens(self, pool_data: dict):
        """Extract tokens from pool data and add to tokens.json if missing."""
        import json
        from pathlib import Path
        
        tokens_path = Path("data/tokens.json")
        if not tokens_path.exists():
            return
            
        try:
            with open(tokens_path) as f:
                tokens = json.load(f)
                
            updated = False
            for key in ["tokenA", "tokenB"]:
                t = pool_data.get(key)
                if not isinstance(t, dict): continue
                
                tid = t.get("id")
                symbol = t.get("symbol")
                if not tid or not symbol: continue
                
                # Check if ID already exists under any key
                exists = any(meta.get("id") == tid for meta in tokens.values())
                if not exists:
                    # Add to registry
                    tokens[symbol] = {
                        "id": tid,
                        "decimals": t.get("decimals", 8),
                        "symbol": symbol,
                        "name": t.get("name", symbol)
                    }
                    updated = True
                    logger.info(f"Sync: Added new token {symbol} ({tid}) to registry.")
                    
            if updated:
                with open(tokens_path, "w") as f:
                    json.dump(tokens, f, indent=2)
        except Exception as e:
            logger.debug(f"Token sync failed: {e}")

    def remove_pool(self, pool_id: str, protocol: str = "v2"):
        """
        Remove a pool from the local approved registry.
        """
        import json
        from pathlib import Path
        
        protocol = protocol.lower()
        reg_file = "data/pools_v2.json" if protocol == "v2" else "data/pools_v1.json"
        reg_path = Path(reg_file)
        
        if not reg_path.exists():
            return False
            
        with open(reg_path) as f:
            registry = json.load(f)
            
        new_registry = [p for p in registry if p.get("contractId") != pool_id]
        
        if len(new_registry) == len(registry):
            return False
            
        with open(reg_path, "w") as f:
            json.dump(new_registry, f, indent=4)
            
        logger.info(f"Removed {protocol} pool: {pool_id}")
        self.router.load_pools() # Reload graph
        return True

    def is_v1_only(self, symbol_in: str, symbol_out: str) -> bool:
        """
        Check if a pair only exists in the approved V1 registry.
        Returns True if the pair is in V1 AND either token is not in V2.
        """
        import json
        from pathlib import Path
        
        symbol_in = symbol_in.upper()
        symbol_out = symbol_out.upper()
        
        # 1. Load V1
        v1_reg_path = Path("data/pools_v1.json")
        if not v1_reg_path.exists():
            return False
            
        try:
            with open(v1_reg_path) as f:
                v1_reg = json.load(f)
                
            in_v1 = False
            for p in v1_reg:
                label = p.get("label", "").upper()
                if symbol_in in label and symbol_out in label:
                    in_v1 = True
                    break
            
            if not in_v1:
                return False
                
            # 2. Check if either is completely missing from V2 pools
            # Note: Native HBAR and major stables are guaranteed to be in V2 
            # if the registry is healthy, but we check specifically for community tokens.
            if symbol_in in ["HBAR", "0.0.0", "WHBAR", "USDC", "USDT"] and \
               symbol_out in ["HBAR", "0.0.0", "WHBAR", "USDC", "USDT"]:
                return False # Top pairs always have V2

            v2_reg_path = Path("data/pools_v2.json")
            if not v2_reg_path.exists():
                return True # No V2 registry means it's V1-only by default if it was in V1
                
            with open(v2_reg_path) as f2:
                v2_reg = json.load(f2)
                # Check tokens in V2 - symbols are often in the tokenA/tokenB symbol field in pools.json
                # But router.py's pool_graph is the true source.
                # However, for a simple hint, checking the pool metadata symbols is enough.
                in_v2_in = any(p.get("tokenA", {}).get("symbol") == symbol_in or p.get("tokenB", {}).get("symbol") == symbol_in for p in v2_reg)
                in_v2_out = any(p.get("tokenA", {}).get("symbol") == symbol_out or p.get("tokenB", {}).get("symbol") == symbol_out for p in v2_reg)
                
                return not (in_v2_in and in_v2_out)

        except Exception as e:
            logger.debug(f"is_v1_only check failed: {e}")
            return False

    # ---------------------------------------------------------------------------
    # Whitelist Management
    # ---------------------------------------------------------------------------

    def get_whitelist(self) -> list:
        """Get the list of whitelisted transfer recipients as [{address, nickname}]."""
        import json
        try:
            with open("data/settings.json") as f:
                settings = json.load(f)
            raw = settings.get("transfer_whitelist", [])
            # Migrate bare strings to dicts transparently
            result = []
            for entry in raw:
                if isinstance(entry, str):
                    result.append({"address": entry, "nickname": ""})
                elif isinstance(entry, dict):
                    result.append(entry)
            return result
        except Exception:
            return []

    def add_to_whitelist(self, address: str, nickname: str = "") -> bool:
        """Add an address (with optional nickname) to the transfer whitelist."""
        import json
        import re
        from pathlib import Path

        if not re.match(r"^0\.0\.\d+$", address):
            logger.error(f"Invalid Hedera ID format: {address}")
            return False

        settings_path = Path("data/settings.json")
        if not settings_path.exists():
            return False

        try:
            with open(settings_path) as f:
                settings = json.load(f)

            raw = settings.get("transfer_whitelist", [])
            # Migrate bare strings
            whitelist = [
                e if isinstance(e, dict) else {"address": e, "nickname": ""}
                for e in raw
            ]

            # Duplicate check
            if any(e["address"] == address for e in whitelist):
                logger.info(f"Address {address} already in whitelist.")
                return True

            whitelist.append({"address": address, "nickname": nickname.strip()})
            settings["transfer_whitelist"] = whitelist

            with open(settings_path, "w") as f:
                json.dump(settings, f, indent=4)

            logger.info(f"Added {address} ('{nickname}') to whitelist.")
            return True
        except Exception as e:
            logger.error(f"Failed to update whitelist: {e}")
            return False

    def remove_from_whitelist(self, address: str) -> bool:
        """Remove an address from the transfer whitelist."""
        import json
        from pathlib import Path

        settings_path = Path("data/settings.json")
        if not settings_path.exists():
            return False

        try:
            with open(settings_path) as f:
                settings = json.load(f)

            raw = settings.get("transfer_whitelist", [])
            # Migrate bare strings then filter
            whitelist = [
                e if isinstance(e, dict) else {"address": e, "nickname": ""}
                for e in raw
            ]
            new_whitelist = [e for e in whitelist if e["address"] != address]

            if len(new_whitelist) == len(whitelist):
                logger.info(f"Address {address} not in whitelist.")
                return False

            settings["transfer_whitelist"] = new_whitelist
            with open(settings_path, "w") as f:
                json.dump(settings, f, indent=4)

            logger.info(f"Removed {address} from whitelist.")
            return True
        except Exception as e:
            logger.error(f"Failed to update whitelist: {e}")
            return False
    def get_liquidity_positions(self) -> list:
        """Fetch NFT IDs of LP tokens for this account with full position details via Mirror Node."""
        if not self.account_id or self.account_id.lower() in ["unknown", "none"]: return []
        network_prefix = "mainnet-public" if self.network == "mainnet" else "testnet"
        nft_token_id = "0.0.4054027"
        url = f"https://{network_prefix}.mirrornode.hedera.com/api/v1/accounts/{self.account_id}/nfts?token.id={nft_token_id}"
        
        positions = []
        try:
            import requests
            from web3 import Web3
            from eth_abi import decode as abi_decode
            from lib.saucerswap import hedera_id_to_evm

            res = requests.get(url, timeout=10)
            if res.status_code == 200:
                data = res.json().get("nfts", [])
                for nft in data:
                    serial = int(nft.get("serial_number"))
                    
                    # Manual decode to handle specific SaucerSwap V2 return length (320 bytes = 10 fields)
                    
                    # Correct selector for positions(uint256) -> 0x99fbab88
                    selector = "0x99fbab88"
                    call_data = selector + hex(serial)[2:].zfill(64)
                    
                    raw_res = self.executor.w3.eth.call({
                        "to": self.liquidity_manager.contract.address,
                        "data": call_data
                    })
                    
                    # SaucerSwap V2 NFPM returns 320 bytes (10 fields of 32 bytes)
                    if len(raw_res) >= 320:
                        clean_res = raw_res[:320]
                        # Struct Layout: [t0, t1, fee, tickL, tickU, liq, feeG0, feeG1, owed0, owed1]
                        pos_types = ['address', 'address', 'uint24', 'int24', 'int24', 'uint128', 'uint256', 'uint256', 'uint128', 'uint128']
                        pos_data = abi_decode(pos_types, clean_res)

                        liquidity = pos_data[5]
                        if liquidity > 0:
                            t0_addr = Web3.to_checksum_address(pos_data[0])
                            t1_addr = Web3.to_checksum_address(pos_data[1])
                            fee = pos_data[2]
                            tick_lower = pos_data[3]
                            tick_upper = pos_data[4]

                            # Try to fetch current tick from the pool
                            tick_current = tick_lower
                            try:
                                from lib.saucerswap import get_pool_address, POOL_ABI
                                t0_num = int(t0_addr.lower(), 16)
                                t1_num = int(t1_addr.lower(), 16)
                                t0_id = f"0.0.{t0_num}"
                                t1_id = f"0.0.{t1_num}"
                                pool_addr = get_pool_address(self.executor.w3, t0_id, t1_id, fee, self.network)
                                pool_contract = self.executor.w3.eth.contract(address=pool_addr, abi=POOL_ABI)
                                slot0 = pool_contract.functions.slot0().call()
                                tick_current = slot0[1]
                            except Exception:
                                pass

                            positions.append({
                                "id": serial,
                                "token0": t0_addr,
                                "token1": t1_addr,
                                "fee": fee,
                                "liquidity": liquidity,
                                "tick_lower": tick_lower,
                                "tick_upper": tick_upper,
                                "tick_current": tick_current,
                            })
            else:
                logger.warning(f"Mirror node NFT query failed with {res.status_code}: {res.text}")
        except Exception as e:
            logger.error(f"Failed to fetch LP positions: {e}")
        return positions
