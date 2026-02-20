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
    ("setup",                    "Secure wallet configuration wizard"),
    ("account",                  "View wallet info & network status"),
    ("account --new",            "Create a new sub-account (same key)"),
    ("account rename <id> <n>",  "Set a nickname for any known account"),
    ("balance",                  "All wallet balances + USD value"),
    ("balance <token>",          "Single token balance"),

    # Swaps
    ("--- SWAPPING ---", ""),
    ("swap <amt> <A> for <B>",   "Exact input swap (you spend exact amount)"),
    ("swap <A> for <amt> <B>",   "Exact output swap (you receive exact amount)"),
    ("swap-v1 <amt> <A> <B>",    "SaucerSwap V1 (Legacy) swap"),

    # Transfers
    ("--- TRANSFERS ---", ""),
    ("send <amt> <tk> to <rcp>", "Transfer crypto to a Hedera account"),
    ("receive [<token>]",        "Get your address & check token association"),
    ("whitelist",                "View trusted send addresses"),
    ("whitelist add <addr> [nick]","Whitelist an address with optional nickname"),
    ("whitelist remove <addr>",  "Remove an address from whitelist"),

    # Staking
    ("--- STAKING ---", ""),
    ("stake [node_id]",          "Stake HBAR (default: Google node 5)"),
    ("unstake",                  "Stop staking & clear node preference"),

    # Market Data
    ("--- MARKET DATA ---", ""),
    ("tokens",                   "Supported token list with IDs & aliases"),
    ("pools",                    "Pool registry management (list/search/approve)"),
    ("price",                    "All market prices from SaucerSwap V2"),
    ("price <token>",            "Single token price + source"),
    ("history",                  "Transaction history (swaps, transfers, staking)"),
    ("sources",                  "Show all price data sources"),

    # System
    ("--- SYSTEM ---", ""),
    ("verbose [on/off]",         "Toggle debug logging"),
    ("help <topic>",             "Deep dive: swap|send|nlp|stake|pools|whitelist|account|balance|price"),
    ("exit",                     "Quit Pacman"),
]

HELP_EXAMPLES = [
    ("swap 100 HBAR for USDC",       "Spend exactly 100 HBAR, get as much USDC as possible"),
    ("swap HBAR for 10 USDC",        "Get exactly 10 USDC, spend minimum HBAR"),
    ("swap 100 USDC for HBAR",       "Spend 100 USDC, receive HBAR"),
    ("swap 0.001 WBTC for HBAR",     "Swap wrapped Bitcoin HTS token for HBAR"),
    ("send 100 USDC to 0.0.1234",    "Transfer USDC to another Hedera account"),
    ("send 5 HBAR to 0.0.9876 memo Rent",   "Transfer HBAR with an on-chain memo"),
    ("balance SAUCE",                "Check SAUCE token balance"),
    ("price WBTC",                   "Get WBTC price from SaucerSwap"),
    ("stake 5",                      "Stake to consensus node 5 (Google)"),
    ("whitelist add 0.0.1234 Exchange", "Whitelist an address with a label"),
    ("account --new",                "Create a sub-account using your current key"),
    ("pools search HBAR",            "Find pools containing HBAR"),
    ("pools approve 0.0.123456",     "Add a pool to your routing registry"),
]

# ---------------------------------------------------------------------------
# IN-DEPTH EXPLAINERS (shown by `help <topic>`)
# ---------------------------------------------------------------------------
# These are designed to be consumed by BOTH:
#   - Human users interactively typing `help swap`
#   - AI agents reading the CLI output to understand how to operate the tool
# ---------------------------------------------------------------------------

HELP_EXPLAINERS = {

    "nlp": """{C.BOLD}NATURAL LANGUAGE INTERFACE{C.R}
{C.CHROME}────────────────────────────────────────────────────────{C.R}
Pacman interprets freeform text using fuzzy pattern matching.
You do NOT need to use exact command syntax for swaps.

{C.ACCENT}Supported Intent Patterns:{C.R}
  "swap 10 HBAR for USDC"        → Exact Input swap
  "buy 50 SAUCE with HBAR"       → Exact Output swap (you get 50 SAUCE)
  "sell 100 USDC for HBAR"       → Exact Input swap
  "exchange 5 HBAR to WBTC"      → Exact Input swap

{C.ACCENT}Token Name Resolution:{C.R}
  - Symbols:    {C.TEXT}HBAR, USDC, WBTC{C.R}
  - Common names: {C.TEXT}Bitcoin, Ethereum, Hedera{C.R}
  - Variants:   {C.TEXT}WBTC_HTS, WBTC_LZ, WETH_HTS{C.R}
  - Nicknames:  {C.TEXT}btc, eth, sauce, usdc{C.R} (see data/aliases.json)
  Pacman is case-insensitive and handles hyphens vs underscores.

{C.ACCENT}Amount Rules:{C.R}
  - Write numbers without symbols: {C.TEXT}100.50{C.R} not {C.TEXT}$100.50{C.R}
  - No commas: {C.TEXT}1000{C.R} not {C.TEXT}1,000{C.R}
  - Decimal precision is preserved

{C.ACCENT}Intent Detection Logic:{C.R}
  Exact In:  Number is BEFORE the from-token  → "swap {C.OK}10{C.R} HBAR for USDC"
  Exact Out: Number is BEFORE the to-token    → "swap HBAR for {C.OK}10{C.R} USDC"
  Buy Mode:  "buy {C.OK}N{C.R} TOKEN with ..."  → always Exact Output

{C.ACCENT}Token Variants (IMPORTANT for AI Agents):{C.R}
  HTS tokens and their ERC20 counterparts have different IDs:
    {C.TEXT}WBTC_HTS{C.R}  = HTS-native (0.0.624505) — shows in HashPack wallet
    {C.TEXT}WBTC_LZ{C.R}   = LayerZero ERC20 — invisible in HashPack
  Use plain {C.TEXT}WBTC{C.R} and Pacman picks the best variant automatically.
  Run {C.TEXT}tokens{C.R} to see all supported variants and their contract IDs.""",

    "swap": """{C.BOLD}SWAPPING ASSETS — COMPLETE REFERENCE{C.R}
{C.CHROME}────────────────────────────────────────────────────────{C.R}
Pacman routes through the SaucerSwap V2 liquidity graph to find
the most efficient path between any two supported tokens.

{C.ACCENT}Command Syntax:{C.R}
  {C.TEXT}swap <amount> <FROM> for <TO>{C.R}   — Exact Input  (spend known amount)
  {C.TEXT}swap <FROM> for <amount> <TO>{C.R}   — Exact Output (receive known amount)
  {C.TEXT}swap-v1 <amount> <FROM> <TO>{C.R}    — Force SaucerSwap V1 (legacy)

{C.ACCENT}Examples:{C.R}
  {C.TEXT}ᗧ swap 100 HBAR for USDC{C.R}       Spend exactly 100 HBAR
  {C.TEXT}ᗧ swap HBAR for 10 USDC{C.R}        Receive exactly 10 USDC
  {C.TEXT}ᗧ swap 0.001 WBTC for HBAR{C.R}     Sell Bitcoin HTS token

{C.ACCENT}Pre-Execution Safety:{C.R}
  1. {C.BOLD}Simulation{C.R}: Every swap runs eth_call simulation first.
     If it would revert, the transaction is NEVER broadcast.
  2. {C.BOLD}Slippage{C.R}: Default 1% tolerance. Multi-hop routes add ~0.5% per hop.
  3. {C.BOLD}Association{C.R}: Pacman auto-associates HTS tokens if needed.
  4. {C.BOLD}Approval{C.R}: ERC20 allowances are checked and approved before swap.

{C.ACCENT}Routing Engine:{C.R}
  - Builds a weighted graph from approved pool registries (data/pools.json)
  - Automatically multi-hops: WBTC → HBAR → USDC when no direct pool exists
  - Prefers lower-fee paths and higher-liquidity pools
  - WHBAR (0.0.1456986) is used internally; users never need to specify it

{C.ACCENT}SIMULATION MODE:{C.R}
  Set {C.TEXT}PACMAN_SIMULATE=true{C.R} in .env to test without broadcasting.
  All outputs are identical except no gas is spent and tx hash = "SIMULATED".""",

    "send": """{C.BOLD}TRANSFERRING ASSETS — COMPLETE REFERENCE{C.R}
{C.CHROME}────────────────────────────────────────────────────────{C.R}
Send HBAR or any HTS token to any Hedera account.

{C.ACCENT}Command Syntax:{C.R}
  {C.TEXT}send <amount> <token> to <recipient> [memo <message>]{C.R}

  recipient can be:
    {C.TEXT}0.0.1234567{C.R}    (Hedera Account ID — recommended)
    {C.TEXT}0x3f4d...{C.R}      (EVM alias — requires whitelist)

{C.ACCENT}Examples:{C.R}
  {C.TEXT}ᗧ send 100 USDC to 0.0.1234{C.R}
  {C.TEXT}ᗧ send 5 HBAR to 0.0.9876 memo Monthly subscription{C.R}
  {C.TEXT}ᗧ send 0.5 WBTC to 0.0.5555{C.R}

{C.ACCENT}Security Gate (Transfer Whitelist):{C.R}
  Live transfers are BLOCKED unless the recipient is whitelisted.
  This prevents accidental sends to wrong addresses.
  Add an address: {C.TEXT}whitelist add 0.0.xxx MyLabel{C.R}

{C.ACCENT}How HTS Transfers Work:{C.R}
  - HBAR: native CryptoTransfer via Hedera SDK
  - HTS tokens: CryptoTransfer with token transfer list
  - Association is checked on sender side before broadcasting
  - Recipient must be already associated (or Pacman warns you)

{C.ACCENT}Memo:{C.R}
  Memos are stored on-chain (max 100 chars). They appear in HashScan
  and are saved to your local execution_records/ log.""",

    "balance": """{C.BOLD}BALANCE & PORTFOLIO — COMPLETE REFERENCE{C.R}
{C.CHROME}────────────────────────────────────────────────────────{C.R}
Display your wallet holdings with live USD valuation.

{C.ACCENT}Commands:{C.R}
  {C.TEXT}ᗧ balance{C.R}            All non-zero token balances
  {C.TEXT}ᗧ balance <token>{C.R}    Single token deep-dive

{C.ACCENT}How Balances Are Fetched:{C.R}
  1. Multicall3 batch (fast): all token balances in one RPC call
  2. Sequential fallback: used if Multicall3 reverts
  3. HBAR balance: fetched separately via eth_getBalance (native)

{C.ACCENT}Price Sources (in order):{C.R}
  1. SaucerSwap V2 pool data (primary — from data/pacman_data_raw.json)
  2. CoinGecko API (fallback for missing tokens)
  3. Binance spot (final fallback for HBAR)

{C.ACCENT}Display Rules:{C.R}
  - WHBAR (0.0.1456986) is hidden — users see HBAR instead
  - Blacklisted tokens filtered by data/settings.json
  - Sort order controlled by wallet_balance_order in settings.json
  - Staking status shown at the top when active

{C.ACCENT}Association Indicators:{C.R}
  {C.WARN}[!]{C.R} next to a token = not yet associated. You will need to
  associate before you can receive that token.""",

    "price": """{C.BOLD}PRICE DISCOVERY — COMPLETE REFERENCE{C.R}
{C.CHROME}────────────────────────────────────────────────────────{C.R}
Fetch real-time market rates for all supported tokens.

{C.ACCENT}Commands:{C.R}
  {C.TEXT}ᗧ price{C.R}          Summary table of all token prices
  {C.TEXT}ᗧ price <token>{C.R}  Price for a specific token with source
  {C.TEXT}ᗧ sources{C.R}        Full source attribution table

{C.ACCENT}Price Source Priority:{C.R}
  1. {C.OK}SaucerSwap V2{C.R} — pool data (primary; from pacman_data_raw.json)
     Refreshed when you run any command that fetches pool data.
     Source label: "SaucerSwap V2 (Contract ID: 0.0.xxxxx)"
  2. {C.MUTED}CoinGecko{C.R}    — only used if SaucerSwap price is missing/stale
  3. {C.MUTED}Binance{C.R}      — last resort for HBAR

{C.ACCENT}HBAR-Specific Pricing:{C.R}
  HBAR is priced via the HBAR/USDC pool on SaucerSwap V2.
  WHBAR (wrapped) is mapped 1:1 to HBAR price.
  Run {C.TEXT}pools search HBAR{C.R} to see which pool is used.

{C.ACCENT}Refreshing Price Data:{C.R}
  Run any price command after `pools search` or after a data refresh.
  The {C.TEXT}refresh_data.py{C.R} script in scripts/ updates pacman_data_raw.json.""",

    "pools": """{C.BOLD}POOL REGISTRY MANAGEMENT — COMPLETE REFERENCE{C.R}
{C.CHROME}────────────────────────────────────────────────────────{C.R}
Manage which SaucerSwap liquidity pools Pacman uses for routing.

{C.ACCENT}Sub-Commands:{C.R}
  {C.TEXT}pools list{C.R}               Show all currently approved pools (V1 + V2)
  {C.TEXT}pools search <query>{C.R}     Search on-chain by symbol or token ID
  {C.TEXT}pools approve <id>{C.R}       Add a pool to your approved registry
  {C.TEXT}pools delete <id>{C.R}        Remove a pool from the registry

{C.ACCENT}Protocol Flags:{C.R}
  {C.TEXT}--v1{C.R} or {C.TEXT}-1{C.R}          Target SaucerSwap V1 (Uniswap V2 style)
  {C.TEXT}--v2{C.R} or {C.TEXT}-2{C.R}          Target SaucerSwap V2 (default)
  Examples:
    {C.TEXT}pools search DOSA --v1{C.R}
    {C.TEXT}pools approve 0.0.12345 --v1{C.R}

{C.ACCENT}How the Registry Works:{C.R}
  data/pools.json              = V2 routing registry
  data/v1_pools_approved.json  = V1 routing registry
  Only approved pools are used in route calculation.
  The router re-builds its graph after every approve/delete.

{C.ACCENT}When to Add Pools:{C.R}
  - New token pairs not in the default registry
  - High-liquidity alternate pools for better pricing
  - Community tokens (DOSA, etc.) only on V1

{C.ACCENT}Pool Approval Flow:{C.R}
  1. {C.TEXT}pools search <token>{C.R}    — find pool contract IDs on-chain
  2. {C.TEXT}pools approve <contractId>{C.R} — add to registry + sync tokens.json
  3. Router automatically reloads — ready to route immediately""",

    "account": """{C.BOLD}WALLET & ACCOUNT MANAGEMENT — COMPLETE REFERENCE{C.R}
{C.CHROME}────────────────────────────────────────────────────────{C.R}
View wallet details and manage Hedera account IDs.

{C.ACCENT}Commands:{C.R}
  {C.TEXT}account{C.R}                          View current account info
  {C.TEXT}account --new{C.R}                    Create sub-account (same private key)
  {C.TEXT}account rename <0.0.xxx> <name>{C.R}  Label any known account

{C.ACCENT}What is Shown:{C.R}
  - Hedera Account ID (0.0.xxxxx format)
  - EVM Alias address (0x... — the ECDSA public key hash)
  - Long-Zero address (0x0000...xxxxx — for reference only, never use for transactions)
  - Network (mainnet / testnet)
  - Mode (LIVE or SIMULATION)
  - Known sub-accounts with nicknames from your local registry

{C.ACCENT}Sub-Account Creation ({C.TEXT}account --new{C.ACCENT}):{C.R}
  Creates a new Hedera ID sharing your current private key. Pacman:
  1. Prompts for an optional nickname to label the account
  2. Calls CryptoCreate via Hiero SDK
  3. Saves ID + nickname to data/accounts.json
  4. Optionally updates .env to switch the active ID

{C.ACCENT}Renaming Accounts ({C.TEXT}account rename{C.ACCENT}):{C.R}
  {C.TEXT}account rename 0.0.10289160 Trading Account{C.R}
  Updates the nickname in data/accounts.json in-place.
  Does NOT change the active account or .env.

{C.ACCENT}Important:{C.R}
  Always use your EVM Alias address (starts 0x3...) for EVM transactions.
  NEVER use the Long-Zero address (0x0000...) — it causes gas reverts on Hedera.

{C.ACCENT}For AI Agents:{C.R}
  Use {C.TEXT}account{C.R} at startup to verify the active account ID and mode.
  Hedera ID is used for SDK operations (transfers, staking).
  EVM alias is used for all Web3/contract interactions.""",

    "whitelist": """{C.BOLD}WHITELIST MANAGEMENT — COMPLETE REFERENCE{C.R}
{C.CHROME}────────────────────────────────────────────────────────{C.R}
The whitelist is a security gate: live transfers are BLOCKED
unless the recipient is explicitly whitelisted.

{C.ACCENT}Commands:{C.R}
  {C.TEXT}whitelist{C.R}                        View all whitelisted addresses
  {C.TEXT}whitelist add <0.0.xxx>{C.R}          Add address (prompts for nickname)
  {C.TEXT}whitelist add <0.0.xxx> MyLabel{C.R}  Add with nickname inline
  {C.TEXT}whitelist remove <0.0.xxx>{C.R}       Remove address

{C.ACCENT}Nickname System:{C.R}
  Each whitelisted address can have a human-readable label:
    {C.TEXT}whitelist add 0.0.7949179 "My Binance Deposit"{C.R}
  Labels appear in the whitelist view to remind you who each address belongs to.
  This prevents whitelisting an address and forgetting what it is.

{C.ACCENT}Storage:{C.R}
  Whitelist is saved in data/settings.json as:
    "transfer_whitelist": [
      {{"address": "0.0.123", "nickname": "Exchange"}}
    ]
  Bare string entries from older versions are auto-migrated.

{C.ACCENT}Note:{C.R}
  Only Hedera IDs (0.0.xxx) are supported for transfers.
  EVM address (0x...) transfers are blocked for safety.""",

    "setup": """{C.BOLD}SECURE WALLET CONFIGURATION — COMPLETE REFERENCE{C.R}
{C.CHROME}────────────────────────────────────────────────────────{C.R}
The setup wizard configures your Hedera credentials safely.

{C.ACCENT}Command:{C.R}
  {C.TEXT}ᗧ setup{C.R}

{C.ACCENT}Setup Options:{C.R}
  [P] Paste existing Private Key
      - Enter your 64-char hex ECDSA private key (masked input)
      - Pacman auto-discovers your Hedera Account ID via Mirror Node
      - Saved to .env as PRIVATE_KEY and HEDERA_ACCOUNT_ID

  [C] Create completely fresh Account
      - Generates a new ECDSA key pair
      - Creates a funded Hedera account via CryptoCreate SDK call
      - IMPORTANT: Write down your private key immediately!

{C.ACCENT}.env File Updated:{C.R}
  PRIVATE_KEY=<64-hex-chars>          (raw hex, no 0x prefix needed)
  HEDERA_ACCOUNT_ID=0.0.xxxxx         (discovered automatically)
  SAUCERSWAP_API_KEY_MAINNET=...      (optional, for higher rate limits)

{C.ACCENT}For AI Agents:{C.R}
  If .env already exists with valid credentials, {C.TEXT}setup{C.R} is not needed.
  Verify credentials are active by running {C.TEXT}account{C.R}.""",

    "swap-v1": """{C.BOLD}V1 (LEGACY) SWAPS — COMPLETE REFERENCE{C.R}
{C.CHROME}────────────────────────────────────────────────────────{C.R}
Execute swaps specifically on SaucerSwap V1 (Uniswap V2 architecture).

{C.ACCENT}When to Use V1:{C.R}
  - Token only has V1 liquidity (e.g., DOSA, older community tokens)
  - You want to bypass V2 routing for any reason

{C.ACCENT}Command Syntax:{C.R}
  {C.TEXT}swap-v1 <amount> <FROM_TOKEN> <TO_TOKEN>{C.R}
  {C.TEXT}v1 <amount> <FROM_TOKEN> <TO_TOKEN>{C.R}       (alias)

{C.ACCENT}Example:{C.R}
  {C.TEXT}ᗧ swap-v1 100 HBAR DOSA{C.R}

{C.ACCENT}Technical Notes:{C.R}
  - Uses Uniswap V2 router interface (swapExactTokensForTokens)
  - HBAR is automatically wrapped to WHBAR before routing
  - Slippage tolerance: 1%
  - Isolated from V2 execution engine (separate code path)""",

    "stake": """{C.BOLD}HEDERA NATIVE STAKING (HIP-406) — COMPLETE REFERENCE{C.R}
{C.CHROME}────────────────────────────────────────────────────────{C.R}
Stake your HBAR balance to a consensus node to earn ~1% APY rewards.

{C.ACCENT}Commands:{C.R}
  {C.TEXT}ᗧ stake{C.R}                Stake to Google Node (5) — recommended default
  {C.TEXT}ᗧ stake <node_id>{C.R}      Stake to a specific consensus node (0–28)
  {C.TEXT}ᗧ unstake{C.R}              Stop staking (clears node_id preference)

{C.ACCENT}Key Properties:{C.R}
  - NON-CUSTODIAL: Funds remain 100% liquid at all times
  - No lock-up period: unstake instantly at any time
  - Rewards accrued daily, first payment arrives ~24h after staking
  - Works on mainnet only (testnet has no real staking rewards)

{C.ACCENT}Node Selection Guide:{C.R}
  Node 5  = Google (most decentralized, recommended)
  Node 6  = EDF
  Node 10 = Swirlds Labs
  Run {C.TEXT}sources{C.R} to see current node stats.

{C.ACCENT}Under the Hood:{C.R}
  Uses a CryptoUpdate transaction (HIP-406) via the Hiero SDK.
  This sets staked_node_id on your account record.
  Pacman verifies your key derivation matches before executing.

{C.ACCENT}Viewing Staking Status:{C.R}
  Run {C.TEXT}balance{C.R} — staking status and pending rewards appear at the top.""",

    "history": """{C.BOLD}TRANSACTION HISTORY — COMPLETE REFERENCE{C.R}
{C.CHROME}────────────────────────────────────────────────────────{C.R}
View your recent on-chain activity recorded locally.

{C.ACCENT}Command:{C.R}
  {C.TEXT}ᗧ history{C.R}

{C.ACCENT}What is Shown (last 20 records):{C.R}
  - SWAP HISTORY:     Date, amounts sent/received, USD value, gas cost
  - TRANSFER HISTORY: Date, amount + token, recipient, memo
  - STAKING RECORDS:  Date, stake/unstake action, node

{C.ACCENT}Storage:{C.R}
  Individual JSON files in {C.TEXT}execution_records/{C.R}:
    swap_YYYY-MM-DD_HH-MM-SS.json
    transfer_YYYY-MM-DD_HH-MM-SS.json
    staking_YYYY-MM-DD_HH-MM-SS.json

  Training data appended to {C.TEXT}training_data/live_executions.jsonl{C.R}
  (for use in AI model fine-tuning & agent memory replay)

{C.ACCENT}For AI Agents:{C.R}
  The history command provides an audit trail of executed operations.
  Use it to verify that a recent swap or transfer completed successfully.
  Success is indicated by {C.OK}✓{C.R} (true) vs {C.ERR}✗{C.R} (failed/simulated).""",
}
