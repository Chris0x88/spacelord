#!/usr/bin/env python3
"""
CLI Commands: HCS & Messaging
=============================

Handles topic creation, message submission, and signal broadcasting.
"""

from cli.display import C
from src.logger import logger

def cmd_hcs(app, args):
    """
    Manage Hedera Consensus Service (HCS) topics and messages.
    Usage:
      hcs topic create [memo]    → create a new signal topic
      hcs send <message>         → send a message to the active topic
      hcs signal <type> <data>   → broadcast an investment signal (JSON)
      hcs status                 → show active topic info
    """
    if not args:
        print_hcs_help()
        return

    sub = args[0].lower()
    
    if sub == "topic":
        if len(args) < 2:
            print(f"  {C.ERR}✗{C.R} Usage: {C.TEXT}hcs topic create [memo]{C.R}")
            return
        if args[1].lower() == "create":
            memo = " ".join(args[2:]) if len(args) > 2 else "Pacman HCS Signal Topic"
            print(f"  {C.MUTED}Creating new HCS topic...{C.R}")
            topic_id = app.hcs_manager.create_topic(memo=memo)
            if topic_id:
                print(f"  {C.OK}✅ Created and set active Topic: {C.BOLD}{topic_id}{C.R}")
            else:
                print(f"  {C.ERR}✗{C.R} Failed to create topic.")
                
    elif sub == "send":
        if len(args) < 2:
            print(f"  {C.ERR}✗{C.R} Usage: {C.TEXT}hcs send <message>{C.R}")
            return
        msg = " ".join(args[1:])
        print(f"  {C.MUTED}Submitting message to HCS...{C.R}")
        if app.hcs_manager.submit_message(msg):
            print(f"  {C.OK}✅ Message submitted successfully.{C.R}")
        else:
            print(f"  {C.ERR}✗{C.R} Failed to submit message.")
            
    elif sub == "signal":
        if len(args) < 3:
            print(f"  {C.ERR}✗{C.R} Usage: {C.TEXT}hcs signal <type> <data_json>{C.R}")
            return
        sig_type = args[1]
        try:
            import json
            data = json.loads(" ".join(args[2:]))
        except Exception as e:
            print(f"  {C.ERR}✗{C.R} Invalid JSON data: {e}")
            return
            
        print(f"  {C.MUTED}Broadcasting {sig_type} signal...{C.R}")
        if app.hcs_manager.broadcast_signal(sig_type, data):
            print(f"  {C.OK}✅ Signal broadcast successfully.{C.R}")
        else:
            print(f"  {C.ERR}✗{C.R} Failed to broadcast signal.")
            
    elif sub == "signals":
        print(f"  {C.MUTED}Fetching recent HCS signals...{C.R}")
        messages = app.hcs_manager.get_messages(limit=5)
        if not messages:
            print(f"  {C.MUTED}No signals found on topic {C.BOLD}{app.hcs_manager.topic_id}{C.R}")
            return
            
        print(f"\n  {C.BOLD}{C.TEXT}RECENT HCS SIGNALS{C.R}")
        print(f"  {C.CHROME}{'─' * 60}{C.R}")
        for m in messages:
            sender = m.get('sender', 'Unknown')
            sig = m.get('signal', 'MESSAGE')
            print(f"  {C.ACCENT}{sig:<15}{C.R} {C.TEXT}from {sender}{C.R}")
            if m.get('data'):
                print(f"    {C.MUTED}{m['data']}{C.R}")
        print(f"  {C.CHROME}{'─' * 60}{C.R}\n")

    elif sub == "status":
        topic_id = app.hcs_manager.topic_id
        print(f"\n  {C.BOLD}{C.TEXT}HCS STATUS{C.R}")
        print(f"  {C.CHROME}{'─' * 40}{C.R}")
        print(f"  {C.TEXT}Active Topic ID: {C.R} {C.BOLD}{topic_id or 'None'}{C.R}")
        if not topic_id:
            print(f"  {C.WARN}⚠  No HCS topic configured.{C.R}")
        print(f"  {C.CHROME}{'─' * 40}{C.R}\n")
    else:
        print_hcs_help()

def print_hcs_help():
    print(f"""
  {C.BOLD}{C.TEXT}HCS COMMANDS{C.R}
  {C.CHROME}{'─' * 40}{C.R}
  {C.ACCENT}topic create{C.R}    Create a new HCS signal topic
  {C.ACCENT}send <msg>{C.R}      Submit a raw message to HCS
  {C.ACCENT}signal <t> <d>{C.R}  Broadcast structured JSON signal
  {C.ACCENT}signals{C.R}         View recent signals from the topic
  {C.ACCENT}status{C.R}          Show active topic info
  {C.CHROME}{'─' * 40}{C.R}
    """)
