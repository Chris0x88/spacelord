"""
Discord Bot Runner  [UNTESTED PLUGIN — wallet bot, mirrors Telegram poller]
============================================================================
⚠️  UNTESTED: Bot connects and syncs slash commands but end-to-end flows
    (swap, send, button interactions) have NOT been QA-verified.

Uses discord.py with slash commands and button interactions.
Shares the SAME InboundRouter as the Telegram bot.

    Bot token:  DISCORD_BOT_TOKEN  (from .env)
    Start:      ./launch.sh discord-start
    Stop:       ./launch.sh discord-stop

All business logic lives in lib/tg_router.py. This file is ONLY
the Discord transport layer — receiving interactions, converting
formats, and sending responses.
"""

import asyncio
import logging
import os
import signal
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import discord
from discord import app_commands

# ---------------------------------------------------------------------------
# Bootstrap: load .env before anything else
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_ENV_FILE = _REPO_ROOT / ".env"

if _ENV_FILE.exists():
    with open(_ENV_FILE) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip("'\"")
            if key and key not in os.environ:
                os.environ[key] = value

# Now safe to import project modules
sys.path.insert(0, str(_REPO_ROOT))

from src.plugins.discord_bot import config as dc_config
from lib.tg_router import InboundRouter
from lib import dc_format

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("spacelord.discord")

# ---------------------------------------------------------------------------
# Module-level state
# ---------------------------------------------------------------------------
_router: Optional[InboundRouter] = None
_allowed_users: Set[int] = set()
_bot_token: str = ""

# Dedup for confirm buttons (same pattern as Telegram)
_recent_confirm_ids: Dict[str, float] = {}
_CONFIRM_DEDUP_TTL = 30.0


def _is_confirm_already_processed(interaction_id: str) -> bool:
    """Dedup guard against double-taps on confirm buttons."""
    now = time.monotonic()
    expired = [k for k, ts in _recent_confirm_ids.items() if now - ts > _CONFIRM_DEDUP_TTL]
    for k in expired:
        del _recent_confirm_ids[k]
    if interaction_id in _recent_confirm_ids:
        return True
    _recent_confirm_ids[interaction_id] = now
    return False


def _is_authorized(user_id: int) -> bool:
    if not _allowed_users:
        return True
    return user_id in _allowed_users


# ---------------------------------------------------------------------------
# Discord UI: convert button data to discord.ui.View
# ---------------------------------------------------------------------------

class CallbackButton(discord.ui.Button):
    """A button that fires a callback_data string back to InboundRouter."""

    def __init__(self, label: str, custom_id: str, style: discord.ButtonStyle = discord.ButtonStyle.secondary):
        super().__init__(label=label, custom_id=custom_id, style=style)

    async def callback(self, interaction: discord.Interaction):
        await _handle_button_press(interaction, self.custom_id)


class LinkButton(discord.ui.Button):
    """A button that opens a URL."""

    def __init__(self, label: str, url: str):
        super().__init__(label=label, url=url, style=discord.ButtonStyle.link)


def _build_view(buttons: List[Any]) -> Optional[discord.ui.View]:
    """
    Build a discord.ui.View from the converted button list.

    buttons is a list of dicts with {label, custom_id} or {label, url},
    separated by "ROW_BREAK" strings.
    """
    if not buttons:
        return None

    view = discord.ui.View(timeout=300)  # 5 min timeout for buttons
    count_in_row = 0

    for item in buttons:
        if item == "ROW_BREAK":
            count_in_row = 0
            continue

        if not isinstance(item, dict):
            continue

        label = item.get("label", "?")
        custom_id = item.get("custom_id", "")
        url = item.get("url", "")

        # Pick style based on button semantics
        style = discord.ButtonStyle.secondary
        if "confirm" in custom_id:
            style = discord.ButtonStyle.success
        elif "swap" in custom_id or "send" in custom_id:
            style = discord.ButtonStyle.primary
        elif "menu" in custom_id or "home" in custom_id:
            style = discord.ButtonStyle.secondary

        if url:
            view.add_item(LinkButton(label=label, url=url))
        elif custom_id:
            view.add_item(CallbackButton(label=label, custom_id=custom_id, style=style))

        count_in_row += 1

    return view if len(view.children) > 0 else None


# ---------------------------------------------------------------------------
# Button press handler
# ---------------------------------------------------------------------------

async def _handle_button_press(interaction: discord.Interaction, callback_data: str):
    """Handle a button press by routing through InboundRouter."""
    if not _is_authorized(interaction.user.id):
        await interaction.response.send_message("Access denied.", ephemeral=True)
        return

    # Confirm swap — dedup + loading state + thread execution
    if callback_data.startswith("confirm_swap:"):
        if _is_confirm_already_processed(str(interaction.id)):
            await interaction.response.send_message("Already processing...", ephemeral=True)
            return
        await interaction.response.defer()
        try:
            response = await asyncio.to_thread(
                _router.execute_swap_callback, callback_data
            )
        except Exception as exc:
            logger.error(f"execute_swap_callback raised: {exc}", exc_info=True)
            from lib.tg_format import format_swap_error, format_buttons
            response = {
                "text": format_swap_error(f"Unexpected error: {exc}"),
                "reply_markup": format_buttons(),
                "parse_mode": "HTML",
            }
        converted = dc_format.convert_response(response)
        view = _build_view(converted.get("buttons"))
        await interaction.followup.send(
            content=converted["content"],
            view=view or discord.utils.MISSING,
        )
        return

    # Confirm send — same pattern
    if callback_data.startswith("confirm_send:"):
        if _is_confirm_already_processed(str(interaction.id)):
            await interaction.response.send_message("Already processing...", ephemeral=True)
            return
        await interaction.response.defer()
        try:
            response = await asyncio.to_thread(
                _router.execute_send_callback, callback_data
            )
        except Exception as exc:
            logger.error(f"execute_send_callback raised: {exc}", exc_info=True)
            from lib.tg_format import format_send_error, format_buttons
            response = {
                "text": format_send_error(f"Unexpected error: {exc}"),
                "reply_markup": format_buttons(),
                "parse_mode": "HTML",
            }
        converted = dc_format.convert_response(response)
        view = _build_view(converted.get("buttons"))
        await interaction.followup.send(
            content=converted["content"],
            view=view or discord.utils.MISSING,
        )
        return

    # All other callbacks — fast lane
    await interaction.response.defer()
    try:
        response = _router.handle_callback(callback_data, interaction.user.id)
    except Exception as exc:
        logger.error(f"handle_callback raised: {exc}", exc_info=True)
        await interaction.followup.send(content=f"Error: {exc}")
        return

    converted = dc_format.convert_response(response)
    view = _build_view(converted.get("buttons"))
    await interaction.followup.send(
        content=converted["content"],
        view=view or discord.utils.MISSING,
    )


# ---------------------------------------------------------------------------
# Slash command helper
# ---------------------------------------------------------------------------

def _route_message(text: str, user_id: int) -> Dict[str, Any]:
    """Route a message through InboundRouter and convert to Discord format."""
    response = _router.handle_message(text, user_id)
    return dc_format.convert_response(response)


# ---------------------------------------------------------------------------
# Bot setup
# ---------------------------------------------------------------------------

def create_bot() -> discord.Client:
    """Create and configure the Discord bot with slash commands."""
    intents = discord.Intents.default()
    # message_content is a privileged intent — enable it in the Discord Developer
    # Portal (Bot → Privileged Gateway Intents) if you want DM/mention free-text.
    # Slash commands work without it and are the primary interface.
    # intents.message_content = True

    client = discord.Client(intents=intents)
    tree = app_commands.CommandTree(client)

    guild_id = dc_config.get_guild_id()
    guild_obj = discord.Object(id=guild_id) if guild_id else None

    # ── Slash Commands ─────────────────────────────────────────

    @tree.command(
        name="spacelord",
        description="Open Space Lord wallet menu",
        guild=guild_obj,
    )
    async def cmd_menu(interaction: discord.Interaction):
        if not _is_authorized(interaction.user.id):
            await interaction.response.send_message("Access denied.", ephemeral=True)
            return
        result = _route_message("/start", interaction.user.id)
        view = _build_view(result.get("buttons"))
        await interaction.response.send_message(
            content=result["content"],
            view=view or discord.utils.MISSING,
        )

    @tree.command(
        name="portfolio",
        description="Show wallet portfolio and balances",
        guild=guild_obj,
    )
    async def cmd_portfolio(interaction: discord.Interaction):
        if not _is_authorized(interaction.user.id):
            await interaction.response.send_message("Access denied.", ephemeral=True)
            return
        await interaction.response.defer()
        result = _route_message("/portfolio", interaction.user.id)
        view = _build_view(result.get("buttons"))
        await interaction.followup.send(
            content=result["content"],
            view=view or discord.utils.MISSING,
        )

    @tree.command(
        name="swap",
        description="Start a token swap",
        guild=guild_obj,
    )
    @app_commands.describe(args="Optional: e.g. '5 USDC for HBAR'")
    async def cmd_swap(interaction: discord.Interaction, args: Optional[str] = None):
        if not _is_authorized(interaction.user.id):
            await interaction.response.send_message("Access denied.", ephemeral=True)
            return
        await interaction.response.defer()
        if args:
            result = _route_message(f"swap {args}", interaction.user.id)
        else:
            response = _router.handle_callback("swap", interaction.user.id)
            result = dc_format.convert_response(response)
        view = _build_view(result.get("buttons"))
        await interaction.followup.send(
            content=result["content"],
            view=view or discord.utils.MISSING,
        )

    @tree.command(
        name="send",
        description="Send tokens to a whitelisted address",
        guild=guild_obj,
    )
    @app_commands.describe(args="Optional: e.g. '10 USDC to 0.0.123456'")
    async def cmd_send(interaction: discord.Interaction, args: Optional[str] = None):
        if not _is_authorized(interaction.user.id):
            await interaction.response.send_message("Access denied.", ephemeral=True)
            return
        await interaction.response.defer()
        if args:
            result = _route_message(f"send {args}", interaction.user.id)
        else:
            response = _router.handle_callback("send", interaction.user.id)
            result = dc_format.convert_response(response)
        view = _build_view(result.get("buttons"))
        await interaction.followup.send(
            content=result["content"],
            view=view or discord.utils.MISSING,
        )

    @tree.command(
        name="price",
        description="Show token prices",
        guild=guild_obj,
    )
    @app_commands.describe(token="Optional: specific token symbol (e.g. HBAR)")
    async def cmd_price(interaction: discord.Interaction, token: Optional[str] = None):
        if not _is_authorized(interaction.user.id):
            await interaction.response.send_message("Access denied.", ephemeral=True)
            return
        await interaction.response.defer()
        msg = f"/price {token}" if token else "/price"
        result = _route_message(msg, interaction.user.id)
        view = _build_view(result.get("buttons"))
        await interaction.followup.send(
            content=result["content"],
            view=view or discord.utils.MISSING,
        )

    @tree.command(
        name="gas",
        description="Check HBAR gas reserve",
        guild=guild_obj,
    )
    async def cmd_gas(interaction: discord.Interaction):
        if not _is_authorized(interaction.user.id):
            await interaction.response.send_message("Access denied.", ephemeral=True)
            return
        await interaction.response.defer()
        result = _route_message("/gas", interaction.user.id)
        view = _build_view(result.get("buttons"))
        await interaction.followup.send(
            content=result["content"],
            view=view or discord.utils.MISSING,
        )

    @tree.command(
        name="history",
        description="Show recent transaction history",
        guild=guild_obj,
    )
    async def cmd_history(interaction: discord.Interaction):
        if not _is_authorized(interaction.user.id):
            await interaction.response.send_message("Access denied.", ephemeral=True)
            return
        await interaction.response.defer()
        result = _route_message("/history", interaction.user.id)
        view = _build_view(result.get("buttons"))
        await interaction.followup.send(
            content=result["content"],
            view=view or discord.utils.MISSING,
        )

    @tree.command(
        name="tokens",
        description="Show supported tokens",
        guild=guild_obj,
    )
    async def cmd_tokens(interaction: discord.Interaction):
        if not _is_authorized(interaction.user.id):
            await interaction.response.send_message("Access denied.", ephemeral=True)
            return
        await interaction.response.defer()
        result = _route_message("/tokens", interaction.user.id)
        view = _build_view(result.get("buttons"))
        await interaction.followup.send(
            content=result["content"],
            view=view or discord.utils.MISSING,
        )

    @tree.command(
        name="robot",
        description="Show rebalancer robot status",
        guild=guild_obj,
    )
    async def cmd_robot(interaction: discord.Interaction):
        if not _is_authorized(interaction.user.id):
            await interaction.response.send_message("Access denied.", ephemeral=True)
            return
        await interaction.response.defer()
        result = _route_message("/robot", interaction.user.id)
        view = _build_view(result.get("buttons"))
        await interaction.followup.send(
            content=result["content"],
            view=view or discord.utils.MISSING,
        )

    @tree.command(
        name="status",
        description="Show system health dashboard",
        guild=guild_obj,
    )
    async def cmd_status(interaction: discord.Interaction):
        if not _is_authorized(interaction.user.id):
            await interaction.response.send_message("Access denied.", ephemeral=True)
            return
        await interaction.response.defer()
        result = _route_message("/status", interaction.user.id)
        view = _build_view(result.get("buttons"))
        await interaction.followup.send(
            content=result["content"],
            view=view or discord.utils.MISSING,
        )

    # ── Events ─────────────────────────────────────────────────

    @client.event
    async def on_ready():
        logger.info(f"Bot: {client.user} (ID: {client.user.id})")
        logger.info(f"Guilds: {[g.name for g in client.guilds]}")

        # Sync slash commands
        if guild_obj:
            tree.copy_global_to(guild=guild_obj)
            synced = await tree.sync(guild=guild_obj)
            logger.info(f"Synced {len(synced)} commands to guild {guild_id}")
        else:
            synced = await tree.sync()
            logger.info(f"Synced {len(synced)} global commands (may take up to 1 hour to propagate)")

        logger.info(
            f"Allowed users: {'(all)' if not _allowed_users else _allowed_users}"
        )

    @client.event
    async def on_message(message: discord.Message):
        """Handle free-text messages (DMs or mentions)."""
        # Ignore own messages
        if message.author == client.user:
            return
        # Ignore messages from other bots
        if message.author.bot:
            return

        # Only respond in DMs or when mentioned
        is_dm = isinstance(message.channel, discord.DMChannel)
        is_mentioned = client.user in message.mentions if message.mentions else False

        if not is_dm and not is_mentioned:
            return

        if not _is_authorized(message.author.id):
            await message.reply("Access denied.")
            return

        text = message.content
        # Strip bot mention from the text
        if is_mentioned and client.user:
            text = text.replace(f"<@{client.user.id}>", "").strip()
            text = text.replace(f"<@!{client.user.id}>", "").strip()

        if not text:
            text = "/start"

        # Check for pending custom amount input
        pending_response = _router.handle_pending_input(text, message.author.id)
        if pending_response:
            converted = dc_format.convert_response(pending_response)
            view = _build_view(converted.get("buttons"))
            await message.reply(
                content=converted["content"],
                view=view or discord.utils.MISSING,
            )
            return

        result = _route_message(text, message.author.id)
        view = _build_view(result.get("buttons"))
        await message.reply(
            content=result["content"],
            view=view or discord.utils.MISSING,
        )

    return client, tree


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main() -> None:
    global _bot_token, _allowed_users, _router

    _bot_token = dc_config.get_bot_token()
    _allowed_users = dc_config.get_allowed_users()

    logger.info("Initialising SpaceLordController...")
    from src.controller import SpaceLordController
    controller = SpaceLordController()
    _router = InboundRouter(controller)

    client, tree = create_bot()

    logger.info("Starting Discord bot...")

    # Handle graceful shutdown
    loop = asyncio.get_running_loop()

    def _handle_shutdown():
        logger.info("Shutdown signal received...")
        asyncio.ensure_future(client.close())

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _handle_shutdown)

    try:
        await client.start(_bot_token)
    finally:
        if not client.is_closed():
            await client.close()
        logger.info("Discord bot stopped.")


if __name__ == "__main__":
    asyncio.run(main())
