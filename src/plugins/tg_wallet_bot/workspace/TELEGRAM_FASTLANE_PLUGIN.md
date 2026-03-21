# Pacman Telegram Fast-Lane Plugin — Build Spec for OpenClaw Agent

## What This Is

A precise instruction set for building an OpenClaw plugin that intercepts Telegram inline button presses (callback_data) and slash commands **before the LLM** and routes them to Pacman's fast-lane CLI. The LLM is only involved for natural language messages.

## The Problem

When a user taps an inline button (e.g. "💱 Swap") in Telegram:
1. OpenClaw receives the callback_data string (e.g. `swap`)
2. OpenClaw sends it to the LLM agent as a text message
3. The LLM thinks about it (1-5 seconds)
4. The LLM decides to run `./launch.sh balance` or similar
5. The LLM formats a response (another 1-3 seconds)

Total: 3-8 seconds for a deterministic operation that should take <200ms.

## The Solution

Use OpenClaw's `registerCommand()` API to register handlers that **bypass the LLM entirely**. When callback_data matches a known pattern, execute `./launch.sh tg callback <data>` directly and return the pre-formatted response.

## Architecture

```
User taps button → Telegram → OpenClaw gateway
    ↓
Plugin: Is callback_data a known pattern?
    ├─ YES → exec("./launch.sh tg callback <data>") → parse JSON → return ReplyPayload with buttons
    │        (< 200ms, no LLM)
    └─ NO  → fall through to LLM agent (natural language)
```

## Plugin Structure

Create these files in the OpenClaw extensions directory:

### File: `~/.openclaw/extensions/pacman-fastlane/package.json`

```json
{
  "name": "pacman-fastlane",
  "version": "1.0.0",
  "description": "Telegram fast-lane for Pacman wallet — bypasses LLM for button-driven operations",
  "type": "module",
  "main": "index.ts",
  "license": "MIT",
  "openclaw": {
    "extensions": ["./index.ts"]
  },
  "peerDependencies": {
    "openclaw": "*"
  }
}
```

### File: `~/.openclaw/extensions/pacman-fastlane/openclaw.plugin.json`

```json
{
  "id": "pacman-fastlane",
  "uiHints": {
    "pacmanDir": {
      "label": "Pacman Directory",
      "help": "Absolute path to the Pacman repo (where launch.sh lives)"
    }
  },
  "configSchema": {
    "type": "object",
    "additionalProperties": false,
    "properties": {
      "enabled": { "type": "boolean" },
      "pacmanDir": { "type": "string" }
    }
  }
}
```

### File: `~/.openclaw/extensions/pacman-fastlane/index.ts`

```typescript
/**
 * pacman-fastlane — OpenClaw plugin
 *
 * Intercepts Telegram callback_data and slash commands for the Pacman
 * wallet bot. Routes known patterns to ./launch.sh tg (fast-lane CLI)
 * which returns pre-formatted HTML + inline keyboard buttons.
 *
 * The LLM agent is ONLY invoked for natural language messages.
 */

import { execSync } from "node:child_process";
import { existsSync } from "node:fs";
import { resolve } from "node:path";
import type { OpenClawPluginApi, ReplyPayload, PluginCommandContext } from "openclaw/plugin-sdk";

// ---------------------------------------------------------------------------
// Known callback_data patterns that should bypass the LLM
// ---------------------------------------------------------------------------

const FAST_LANE_CALLBACKS = new Set([
  "portfolio", "balance", "swap", "send", "price", "gas",
  "health", "status", "tokens", "history", "setup", "robot",
  "orders", "menu",
]);

const FAST_LANE_PREFIXES = [
  "sf:",           // swap: pick "from" token
  "st:",           // swap: pick "to" token
  "sa:",           // swap: pick amount
  "confirm_swap:", // swap: confirm execution
  "cancel:",       // cancel any flow
  "send_tok:",     // send: pick token
  "send_to:",      // send: pick recipient
  "send_amt:",     // send: pick amount
  "confirm_send:", // send: confirm execution
];

// Slash commands that map to fast-lane
const FAST_LANE_SLASH = new Set([
  "portfolio", "balance", "swap", "send", "price", "gas",
  "health", "status", "tokens", "history", "setup", "robot",
  "orders", "start", "help", "menu",
]);

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function isFastLaneCallback(data: string): boolean {
  if (FAST_LANE_CALLBACKS.has(data)) return true;
  return FAST_LANE_PREFIXES.some(prefix => data.startsWith(prefix));
}

function resolvePacmanDir(config: any): string {
  const dir = config?.plugins?.entries?.["pacman-fastlane"]?.pacmanDir
    ?? process.env.PACMAN_DIR
    ?? resolve(process.env.HOME ?? "~", "Developer/pacman");
  return dir;
}

type FastLaneResponse = {
  text: string;
  parse_mode?: string;
  buttons?: Array<Array<{ text: string; callback_data: string }>>;
};

function execFastLane(pacmanDir: string, action: string): FastLaneResponse | null {
  if (!existsSync(resolve(pacmanDir, "launch.sh"))) {
    return null;
  }

  try {
    const stdout = execSync(
      `./launch.sh tg ${action}`,
      {
        cwd: pacmanDir,
        timeout: 15000,       // 15s max (swap execution can take time)
        encoding: "utf-8",
        stdio: ["pipe", "pipe", "pipe"],
        env: { ...process.env, PYTHONDONTWRITEBYTECODE: "1" },
      }
    ).trim();

    if (!stdout) return null;
    return JSON.parse(stdout) as FastLaneResponse;
  } catch (err: any) {
    // Log but don't crash — fall through to LLM
    console.error(`[pacman-fastlane] exec error: ${err.message}`);
    return null;
  }
}

function fastLaneToReply(result: FastLaneResponse): ReplyPayload {
  const payload: ReplyPayload = {
    text: result.text,
  };

  // Attach buttons via channelData for Telegram
  if (result.buttons && result.buttons.length > 0) {
    payload.channelData = {
      telegram: {
        buttons: result.buttons,
      },
    };
  }

  return payload;
}

// ---------------------------------------------------------------------------
// Plugin definition
// ---------------------------------------------------------------------------

export default function register(api: OpenClawPluginApi) {
  const config = api.config ?? {};
  const pacmanDir = resolvePacmanDir(config);

  // -----------------------------------------------------------------------
  // Register slash commands that bypass LLM
  // -----------------------------------------------------------------------

  for (const cmd of FAST_LANE_SLASH) {
    api.registerCommand({
      name: cmd,
      description: `Pacman: /${cmd}`,
      acceptsArgs: true,
      requireAuth: true,
      handler: (ctx: PluginCommandContext): ReplyPayload => {
        // Only intercept on the pacman bot account
        if (ctx.accountId && ctx.accountId !== "pacman") {
          // Not our bot — let the default agent handle it
          return { text: "" };
        }

        const args = ctx.args?.trim() ?? "";
        const action = args ? `${cmd} ${args}` : cmd;
        const result = execFastLane(pacmanDir, action);

        if (!result) {
          // Fast lane failed — return empty to let LLM handle
          return { text: "" };
        }

        return fastLaneToReply(result);
      },
    });
  }

  // -----------------------------------------------------------------------
  // Hook: intercept callback_data before it reaches the LLM
  // -----------------------------------------------------------------------

  api.on("message_received", (event, ctx) => {
    // Check if this is a callback_data message from Telegram
    const metadata = (event as any).metadata ?? {};
    const callbackData = metadata.callbackData
      ?? metadata.callback_data
      ?? metadata.inlineData;

    if (!callbackData || typeof callbackData !== "string") {
      return; // Not a callback — let it flow to LLM
    }

    if (!isFastLaneCallback(callbackData)) {
      return; // Unknown callback — let LLM handle
    }

    // Execute fast lane
    const result = execFastLane(pacmanDir, `callback ${callbackData}`);
    if (!result) {
      return; // Failed — fall through to LLM
    }

    // Return the reply directly, bypassing LLM
    return fastLaneToReply(result);
  }, { priority: 100 }); // High priority — run before other hooks
}
```

## Register the Plugin in OpenClaw

Add to `~/.openclaw/openclaw.json` in the `plugins` section:

```json
{
  "plugins": {
    "allow": ["telegram", "pacman-fastlane"],
    "entries": {
      "pacman-fastlane": {
        "enabled": true,
        "pacmanDir": "/Users/cdi/Developer/pacman"
      }
    },
    "installs": {
      "pacman-fastlane": {
        "source": "local",
        "installPath": "/Users/cdi/.openclaw/extensions/pacman-fastlane"
      }
    }
  }
}
```

Then restart the gateway: `gateway restart`

## How It Works

1. **Slash commands** (`/portfolio`, `/swap`, `/price`, etc.):
   - `registerCommand()` handlers fire **before the LLM**
   - Handler calls `./launch.sh tg portfolio` (or swap, price, etc.)
   - Returns pre-formatted HTML + buttons via `ReplyPayload`
   - LLM is never invoked

2. **Inline button presses** (callback_data like `swap`, `sf:0.0.456858`, etc.):
   - `message_received` hook fires at priority 100 (before LLM)
   - Checks if callback_data matches a known pattern
   - If yes: calls `./launch.sh tg callback <data>`, returns formatted reply
   - If no: falls through to LLM for natural language handling

3. **Natural language** ("buy some bitcoin", "what's my balance?"):
   - No callback_data, not a slash command
   - Falls through to the LLM agent as normal
   - LLM reads SKILL.md, runs commands, formats response

## Testing

After installation, verify in Telegram:

1. Send `/start` → should get instant welcome with button grid (< 500ms)
2. Tap "💱 Swap" → should get instant token picker (< 500ms)
3. Tap "⟐ HBAR" → should get instant "To" picker (< 500ms)
4. Type "what is HBAR?" → should go through LLM (1-3 seconds, conversational)

If buttons still go through the LLM, check:
- `gateway restart` was run after config change
- Plugin is in `plugins.allow` array
- `pacmanDir` points to correct path
- `./launch.sh tg swap` works from command line

## Critical Notes

- **callback_data is max 64 bytes** (Telegram limit). Our patterns are compact (e.g. `sf:0.0.456858`) and fit easily.
- **The `channelData.telegram.buttons` path** is how OpenClaw passes inline keyboards. If this doesn't work in your OpenClaw version, try putting buttons directly on the ReplyPayload or using the `[[buttons:...]]` line directive format.
- **Empty text return** from registerCommand means "I didn't handle this, let the default handler proceed." This is the fallback mechanism.
- **The message_received hook** may need adjustment depending on how OpenClaw surfaces callback_data in the event object. Check `event.metadata` keys. The plugin tries three common key names.
