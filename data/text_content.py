"""
Pacman Text Resources
=====================

Central repository for static text, help menus, and user messages.
Keeps display logic clean and focused on rendering.
"""
# Note: Uses placeholders {ACCENT}, {CHROME}, etc. for formatting
PACMAN_BANNER_TEMPLATE = """{ACCENT}
    ██████╗  █████╗  ██████╗███╗   ███╗ █████╗ ███╗   ██╗
    ██╔══██╗██╔══██╗██╔════╝████╗ ████║██╔══██╗████╗  ██║
    ██████╔╝███████║██║     ██╔████╔██║███████║██╔██╗ ██║
    ██╔═══╝ ██╔══██║██║     ██║╚██╔╝██║██╔══██║██║╚██╗██║
    ██║     ██║  ██║╚██████╗██║ ╚═╝ ██║██║  ██║██║ ╚████║
    ╚═╝     ╚═╝  ╚═╝ ╚═════╝╚═╝     ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝{R}

{CHROME}    ╭──────────────────────────────────────────────────────╮{R}
{ACCENT}     ᗧ{R}{MUTED}· · ·{R}{OK} 👾{R}  {TEXT}SaucerSwap V2{R} {MUTED}on{R} {BRAND}Hedera{R} {MUTED}Hashgraph{R}
{CHROME}    ╰──────────────────────────────────────────────────────╯{R}"""

HELP_COMMANDS = [
    # Wallet
    ("--- WALLET & SETUP ---", ""),
    ("setup",                    "Secure wallet configuration"),
    ("account",                  "Wallet & network info"),
    ("balance",                  "All wallet balances"),
    ("balance <token>",          "Single token balance"),

    # Swaps
    ("--- SWAPPING ---", ""),
    ("swap <amt> <A> for <B>",   "Exact input swap"),
    ("swap <A> for <amt> <B>",   "Exact output swap"),
    ("swap-v1 <amt> <A> <B>",    "SaucerSwap V1 (Legacy) swap"),

    # Transfers
    ("--- TRANSFERS ---", ""),
    ("send <amt> <tk> to <rcp>", "Transfer crypto"),
    ("receive <token>",          "Get addr & associate"),
    ("whitelist [view|add|rm]",  "Manage trusted addresses"),

    # Staking
    ("--- STAKING ---", ""),
    ("stake [node_id]",          "Stake HBAR (default: Google node 5)"),
    ("unstake",                  "Stop earning rewards"),

    # Tools
    ("--- MARKET DATA ---", ""),
    ("tokens",                   "Supported token list"),
    ("pools",                    "Manage pool registries"),
    ("price",                    "List all market prices"),
    ("price <token>",            "Check single price"),
    ("history",                  "Transaction history"),
    ("sources",                  "Show all price sources"),

    # System
    ("--- SYSTEM ---", ""),
    ("verbose",                  "Toggle debug logging"),
    ("help <topic>",             "Deep dive (swap/send/nlp/stake/pools/whitelist)"),
    ("exit",                     "Quit Pacman"),
]

HELP_EXAMPLES = [
    ("swap 100 HBAR for USDC",    "Swap ~100 HBAR to USDC"),
    ("swap HBAR for 10 USDC",     "Swap enough HBAR to get 10 USDC"),
    ("swap 100 USDC for HBAR",    "Swap 100 USDC to HBAR"),
    ("send 100 USDC to 0.0.1234", "Send token to external account"),
    ("balance SAUCE",             "Check SAUCE balance"),
]

# --- IN-DEPTH EXPLAINERS ---
# These are shown when a user types "help <topic>"

HELP_EXPLAINERS = {
    "nlp": """{C.BOLD}NATURAL LANGUAGE RULES{C.R}
{C.CHROME}────────────────────────────────────────────────────────{C.R}
Pacman interprets your intent using fuzzy logic and regex.
Follow these rules for the best results:

{C.ACCENT}1. No Symbols ($ / ,){C.R}
   Use {C.TEXT}100.50{C.R} instead of {C.TEXT}$100.50{C.R} or {C.TEXT}1,000{C.R}.
   Symbols can confuse the parser during token resolution.

{C.ACCENT}2. Token Aliases{C.R}
   You can use symbols ({C.TEXT}HBAR{C.R}), common names ({C.TEXT}Bitcoin{C.R}), 
   or variant keys ({C.TEXT}WBTC_HTS{C.R}). Pacman ignores casing and 
   handles hyphens vs underscores (e.g., {C.TEXT}HTS-WBTC{C.R} works).
   
   Check {C.TEXT}data/aliases.json{C.R} for supported nicknames.

{C.ACCENT}3. Intent Detection{C.R}
   - {C.BOLD}Exact In{C.R}:  "swap {C.OK}10{C.R} A for B" (You spend exactly 10 A)
   - {C.BOLD}Exact Out{C.R}: "swap A for {C.OK}10{C.R} B" (You get exactly 10 B)
   - {C.BOLD}Buy Mode{C.R}:  "buy 10 B with A" (Exact Output mode)
   
{C.ACCENT}4. Token Variants (IMPORTANT){C.R}
   Hedera has TWO versions of bridged tokens:
   - {C.TEXT}WBTC_HTS{C.R}  = HTS-native  (visible in HashPack)
   - {C.TEXT}WBTC_LZ{C.R}   = ERC20       (invisible in HashPack)
   
   Using plain "WBTC" lets Pacman decide the best variant.
   Use the explicit key to force a specific output format.
   Type {C.TEXT}tokens{C.R} to see all supported variants.""",

    "swap": """{C.BOLD}SWAPPING ASSETS{C.R}
{C.CHROME}────────────────────────────────────────────────────────{C.R}
Pacman finds the most efficient path through the SaucerSwap 
V2 Liquidity Graph.

{C.ACCENT}Usage examples:{C.R}
  {C.TEXT}ᗧ swap 10 HBAR for USDC{C.R}   (Exact Input)
  {C.TEXT}ᗧ swap HBAR for 10 USDC{C.R}   (Exact Output)

{C.ACCENT}Smart Routing:{C.R}
  Pacman will automatically route through intermediate pools 
  (e.g., WBTC → HBAR → USDC) to find the best rate. It also 
  handles HTS associations automatically before execution.""",

    "send": """{C.BOLD}TRANSFERRING ASSETS{C.R}
{C.CHROME}────────────────────────────────────────────────────────{C.R}
Send HBAR or any supported HTS token to any Hedera account.

{C.ACCENT}Usage example:{C.R}
  {C.TEXT}ᗧ send 100 USDC to 0.0.123456{C.R}

{C.ACCENT}Validation:{C.R}
  Pacman verifies your balance and simulations the transfer 
  on-chain before broadcasting to ensure it won't revert 
  due to lack of association on the recipient's end.""",

    "balance": """{C.BOLD}PORTFOLIO & BALANCES{C.R}
{C.CHROME}────────────────────────────────────────────────────────{C.R}
Check your current holdings and their USD valuations.

{C.ACCENT}Usage examples:{C.R}
  {C.TEXT}ᗧ balance{C.R}        (Show all major holdings)
  {C.TEXT}ᗧ balance SAUCE{C.R}  (Deep-dive into one token)

{C.ACCENT}Valuation Logic:{C.R}
  Prices are live-synced from SaucerSwap V2. Small tiny 
  dust balances are hidden by default to keep the UI clean.""",

    "price": """{C.BOLD}PRICE DISCOVERY{C.R}
{C.CHROME}────────────────────────────────────────────────────────{C.R}
Get real-time market rates and spread data.

{C.ACCENT}Usage examples:{C.R}
  {C.TEXT}ᗧ price{C.R}        (Summary of all tokens)
  {C.TEXT}ᗧ price WBTC{C.R}   (Detailed routing metrics)

{C.ACCENT}Sources:{C.R}
  1. Primary: SaucerSwap V2 Liquidity Pools
  2. Fallback: CoinGecko API / Binance
  3. Network: Hedera Mainnet / Testnet""",

    "pools": """{C.BOLD}POOL REGISTRY MANAGEMENT{C.R}
{C.CHROME}────────────────────────────────────────────────────────{C.R}
Pacman allows you to surgically manage which liquidity pools 
are used for routing.

{C.ACCENT}Sub-Commands:{C.R}
  {C.TEXT}list{C.R}             Show all currently approved pools.
  {C.TEXT}search <q>{C.R}      Find pools on-chain (Symbol or ID).
  {C.TEXT}approve <id>{C.R}   Add a pool to your trading registry.
  {C.TEXT}delete <id>{C.R}    Remove a pool from your registry.

{C.ACCENT}Protocol Toggles:{C.R}
  Use {C.TEXT}--v1{C.R} or {C.TEXT}--v2{C.R} to filter your search. V2 is default.

{C.ACCENT}Why manage pools?{C.R}
  By "approving" a pool, you whitelist it for the routing engine.
  This allows you to access new pairs instantly or strip out 
  low-liquidity pools that might cause high slippage.""",

    "account": """{C.BOLD}WALLET & NETWORK INFO{C.R}
{C.CHROME}────────────────────────────────────────────────────────{C.R}
View your current Hedera Account ID, EVM address, and 
connected network status.

{C.ACCENT}Sub-account Management:{C.R}
  Pacman allows you to create multiple Account IDs (0.0.xxx) 
  that share the same Private Key. This is a native Hedera 
  feature for organizational and privacy purposes.""",

    "setup": """{C.BOLD}SECURE WALLET CONFIGURATION{C.R}
{C.CHROME}────────────────────────────────────────────────────────{C.R}
Guide to configuring your Hedera credentials safely.

{C.ACCENT}Command:{C.R}
  {C.TEXT}ᗧ setup{C.R}

{C.ACCENT}Process:{C.R}
  1. {C.BOLD}Setup Mode{C.R}: Choose between [P] Paste Key or [C] Create New.
  2. {C.BOLD}Auto-Discovery{C.R}: Pacman automatically finds your Hedera ID.
  3. {C.BOLD}Secure Save{C.R}: Credentials are saved masked to your .env.

{C.ACCENT}Sub-accounts:{C.R}
  Use the {C.TEXT}account{C.R} command to manage sub-accounts or create 
  new IDs sharing your existing key.""",

    "swap-v1": """{C.BOLD}V1 (LEGACY) SWAPS{C.R}
{C.CHROME}────────────────────────────────────────────────────────{C.R}
Execute swaps specifically on SaucerSwap V1 (Uniswap V2) 
liquidity pools. 

This command is strictly decoupled from the main engine.

{C.ACCENT}Usage example:{C.R}
  {C.TEXT}ᗧ swap-v1 100 HBAR DOSA{C.R}

{C.ACCENT}Why use V1?{C.R}
  Certain community tokens (like DOSA) only have liquidity 
  in legacy V1 pools. This command gives you direct access 
  without affecting the stability of the V2 routing engine.""",

    "whitelist": """{C.BOLD}WHITELIST MANAGEMENT{C.R}
{C.CHROME}────────────────────────────────────────────────────────{C.R}
Manage your trusted recipient list for enhanced security.
Live transfers are BLOCKED unless the address is whitelisted.

{C.ACCENT}Commands:{C.R}
  {C.TEXT}view{C.R}               List all approved addresses.
  {C.TEXT}add <0.0.xxx>{C.R}      Add a new trusted address.
  {C.TEXT}remove <0.0.xxx>{C.R}   Remove an address.

{C.ACCENT}Note:{C.R}
  Direct EVM transfers (0x...) are currently blocked by default 
  in live mode. Use Hedera IDs (0.0.xxx) for maximum safety.""",

    "stake": """{C.BOLD}HEDERA STAKING (HIP-406){C.R}
{C.CHROME}────────────────────────────────────────────────────────{C.R}
Stake your HBAR balance to a consensus node to earn rewards.

{C.ACCENT}Commands:{C.R}
  {C.TEXT}ᗧ stake{C.R}           Stake to Google Node (5) — default
  {C.TEXT}ᗧ stake <node_id>{C.R} Stake to a specific node (0–28)
  {C.TEXT}ᗧ unstake{C.R}         Stop staking

{C.ACCENT}Details:{C.R}
  - Staking is {C.BOLD}non-custodial{C.R}: funds remain 100% liquid.
  - Rewards are issued daily by the Hedera network (~1% APY).
  - First reward payment arrives ~24h after staking.
  - Node 5 (Google) is the recommended default.

{C.ACCENT}How it works:{C.R}
  Uses a native {C.TEXT}CryptoUpdate{C.R} transaction (HIP-406) via the 
  Hiero SDK. Does NOT lock or move your funds.""",

    "history": """{C.BOLD}TRANSACTION HISTORY{C.R}
{C.CHROME}────────────────────────────────────────────────────────{C.R}
View your recent on-chain activity log.

{C.ACCENT}Command:{C.R}
  {C.TEXT}ᗧ history{C.R}

{C.ACCENT}Data stored:{C.R}
  Each execution is saved as a JSON file in {C.TEXT}execution_records/{C.R}.
  History shows: Swaps, Transfers, Staking events.

{C.ACCENT}Training data:{C.R}
  Executions are also appended to {C.TEXT}training_data/live_executions.jsonl{C.R}
  for use in AI model fine-tuning.""",
}

