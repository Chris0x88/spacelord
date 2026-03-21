# Pacman Agent — OpenClaw Setup Guide

Turn your Pacman CLI into a full AI-powered Hedera trading agent on any messaging platform.

## What You Get

- A dedicated **Hedera wallet agent** on Telegram, Discord, WhatsApp, or any OpenClaw channel
- **Twice-daily portfolio monitoring** (6 AM / 6 PM) with proactive alerts
- **Background daemons** for Power Law rebalancing and limit orders
- Full conversational trading: "swap 5 USDC for HBAR", "what's bitcoin doing?", "send 10 HBAR to 0.0.xxx"

## Prerequisites

1. **Pacman CLI** installed and working (`./launch.sh balance` returns your portfolio)
2. **OpenClaw** installed ([openclaw.ai](https://openclaw.ai))
3. A **Telegram bot token** (optional — for Telegram routing)

---

## Step 1: Install Pacman

```bash
git clone https://github.com/Chris0x88/pacman.git
cd pacman
./launch.sh setup        # Configure wallet keys
./launch.sh doctor       # Verify system health
./launch.sh balance      # Confirm it works
```

## Step 2: Create the Pacman Agent

```bash
openclaw agents add pacman
```

Set the workspace to this `openclaw/` directory:

```bash
# Option A: Set workspace directly
openclaw agents set pacman --workspace /path/to/pacman/openclaw

# Option B: Symlink into OpenClaw's agent directory
ln -s /path/to/pacman/openclaw ~/.openclaw/workspace-pacman
```

## Step 3: Link the Skill & Copy Defaults

```bash
# Link the skill
cd /path/to/pacman/openclaw/skills/pacman-hedera
ln -s ../../../SKILL.md SKILL.md

# Copy default user files (customize these for your setup)
cp /path/to/pacman/openclaw/defaults/USER.md /path/to/pacman/openclaw/USER.md
cp /path/to/pacman/openclaw/defaults/MEMORY.md /path/to/pacman/openclaw/MEMORY.md
```

The symlink means SKILL.md updates automatically when the Pacman repo is updated. USER.md and MEMORY.md are gitignored — they're personal to each operator.

## Step 4: Configure OpenClaw

Edit `~/.openclaw/openclaw.json`. Choose a configuration below based on your setup.

### A) Pacman Only (Simplest)

One agent, one channel. Everything goes to Pacman.

```json5
{
  agents: {
    list: [
      {
        id: "pacman",
        default: true,
        name: "Pacman",
        workspace: "/path/to/pacman/openclaw"
      }
    ]
  }
}
```

### B) Pacman + Your Existing Agent

Keep your default OpenClaw agent for general tasks. Route a specific Telegram bot to Pacman.

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
        id: "pacman",
        name: "Pacman",
        workspace: "/path/to/pacman/openclaw"
      }
    ]
  },
  bindings: [
    // Route a dedicated Telegram bot to Pacman
    {
      agentId: "pacman",
      match: { channel: "telegram", accountId: "pacman-bot" }
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
        "pacman-bot": {
          botToken: "YOUR_PACMAN_BOT_TOKEN",
          dmPolicy: "pairing"
        }
      }
    }
  }
}
```

**How to get a second Telegram bot:**
1. Open Telegram, find **@BotFather**
2. Send `/newbot`, name it "Pacman Wallet" (or similar)
3. Copy the bot token into `YOUR_PACMAN_BOT_TOKEN`

### C) Route by Chat (Single Bot, Multiple Agents)

Use one Telegram bot but route specific group chats to Pacman.

```json5
{
  agents: {
    list: [
      { id: "default", default: true, workspace: "~/.openclaw/workspace-default" },
      { id: "pacman", name: "Pacman", workspace: "/path/to/pacman/openclaw" }
    ]
  },
  bindings: [
    // This specific group chat goes to Pacman
    {
      agentId: "pacman",
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

Same Pacman agent, reachable from multiple platforms.

```json5
{
  agents: {
    list: [
      {
        id: "pacman",
        default: true,
        name: "Pacman",
        workspace: "/path/to/pacman/openclaw"
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
        id: "pacman",
        default: true,
        workspace: "/path/to/pacman/openclaw"
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
  --name "pacman-morning" \
  --cron "0 6 * * *" \
  --agent pacman \
  --session isolated \
  --announce telegram:default \
  --message "Run the HEARTBEAT.md checklist"

# 6 PM daily check
openclaw cron add \
  --name "pacman-evening" \
  --cron "0 18 * * *" \
  --agent pacman \
  --session isolated \
  --announce telegram:default \
  --message "Run the HEARTBEAT.md checklist"
```

Adjust the `--announce` channel to match your setup (e.g., `discord:default`, `whatsapp:default`).

## Step 6: Start Daemons & Verify

```bash
# Start Pacman background services
cd /path/to/pacman
./launch.sh daemon-start

# Verify agent is loaded
openclaw agents list --bindings

# Restart the gateway to pick up config changes
openclaw gateway restart

# Test with a chat
openclaw chat pacman
> hi
# Should see: portfolio overview, daemon status, action menu
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Skill not found" | Check symlink: `ls -la openclaw/skills/pacman-hedera/SKILL.md` |
| "exec failed" | Verify Pacman works standalone: `cd /path/to/pacman && ./launch.sh balance` |
| "daemon not running" | Run `./launch.sh daemon-start` from the Pacman repo |
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
│              │  Pacman Agent   │                 │
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
│              │  Pacman CLI     │                 │
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
| `skills/pacman-hedera/SKILL.md` | On demand | Full 965-line command reference |
