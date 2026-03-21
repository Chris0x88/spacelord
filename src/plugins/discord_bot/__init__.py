"""
Discord Wallet Bot  [UNTESTED PLUGIN — do not use in production]
==================
⚠️  STATUS: Untested. Architecture is complete and mirrors the Telegram bot
    exactly, but has NOT been run through a full QA cycle. Slash commands,
    button flows, and swap/send confirmations are implemented but unverified.

Standalone Discord bot using discord.py with slash commands and button interactions.
Uses DISCORD_BOT_TOKEN from .env.

Uses the SAME InboundRouter and business logic as the Telegram bot.
Output is converted from HTML (Telegram format) to Discord markdown via lib/dc_format.py.

    Start:   ./launch.sh discord-start
    Stop:    ./launch.sh discord-stop
    Status:  ./launch.sh discord-status

Prerequisites before testing:
    1. Set DISCORD_BOT_TOKEN in .env
    2. Set DISCORD_GUILD_ID in .env (for instant slash command sync)
    3. Enable Message Content Intent in Discord Dev Portal if you want DM/mention support
    4. Invite bot to server via OAuth2 URL (scopes: bot + applications.commands)
"""
