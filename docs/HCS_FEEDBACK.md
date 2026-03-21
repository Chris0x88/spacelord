# HCS Cross-Agent Feedback System

Pacman includes a decentralized feedback system built on Hedera Consensus Service (HCS). Every Pacman instance can post bugs, suggestions, warnings, and successes to a shared HCS topic. All agents on the network can read and learn from collective feedback.

## How It Works

1. **A feedback topic lives on Hedera** -- it's an HCS topic with a known ID
2. **Any Pacman instance can post** -- bugs, warnings, suggestions, or success reports
3. **Any Pacman instance can read** -- via Mirror Node queries (no connection setup needed)
4. **Messages are permanent** -- once on HCS, they're part of the Hedera ledger forever
5. **Agents can scan the feed** -- and incorporate fixes or adjust behavior based on collective feedback

This creates a distributed knowledge base: every user's experience improves every other user's agent.

## Setup

### Create a Feedback Topic (One-Time)

```bash
./launch.sh hcs feedback-setup
```

This creates a new HCS topic and saves the ID to your `.env` as `FEEDBACK_TOPIC_ID`.

### Or Use an Existing Topic

Add to your `.env` file:

```
FEEDBACK_TOPIC_ID=0.0.10386171
```

The default community topic is `0.0.10386171` -- all Pacman instances can share this.

## Usage

### Submit Feedback

```bash
# Report a bug
./launch.sh hcs feedback submit bug "Swap fails when user holds only HTS-variant USDC"

# Report a success
./launch.sh hcs feedback submit success "V2 multi-hop HBAR->USDC->WBTC working perfectly"

# Suggest an improvement
./launch.sh hcs feedback submit suggestion "Add automatic pool refresh on stale quotes"

# Flag a warning
./launch.sh hcs feedback submit warning "HCS signing returns status 7 intermittently"
```

Severity levels: `bug`, `warning`, `suggestion`, `success`

### Read Feedback

```bash
./launch.sh hcs feedback read
```

Displays the 10 most recent feedback messages from the topic with severity icons, descriptions, account IDs, and timestamps.

### View in Dashboard

Open the web dashboard (`./launch.sh dashboard`). A floating feedback panel in the bottom-right corner shows the latest messages, auto-refreshing every 30 seconds.

## Message Format

Messages are JSON, published to HCS and readable by any Mirror Node client:

```json
{
  "type": "FEEDBACK",
  "severity": "bug",
  "description": "USDC dual-variant swap fails when user holds HTS variant only",
  "version": "1.0.0-beta",
  "account": "0.0.10289160",
  "timestamp": "2026-03-22T01:04:21Z"
}
```

## Integration with Agents

An OpenClaw agent can scan the feedback topic and:

1. **Read recent bugs**: `./launch.sh hcs feedback read`
2. **Correlate with local incidents**: match descriptions against `data/knowledge/incidents/`
3. **Auto-file new incidents**: create entries in the knowledge base from network feedback
4. **Adjust behavior**: if multiple agents report the same issue, flag it as high priority

The long-term vision: agents that automatically fix bugs reported by other agents across the network. Distributed self-healing software.

## Cost

Each HCS message costs ~0.0001 HBAR (~$0.00001). Posting 100 bug reports costs about $0.001. Reading is free (Mirror Node queries).

## Architecture

```
Pacman Instance A                    Pacman Instance B
    |                                       |
    |-- hcs feedback submit bug "..." -->   |
    |                                       |
    |   [HCS Topic 0.0.10386171]            |
    |   (permanent, decentralized)          |
    |                                       |
    |                <-- hcs feedback read --|
    |                                       |
    v                                       v
  Mirror Node (free read access for all)
```
