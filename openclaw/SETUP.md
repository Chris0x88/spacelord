# Space Lord Agent — OpenClaw Setup Guide

Turn your Space Lord CLI into a full AI-powered Hedera trading agent on any messaging platform.

## What You Get

- A dedicated **Hedera wallet agent** on Telegram, Discord, WhatsApp, or any OpenClaw channel
- **Twice-daily portfolio monitoring** (6 AM / 6 PM) with proactive alerts
- **Background daemons** for Power Law rebalancing and limit orders
- Full conversational trading: "swap 5 USDC for HBAR", "what's bitcoin doing?", "send 10 HBAR to 0.0.xxx"

## Prerequisites

1. **Space Lord CLI** installed and working (`./launch.sh balance` returns your portfolio)
2. **OpenClaw** installed ([openclaw.ai](https://openclaw.ai))
3. A **Telegram bot token** (optional — for Telegram routing)

---

## Step 1: Install Space Lord

```bash
git clone https://github.com/Chris0x88/spacelord.git
cd spacelord
./launch.sh setup        # Configure wallet keys
./launch.sh doctor       # Verify system health
./launch.sh balance      # Confirm it works
```

## Step 2: Create the Space Lord Agent

```bash
openclaw agents add spacelord
```

Set the workspace to this `openclaw/` directory:

```bash
# Option A: Set workspace directly
openclaw agents set spacelord --workspace /path/to/spacelord/openclaw

# Option B: Symlink into OpenClaw's agent directory
ln -s /path/to/spacelord/openclaw ~/.openclaw/workspace-spacelord
```

## Step 3: Link the Skill & Copy Defaults

```bash
# Link the skill
cd /path/to/spacelord/openclaw/skills/spacelord-hedera
ln -s ../../../SKILL.md SKILL.md

# Copy default user files (customize these for your setup)
cp /path/to/spacelord/openclaw/defaults/USER.md /path/to/spacelord/openclaw/USER.md
cp /path/to/spacelord/openclaw/defaults/MEMORY.md /path/to/spacelord/openclaw/MEMORY.md
```

The symlink means SKILL.md updates automatically when the Space Lord repo is updated. USER.md and MEMORY.md are gitignored — they're personal to each operator.

## Step 4: Configure OpenClaw

Edit `~/.openclaw/openclaw.json`. Choose a configuration below based on your setup.

### A) Space Lord Only (Simplest)

One agent, one channel. Everything goes to Space Lord.

```json5
{
  agents: {
    list: [
      {
        id: "spacelord",
        default: true,
        name: "Space Lord",
        workspace: "/path/to/spacelord/openclaw"
      }
    ]
  }
}
```

### B) Space Lord + Your Existing Agent

Keep your default OpenClaw agent for general tasks. Route a dedicated Telegram bot to Space Lord.

```json5
{
  agents: {
    list: [
      {
        id: "default",
        default: true,
        name: "Assistant",
        workspace: "~/.openclaw/workspace-default"
      },
      {
        id: "spacelord",
        name: "Space Lord",
        workspace: "/path/to/spacelord/openclaw"
      }
    ]
  },
  bindings: [
    // Route a dedicated Telegram bot to Space Lord
    {
      agentId: "spacelord",
      match: { channel: "telegram", accountId: "spacelord-bot" }
    },
    // Everything else goes to default
    {
      agentId: "default",
      match: {}
    }
  ],
  channels: {
    telegram: {
      accounts: {
        default: {
          botToken: "YOUR_MAIN_BOT_TOKEN"
        },
        "spacelord-bot": {
          botToken: "YOUR_SPACELORD_BOT_TOKEN",
          dmPolicy: "pairing"
        }
      }
    }
  }
}
```

**How to get a second Telegram bot:**
1. Open Telegram, find **@BotFather**
2. Send `/newbot`, name it "Space Lord Wallet" (or similar)
3. Copy the bot token into `YOUR_SPACELORD_BOT_TOKEN`

### C) Route by Chat (Single Bot, Multiple Agents)

Use one Telegram bot but route specific group chats to Space Lord.

```json5
{
  agents: {
    list: [
      { id: "default", default: true, workspace: "~/.openclaw/workspace-default" },
      { id: "spacelord", name: "Space Lord", workspace: "/path/to/spacelord/openclaw" }
    ]
  },
  bindings: [
    // This specific group chat goes to Space Lord
    {
      agentId: "spacelord",
      match: {
        channel: "telegram",
        peer: { kind: "group", id: "-1001234567890" }
      }
    },
    // Everything else stays default
    { agentId: "default", match: {} }
  ]
}
```

To find a Telegram group chat ID: add your bot to the group, send a message, then check `https://api.telegram.org/bot<TOKEN>/getUpdates`.

### D) Multi-Channel (Telegram + Discord)

Same Space Lord agent, reachable from multiple platforms.

```json5
{
  agents: {
    list: [
      {
        id: "spacelord",
        default: true,
        name: "Space Lord",
        workspace: "/path/to/spacelord/openclaw"
      }
    ]
  },
  channels: {
    telegram: {
      accounts: {
        default: {
          botToken: "YOUR_TELEGRAM_BOT_TOKEN",
          dmPolicy: "pairing"
        }
      }
    },
    discord: {
      accounts: {
        default: {
          botToken: "YOUR_DISCORD_BOT_TOKEN"
        }
      }
    }
  }
}
```

### E) WhatsApp Setup

WhatsApp uses QR pairing instead of a bot token.

```json5
{
  agents: {
    list: [
      {
        id: "spacelord",
        default: true,
        workspace: "/path/to/spacelord/openclaw"
      }
    ]
  },
  channels: {
    whatsapp: {
      accounts: {
        default: {
          dmPolicy: "pairing"
        }
      }
    }
  }
}
```

Then run `openclaw channels pair whatsapp` and scan the QR code with your phone.

## Step 5: Set Up the Heartbeat (Cron)

The heartbeat checks your portfolio, daemons, and orders twice daily.

```bash
# 6 AM daily check
openclaw cron add \
  --name "spacelord-morning" \
  --cron "0 6 * * *" \
  --agent spacelord \
  --session isolated \
  --announce telegram:default \
  --message "Run the HEARTBEAT.md checklist"

# 6 PM daily check
openclaw cron add \
  --name "spacelord-evening" \
  --cron "0 18 * * *" \
  --agent spacelord \
  --session isolated \
  --announce telegram:default \
  --message "Run the HEARTBEAT.md checklist"
```

Adjust the `--announce` channel to match your setup (e.g., `discord:default`, `whatsapp:default`).

## Step 6: Start Daemons & Verify

```bash
# Start Space Lord background services
cd /path/to/spacelord
./launch.sh daemon-start

# Verify agent is loaded
openclaw agents list --bindings

# Restart the gateway to pick up config changes
openclaw gateway restart

# Test with a chat
openclaw chat spacelord
> hi
# Should see: portfolio overview, daemon status, action menu
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Skill not found" | Check symlink: `ls -la openclaw/skills/spacelord-hedera/SKILL.md` |
| "exec failed" | Verify Space Lord works standalone: `cd /path/to/spacelord && ./launch.sh balance` |
| "daemon not running" | Run `./launch.sh daemon-start` from the Space Lord repo |
| Agent suggests MoonPay with tokens available | SOUL.md rule — check it's loaded (`/context list` in chat) |
| "No route found" for a swap | Run `./launch.sh pools search <TOKEN>` to discover pools |
| Agent modifying config files | SOUL.md violation — check `openclaw agents list` shows correct workspace |

## Architecture

```
┌──────────────────────────────────────────────────┐
│  OpenClaw Gateway                                │
│  ┌────────────┐  ┌───────────┐  ┌────────────┐  │
│  │  Telegram   │  │  Discord  │  │  WhatsApp  │  │
│  └─────┬──────┘  └─────┬─────┘  └─────┬──────┘  │
│        └───────────────┼───────────────┘         │
│                        ▼                         │
│              ┌─────────────────┐                 │
│              │  Space Lord Agent   │                 │
│              │  (openclaw/)    │                 │
│              │                 │                 │
│              │  SOUL.md ◄──── loaded every turn  │
│              │  SKILL.md ◄─── loaded on demand   │
│              │  HEARTBEAT.md   ◄── 6AM + 6PM     │
│              └────────┬────────┘                 │
│                       ▼                          │
│              ./launch.sh <cmd>                   │
│                       ▼                          │
│              ┌─────────────────┐                 │
│              │  Space Lord CLI     │                 │
│              │  (Python app)   │                 │
│              │                 │                 │
│              │  Daemon ──► PowerLaw rebalancer   │
│              │           ──► Limit order engine  │
│              │           ──► HCS signals         │
│              │           ──► Web dashboard       │
│              └─────────────────┘                 │
└──────────────────────────────────────────────────┘
```

## Files in This Workspace

| File | Loaded | Purpose |
|------|--------|---------|
| `SOUL.md` | Every turn | Core identity + unbreakable rules (~370 words) |
| `IDENTITY.md` | Every turn | Name and role (3 lines) |
| `BOOTSTRAP.md` | Every turn | Channel format table + safety limits |
| `USER.md` | Every turn | Your personal preferences |
| `AGENTS.md` | Every turn | Architecture guide for the agent |
| `MEMORY.md` | Private sessions | Long-term memory index |
| `HEARTBEAT.md` | Cron (2x/day) | Portfolio monitoring checklist |
| `skills/spacelord-hedera/SKILL.md` | On demand | Full 965-line command reference |
