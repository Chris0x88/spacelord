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

