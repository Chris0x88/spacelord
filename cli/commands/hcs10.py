#!/usr/bin/env python3
"""
CLI Commands: HCS-10 Agent Messaging
=====================================

Hedera-native agent-to-agent communication using the HCS-10 OpenConvAI standard.
https://github.com/hashgraph-online/standards-sdk

Usage:
  hcs10 setup                      → create your public inbound topic (one-time)
  hcs10 connect <topic_id>         → connect to another agent's inbound topic
  hcs10 send <connection_id> <msg> → send a message to a connected agent
  hcs10 close <connection_id>      → close a connection
  hcs10 connections                → list all connections
  hcs10 read <topic_id> [limit]    → read messages from any HCS topic
  hcs10 start                      → start the background listener
  hcs10 status                     → show HCS-10 status
"""

from cli.display import C
from src.logger import logger


def cmd_hcs10(app, args):
    if not args:
        _print_help()
        return

    sub = args[0].lower()
    dispatch = {
        "setup":       _cmd_setup,
        "connect":     _cmd_connect,
        "send":        _cmd_send,
        "close":       _cmd_close,
        "connections": _cmd_connections,
        "read":        _cmd_read,
        "start":       _cmd_start,
        "status":      _cmd_status,
    }
    fn = dispatch.get(sub)
    if fn:
        fn(app, args[1:])
    else:
        _print_help()


def _cmd_setup(app, args):
    """Create your public inbound topic (one-time setup)."""
    agent = _get_agent(app)
    if not agent:
        return
    if agent.inbound_topic_id:
        print(f"\n  {C.WARN}⚠  Inbound topic already set: {C.BOLD}{agent.inbound_topic_id}{C.R}")
        print(f"  {C.MUTED}To create a new one, remove HCS_INBOUND_TOPIC_ID from .env first.{C.R}")
        return
    print(f"\n  {C.MUTED}Creating public inbound topic (no submit_key — open for all senders)...{C.R}")
    topic_id = agent.create_inbound_topic()
    if topic_id:
        print(f"  {C.OK}✅ Inbound topic: {C.BOLD}{topic_id}{C.R}")
        print(f"  {C.MUTED}Saved to HCS_INBOUND_TOPIC_ID in .env{C.R}")
        print(f"  {C.MUTED}Share this topic ID so other agents can connect to you.{C.R}\n")
    else:
        print(f"  {C.ERR}✗{C.R} Failed to create inbound topic.\n")


def _cmd_connect(app, args):
    """Send a connection_request to another agent's inbound topic."""
    if not args:
        print(f"  {C.ERR}✗{C.R} Usage: {C.TEXT}hcs10 connect <inbound_topic_id> [memo]{C.R}")
        return
    agent = _get_agent(app)
    if not agent:
        return
    if not agent.inbound_topic_id:
        print(f"  {C.WARN}⚠  You need an inbound topic first. Run: {C.TEXT}hcs10 setup{C.R}")
        return
    peer_topic = args[0]
    memo = " ".join(args[1:]) if len(args) > 1 else ""
    print(f"\n  {C.MUTED}Sending connection request to {peer_topic}...{C.R}")
    if agent.connect_to(peer_topic, memo=memo):
        print(f"  {C.OK}✅ Connection request sent.{C.R}")
        print(f"  {C.MUTED}Start the listener to receive confirmation: {C.TEXT}hcs10 start{C.R}\n")
    else:
        print(f"  {C.ERR}✗{C.R} Failed to send connection request.\n")


def _cmd_send(app, args):
    """Send a message over an established connection."""
    if len(args) < 2:
        print(f"  {C.ERR}✗{C.R} Usage: {C.TEXT}hcs10 send <connection_id> <message>{C.R}")
        return
    agent = _get_agent(app)
    if not agent:
        return
    conn_id = args[0]
    message = " ".join(args[1:])
    if agent.send_message(conn_id, message):
        print(f"  {C.OK}✅ Message sent on connection {conn_id}.{C.R}")
    else:
        print(f"  {C.ERR}✗{C.R} Failed to send message.")


def _cmd_close(app, args):
    """Close an active connection."""
    if not args:
        print(f"  {C.ERR}✗{C.R} Usage: {C.TEXT}hcs10 close <connection_id> [reason]{C.R}")
        return
    agent = _get_agent(app)
    if not agent:
        return
    conn_id = args[0]
    reason = " ".join(args[1:]) if len(args) > 1 else ""
    if agent.close_connection(conn_id, reason=reason):
        print(f"  {C.OK}✅ Connection {conn_id} closed.{C.R}")
    else:
        print(f"  {C.ERR}✗{C.R} Failed to close connection (may already be closed).")


def _cmd_connections(app, args):
    """List all connections."""
    agent = _get_agent(app)
    if not agent:
        return
    connections = agent.connections
    if not connections:
        print(f"\n  {C.MUTED}No connections yet.{C.R}")
        print(f"  {C.MUTED}Use {C.TEXT}hcs10 connect <topic_id>{C.MUTED} to start one.{C.R}\n")
        return
    print(f"\n  {C.BOLD}{C.TEXT}HCS-10 CONNECTIONS{C.R}")
    print(f"  {C.CHROME}{'─' * 64}{C.R}")
    for conn_id, conn in connections.items():
        status = conn.get("status", "?")
        sc = C.OK if status == "active" else C.MUTED
        direction = "outbound →" if conn.get("initiated_by") == "self" else "← inbound"
        import time as _t
        age = int((_t.time() - conn.get("created_at", _t.time())) / 3600)
        age_str = f"{age}h ago" if age > 0 else "just now"
        print(f"  {C.ACCENT}{conn_id:<6}{C.R}  {sc}{status:<8}{C.R}  {C.MUTED}{direction}  {age_str}{C.R}")
        print(f"         peer:  {conn.get('peer_account_id', '?')}")
        print(f"         topic: {conn.get('connection_topic_id', '?')}")
    print(f"  {C.CHROME}{'─' * 64}{C.R}\n")


def _cmd_read(app, args):
    """Read messages from any HCS topic (read-only, no auth needed)."""
    if not args:
        print(f"  {C.ERR}✗{C.R} Usage: {C.TEXT}hcs10 read <topic_id> [limit]{C.R}")
        return
    agent = _get_agent(app)
    if not agent:
        return
    topic_id = args[0]
    limit = int(args[1]) if len(args) > 1 and args[1].isdigit() else 10
    print(f"\n  {C.MUTED}Reading {topic_id} (last {limit} messages)...{C.R}")
    messages = agent.read_topic(topic_id, limit=limit)
    if not messages:
        print(f"  {C.MUTED}No messages found.{C.R}\n")
        return
    print(f"\n  {C.BOLD}{C.TEXT}MESSAGES — {topic_id}{C.R}")
    print(f"  {C.CHROME}{'─' * 64}{C.R}")
    for m in reversed(messages):
        op = m.get("op") or "raw"
        sender = m.get("sender") or ""
        data = m.get("data") or ""
        ts = (m.get("ts") or "")[:19].replace("T", " ")
        proto = m.get("protocol", "")
        label = f"[{proto}] {op}" if proto else op
        print(f"  {C.ACCENT}{label:<28}{C.R}  {C.MUTED}{ts}{C.R}")
        if sender:
            print(f"    from: {sender}")
        if data:
            preview = data[:120] + ("…" if len(data) > 120 else "")
            print(f"    data: {preview}")
    print(f"  {C.CHROME}{'─' * 64}{C.R}\n")


def _cmd_start(app, args):
    """Start the HCS-10 background listener."""
    agent = _get_agent(app)
    if not agent:
        return
    if not agent.inbound_topic_id:
        print(f"  {C.WARN}⚠  No inbound topic. Run {C.TEXT}hcs10 setup{C.WARN} first.{C.R}")
        return
    if agent.running and agent.is_alive():
        print(f"  {C.MUTED}Listener already running.{C.R}")
        return
    agent.start_plugin()
    from src.plugins.hcs10.plugin import POLL_INTERVAL_SEC
    print(f"  {C.OK}✅ HCS-10 listener started.{C.R}")
    print(f"  {C.MUTED}Polling every {POLL_INTERVAL_SEC}s — inbound + {len(agent.connections)} connection topic(s){C.R}")


def _cmd_status(app, args):
    """Show HCS-10 status."""
    agent = _get_agent(app)
    if not agent:
        return
    s = agent.get_status()
    print(f"\n  {C.BOLD}{C.TEXT}HCS-10 STATUS{C.R}")
    print(f"  {C.CHROME}{'─' * 44}{C.R}")
    inbound = s.get("inbound_topic_id") or f"{C.WARN}Not set — run hcs10 setup{C.R}"
    print(f"  Inbound topic:      {inbound}")
    print(f"  Listener:           {'running' if s.get('running') else C.MUTED + 'stopped' + C.R}")
    print(f"  Active connections: {s.get('active_connections', 0)}")
    print(f"  Total connections:  {s.get('total_connections', 0)}")
    print(f"  {C.CHROME}{'─' * 44}{C.R}\n")


def _get_agent(app):
    try:
        return app.hcs10_agent
    except AttributeError:
        print(f"  {C.ERR}✗{C.R} HCS-10 plugin not initialized.")
        return None


def _print_help():
    print(f"""
  {C.BOLD}{C.TEXT}HCS-10 AGENT MESSAGING (OpenConvAI){C.R}
  {C.CHROME}{'─' * 52}{C.R}
  {C.ACCENT}setup{C.R}                    Create your public inbound topic
  {C.ACCENT}connect <topic_id>{C.R}       Request a connection to another agent
  {C.ACCENT}send <id> <msg>{C.R}          Send a message to a connected agent
  {C.ACCENT}close <id> [reason]{C.R}      Close a connection
  {C.ACCENT}connections{C.R}              List all connections and their status
  {C.ACCENT}read <topic_id> [n]{C.R}      Read messages from any HCS topic
  {C.ACCENT}start{C.R}                    Start the background listener
  {C.ACCENT}status{C.R}                   Show HCS-10 agent status
  {C.CHROME}{'─' * 52}{C.R}
    """)
