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
    ("swap <amt> <A> for <B>",   "Exact input swap"),
    ("swap <A> for <amt> <B>",   "Exact output swap"),
    ("convert <A> for <amt> <B>","Wrap / Unwrap tokens"),
    ("send <amt> <tk> to <rcp>", "Transfer crypto"),
    ("receive <token>",          "Get addr & associate"),
    ("balance",                  "All wallet balances"),
    ("balance <token>",          "Single token balance"),
    ("price",                    "List all market prices"),
    ("price <token>",            "Check single price"),
    ("sources",                  "Show all price sources"),
    ("account",                  "Wallet & network info"),
    ("tokens",                   "Supported token list"),
    ("history",                  "Transaction history"),
    ("verbose",                  "Toggle debug logging"),
    ("help",                     "This menu"),
    ("exit",                     "Quit Pacman"),
]

HELP_EXAMPLES = [
    ("swap 100 HBAR for USDC",    "Swap ~100 HBAR to USDC"),
    ("swap HBAR for 10 USDC",     "Swap enough HBAR to get 10 USDC"),
    ("swap 100 USDC for HBAR",    "Swap 100 USDC to HBAR"),
    ("convert 100 HBAR for WHBAR", "Wrap HBAR to WHBAR"),
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

{C.ACCENT}3. Intent Detection{C.R}
   - {C.BOLD}Exact In{C.R}:  "swap {C.OK}10{C.R} A for B" (You spend exactly 10 A)
   - {C.BOLD}Exact Out{C.R}: "swap A for {C.OK}10{C.R} B" (You get exactly 10 B)
   - {C.BOLD}Buy Mode{C.R}:  "buy 10 B with A" (Exact Output mode)""",

    "swap": """{C.BOLD}SWAPPING & CONVERSION{C.R}
{C.CHROME}────────────────────────────────────────────────────────{C.R}
Pacman finds the most efficient path through the SaucerSwap 
V2 Liquidity Graph.

{C.ACCENT}Usage examples:{C.R}
  {C.TEXT}ᗧ swap 10 HBAR for USDC{C.R}   (Exact Input)
  {C.TEXT}ᗧ swap HBAR for 10 USDC{C.R}   (Exact Output)
  {C.TEXT}ᗧ convert 10 HBAR to WHBAR{C.R} (Wrap/Unwrap)

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
}

