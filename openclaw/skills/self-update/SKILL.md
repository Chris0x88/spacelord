---
name: self-update
description: Pull latest codebase knowledge into your workspace
version: 1.0.0
triggers:
  - "update yourself"
  - "sync your knowledge"
  - "check for updates"
  - "refresh your skills"
  - "are you up to date"
---

# Self-Update Skill

Your knowledge of Pacman comes from files in this workspace (`openclaw/`).
The Pacman CLI is developed separately and may add commands, flags, or features
you don't know about yet.

## How to Sync

Run this command:
```
./launch.sh agent-sync
```

This reads the live codebase and regenerates your workspace files:
- **TOOLS.md** — command reference, account IDs, network info, full CLI help
- **AGENTS.md** — architecture guide, plugin list, Hedera rules
- **BOOTSTRAP.md** — safety limits from governance.json

Files it preserves (developer-owned, never overwritten):
- SOUL.md, IDENTITY.md, USER.md, HEARTBEAT.md

## When to Run

- After the developer says "I added something" or "things changed"
- When a command fails with "unknown command"
- On `/start` if you haven't synced recently
- After any session where you noticed gaps in your knowledge

## Preview Mode

To see what would change without writing:
```
./launch.sh agent-sync --diff
```

## What This Cannot Update

SKILL.md (your main instruction set) is a symlink to the repo root.
The developer updates it directly. If you notice SKILL.md is missing
guidance for a feature that exists, tell the developer:

"I can run `<command>` but SKILL.md doesn't have a decision tree for it.
Can you add guidance?"
