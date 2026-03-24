#!/usr/bin/env python3
"""
HCS-10 OpenConvAI — Hedera-Native Agent Messaging
==================================================

Implements the HCS-10 standard by Hashgraph Online for agent-to-agent communication
on the Hedera Consensus Service (HCS).

Wire format (every message submitted to an HCS topic):
    {"p": "hcs-10", "op": "<operation>", "operator_id": "<topicId>@<accountId>", ...}

Operations:
    connection_request   → sent to another agent's inbound topic to initiate a connection
    connection_created   → reply confirming connection, includes dedicated connection topic
    message              → send data over an established connection topic
    close_connection     → terminate a session

Topics:
    inbound_topic    — your public inbox. NO submit_key so anyone can post here.
                       Memo: hcs-10:0:0:0:{accountId}
    connection_topic — created per accepted connection. Open submit_key (both parties write).
                       Memo: hcs-10:1:0:2:{peerInboundTopicId}:{connectionId}

State is persisted to data/hcs10_connections.json.

References:
    https://github.com/hashgraph-online/standards-sdk  (hcs-10 spec, TS implementation)
"""

import json
import time
import base64
import threading
import requests
from typing import Optional, List, Dict, Callable
from pathlib import Path

from src.core.base_plugin import BasePlugin
from src.logger import logger

HCS10_PROTOCOL = "hcs-10"
MAX_MESSAGE_BYTES = 950   # HCS max ~1KB; stay safely under
POLL_INTERVAL_SEC = 15
STATE_FILE = Path(__file__).parent.parent.parent.parent / "data" / "hcs10_connections.json"


class Hcs10Agent(BasePlugin):
    """
    HCS-10 OpenConvAI agent plugin.

    Manages your inbound topic (public inbox) and a set of per-session connection
    topics. The background thread polls for new messages and fires registered handlers.

    Usage:
        agent = app.hcs10_agent                      # access via controller property
        agent.create_inbound_topic()                 # one-time setup
        agent.connect_to("0.0.XXXXX")                # request a connection
        agent.send_message("1", '{"hello": "world"}')
        agent.register_handler(my_fn)                # fn(connection_id, sender, data, raw)
        agent.start_plugin()                         # begin listening
    """

    def __init__(self, app):
        super().__init__(app, "HCS10")
        self._state_lock = threading.Lock()
        self._state = self._load_state()
        self._message_handlers: List[Callable] = []
        network = getattr(app.config, "network", "mainnet")
        self._mirror = (
            "https://mainnet-public.mirrornode.hedera.com"
            if network == "mainnet"
            else "https://testnet-public.mirrornode.hedera.com"
        )

    # ── Identity ──────────────────────────────────────────────────────────────

    @property
    def inbound_topic_id(self) -> Optional[str]:
        return (
            self._state.get("inbound_topic_id")
            or getattr(self.app.config, "hcs_inbound_topic_id", None)
        )

    @property
    def connections(self) -> Dict:
        return self._state.get("connections", {})

    @property
    def operator_id(self) -> str:
        """HCS-10 identity string: <inboundTopicId>@<accountId>"""
        return f"{self.inbound_topic_id}@{self.app.config.hedera_account_id}"

    # ── State ─────────────────────────────────────────────────────────────────

    def _load_state(self) -> dict:
        try:
            if STATE_FILE.exists():
                return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
        return {"inbound_topic_id": None, "connections": {}, "pending_requests": {}}

    def _save_state(self):
        try:
            STATE_FILE.write_text(json.dumps(self._state, indent=2))
        except Exception as e:
            logger.error(f"[HCS10] Failed to save state: {e}")

    # ── Topic Management ──────────────────────────────────────────────────────

    def create_inbound_topic(self) -> Optional[str]:
        """
        Create a public inbound topic (no submit_key — anyone can post here).
        You hold the admin key so you can update/delete it later.
        The topic ID is saved to HCS_INBOUND_TOPIC_ID in .env.
        """
        from hiero_sdk_python.consensus.topic_create_transaction import TopicCreateTransaction
        from src.config import SpaceLordConfig
        try:
            client = self.app.account_manager.client
            account_id = self.app.config.hedera_account_id
            memo = f"hcs-10:0:0:0:{account_id}"
            tx = (
                TopicCreateTransaction()
                .set_memo(memo)
                .set_admin_key(client.operator_private_key.public_key())
                # No set_submit_key → open for all senders
            )
            tx.freeze_with(client)
            response = tx.execute(client)
            receipt = response.get_receipt(client) if hasattr(response, "get_receipt") else response
            if receipt.topic_id:
                topic_id = str(receipt.topic_id)
                with self._state_lock:
                    self._state["inbound_topic_id"] = topic_id
                    self._save_state()
                SpaceLordConfig.set_env_value("HCS_INBOUND_TOPIC_ID", topic_id)
                logger.info(f"[HCS10] Inbound topic created: {topic_id}")
                return topic_id
        except Exception as e:
            logger.error(f"[HCS10] Failed to create inbound topic: {e}")
        return None

    def _create_connection_topic(self, peer_inbound_topic_id: str, connection_id: int) -> Optional[str]:
        """Create a dedicated connection topic for a session (open submit_key — both parties write)."""
        from hiero_sdk_python.consensus.topic_create_transaction import TopicCreateTransaction
        try:
            client = self.app.account_manager.client
            memo = f"hcs-10:1:0:2:{peer_inbound_topic_id}:{connection_id}"
            tx = (
                TopicCreateTransaction()
                .set_memo(memo)
                .set_admin_key(client.operator_private_key.public_key())
                # No submit_key — both parties can post
            )
            tx.freeze_with(client)
            response = tx.execute(client)
            receipt = response.get_receipt(client) if hasattr(response, "get_receipt") else response
            if receipt.topic_id:
                return str(receipt.topic_id)
        except Exception as e:
            logger.error(f"[HCS10] Failed to create connection topic: {e}")
        return None

    # ── Outbound Operations ───────────────────────────────────────────────────

    def connect_to(self, peer_inbound_topic_id: str, memo: str = "") -> bool:
        """
        Send a connection_request to another agent's inbound topic.
        They will respond with connection_created on their inbound topic (or yours).
        Start the listener to receive the response.
        """
        if not self.inbound_topic_id:
            logger.error("[HCS10] No inbound topic. Run 'hcs10 setup' first.")
            return False
        payload: Dict = {
            "p": HCS10_PROTOCOL,
            "op": "connection_request",
            "operator_id": self.operator_id,
        }
        if memo:
            payload["m"] = memo
        if self._submit_to_topic(peer_inbound_topic_id, payload):
            # Track as pending — will be confirmed when connection_created arrives
            with self._state_lock:
                if "pending_requests" not in self._state:
                    self._state["pending_requests"] = {}
                # Key by timestamp; will be matched to confirmed_request_id later
                self._state["pending_requests"][str(int(time.time()))] = {
                    "peer_inbound_topic_id": peer_inbound_topic_id,
                    "sent_at": int(time.time()),
                }
                self._save_state()
            return True
        return False

    def send_message(self, connection_id: str, data: str) -> bool:
        """Send a message over an established connection topic."""
        conn = self.connections.get(connection_id)
        if not conn:
            logger.error(f"[HCS10] No connection: {connection_id}")
            return False
        if conn.get("status") != "active":
            logger.error(f"[HCS10] Connection {connection_id} is not active.")
            return False
        if len(data.encode("utf-8")) > MAX_MESSAGE_BYTES:
            logger.warning("[HCS10] Message exceeds 950 bytes and will be truncated. Large message support (hcs://) coming soon.")
            data = data.encode("utf-8")[:MAX_MESSAGE_BYTES].decode("utf-8", errors="ignore")
        payload = {
            "p": HCS10_PROTOCOL,
            "op": "message",
            "operator_id": self.operator_id,
            "data": data,
        }
        return self._submit_to_topic(conn["connection_topic_id"], payload)

    def close_connection(self, connection_id: str, reason: str = "") -> bool:
        """Close an active connection and notify the peer."""
        conn = self.connections.get(connection_id)
        if not conn:
            return False
        payload: Dict = {
            "p": HCS10_PROTOCOL,
            "op": "close_connection",
            "operator_id": self.operator_id,
            "connection_id": int(connection_id) if connection_id.isdigit() else connection_id,
        }
        if reason:
            payload["reason"] = reason
        ok = self._submit_to_topic(conn["connection_topic_id"], payload)
        if ok:
            with self._state_lock:
                self._state["connections"][connection_id]["status"] = "closed"
                self._save_state()
        return ok

    # ── Inbound Handling ──────────────────────────────────────────────────────

    def _handle_inbound_op(self, parsed: dict, seq: int):
        """Route an inbound HCS-10 operation by op type."""
        op = parsed.get("op")
        if op == "connection_request":
            self._accept_connection(parsed, seq)
        elif op == "connection_created":
            self._finalize_connection(parsed)
        elif op == "close_connection":
            self._on_peer_closed(parsed)

    def _accept_connection(self, req: dict, request_seq: int):
        """Auto-accept an inbound connection_request."""
        peer_operator_id = req.get("operator_id", "")
        if "@" in peer_operator_id:
            peer_inbound_topic_id, peer_account_id = peer_operator_id.split("@", 1)
        else:
            peer_inbound_topic_id = None
            peer_account_id = peer_operator_id

        logger.info(f"[HCS10] Connection request from {peer_operator_id} (seq {request_seq})")

        connection_topic_id = self._create_connection_topic(
            peer_inbound_topic_id or "unknown", request_seq
        )
        if not connection_topic_id:
            logger.error("[HCS10] Could not create connection topic — rejecting request.")
            return

        connection_id = str(request_seq)
        reply: Dict = {
            "p": HCS10_PROTOCOL,
            "op": "connection_created",
            "operator_id": self.operator_id,
            "connection_topic_id": connection_topic_id,
            "connected_account_id": self.app.config.hedera_account_id,
            "confirmed_request_id": request_seq,
        }
        # Reply on requester's inbound topic so they see the confirmation
        reply_target = peer_inbound_topic_id or self.inbound_topic_id
        if self._submit_to_topic(reply_target, reply):
            with self._state_lock:
                self._state["connections"][connection_id] = {
                    "connection_topic_id": connection_topic_id,
                    "peer_account_id": peer_account_id,
                    "peer_inbound_topic_id": peer_inbound_topic_id,
                    "status": "active",
                    "last_seq": 0,
                    "initiated_by": "peer",
                    "created_at": int(time.time()),
                }
                self._save_state()
            logger.info(f"[HCS10] Connection {connection_id} active. Topic: {connection_topic_id}")

    def _finalize_connection(self, msg: dict):
        """Process connection_created received in response to our outbound request."""
        conn_topic = msg.get("connection_topic_id")
        peer_account = msg.get("connected_account_id")
        req_id = msg.get("confirmed_request_id")
        connection_id = str(req_id)

        with self._state_lock:
            # Remove any matching pending request entry
            self._state.setdefault("pending_requests", {})
            # Store as active connection
            self._state["connections"][connection_id] = {
                "connection_topic_id": conn_topic,
                "peer_account_id": peer_account,
                "peer_inbound_topic_id": msg.get("operator_id", "").split("@")[0],
                "status": "active",
                "last_seq": 0,
                "initiated_by": "self",
                "created_at": int(time.time()),
            }
            self._save_state()
        logger.info(f"[HCS10] Connection {connection_id} confirmed. Topic: {conn_topic}")

    def _on_peer_closed(self, msg: dict, connection_id: str = None):
        """Handle close_connection received from a peer."""
        if not connection_id:
            # Try to find connection by sender
            sender = msg.get("operator_id", "")
            for cid, conn in self.connections.items():
                if conn.get("peer_inbound_topic_id") and sender.startswith(conn["peer_inbound_topic_id"]):
                    connection_id = cid
                    break
        if connection_id and connection_id in self._state.get("connections", {}):
            with self._state_lock:
                self._state["connections"][connection_id]["status"] = "closed"
                self._save_state()
            logger.info(f"[HCS10] Connection {connection_id} closed by peer.")

    def _dispatch_message(self, connection_id: str, parsed: dict):
        """Handle a message op on a connection topic."""
        op = parsed.get("op")
        if op == "message":
            data = parsed.get("data", "")
            sender = parsed.get("operator_id", "unknown")
            for handler in self._message_handlers:
                try:
                    handler(connection_id=connection_id, sender=sender, data=data, raw=parsed)
                except Exception as e:
                    logger.error(f"[HCS10] Handler error: {e}")
        elif op == "close_connection":
            self._on_peer_closed(parsed, connection_id=connection_id)

    # ── Polling Loop ──────────────────────────────────────────────────────────

    def run_loop(self):
        """Poll inbound topic and all active connection topics for new messages."""
        if self.inbound_topic_id:
            self._poll_topic(self.inbound_topic_id, is_inbound=True)
        for conn_id, conn in list(self.connections.items()):
            if conn.get("status") == "active":
                self._poll_topic(
                    conn["connection_topic_id"],
                    is_inbound=False,
                    connection_id=conn_id,
                )
        time.sleep(POLL_INTERVAL_SEC)

    def _poll_topic(self, topic_id: str, is_inbound: bool, connection_id: str = None):
        """Fetch new HCS-10 messages since last known sequence number."""
        seq_key = f"_seq_{topic_id}"
        last_seq = self._state.get(seq_key, 0)
        try:
            url = (
                f"{self._mirror}/api/v1/topics/{topic_id}/messages"
                f"?limit=25&order=asc&sequencenumber=gt:{last_seq}"
            )
            resp = requests.get(url, timeout=10)
            if resp.status_code != 200:
                return
            messages = resp.json().get("messages", [])
            for msg in messages:
                seq = msg.get("sequence_number", 0)
                try:
                    raw_b64 = msg.get("message", "")
                    decoded = base64.b64decode(raw_b64).decode("utf-8")
                    parsed = json.loads(decoded)
                    if parsed.get("p") != HCS10_PROTOCOL:
                        continue
                    if is_inbound:
                        self._handle_inbound_op(parsed, seq)
                    else:
                        self._dispatch_message(connection_id, parsed)
                except Exception:
                    pass
                if seq > last_seq:
                    last_seq = seq
            with self._state_lock:
                self._state[seq_key] = last_seq
                self._save_state()
        except Exception as e:
            logger.error(f"[HCS10] Poll error on {topic_id}: {e}")

    # ── Handler Registration ──────────────────────────────────────────────────

    def register_handler(self, fn: Callable):
        """
        Register a callback for incoming messages.
        Signature: fn(connection_id: str, sender: str, data: str, raw: dict)
        """
        self._message_handlers.append(fn)

    # ── Read-Only Access ──────────────────────────────────────────────────────

    def read_topic(self, topic_id: str, limit: int = 20) -> List[dict]:
        """
        Read recent messages from any HCS topic (no auth required — Mirror Node).
        Returns HCS-10 messages decoded where possible, raw bytes otherwise.
        """
        try:
            url = f"{self._mirror}/api/v1/topics/{topic_id}/messages?limit={limit}&order=desc"
            resp = requests.get(url, timeout=10)
            if resp.status_code != 200:
                return []
            out = []
            for msg in resp.json().get("messages", []):
                seq = msg.get("sequence_number", 0)
                ts = msg.get("consensus_timestamp", "")
                try:
                    decoded = base64.b64decode(msg.get("message", "")).decode("utf-8")
                    parsed = json.loads(decoded)
                    out.append({
                        "seq": seq,
                        "ts": ts,
                        "protocol": parsed.get("p"),
                        "op": parsed.get("op"),
                        "sender": parsed.get("operator_id"),
                        "data": parsed.get("data"),
                        "raw": parsed,
                    })
                except Exception:
                    out.append({"seq": seq, "ts": ts, "raw_b64": msg.get("message", "")})
            return out
        except Exception as e:
            logger.error(f"[HCS10] read_topic {topic_id}: {e}")
            return []

    # ── Submit ────────────────────────────────────────────────────────────────

    def _submit_to_topic(self, topic_id: str, payload: dict) -> bool:
        from hiero_sdk_python.consensus.topic_message_submit_transaction import TopicMessageSubmitTransaction
        from hiero_sdk_python.consensus.topic_id import TopicId
        try:
            client = self.app.account_manager.client
            msg = json.dumps(payload, separators=(",", ":"))
            tx = (
                TopicMessageSubmitTransaction()
                .set_topic_id(TopicId.from_string(topic_id))
                .set_message(msg)
            )
            tx.freeze_with(client)
            response = tx.execute(client)
            receipt = response.get_receipt(client) if hasattr(response, "get_receipt") else response
            return receipt.status == 22  # SUCCESS
        except Exception as e:
            logger.error(f"[HCS10] Submit to {topic_id} failed: {e}")
            return False

    # ── Status ────────────────────────────────────────────────────────────────

    def get_status(self) -> dict:
        s = super().get_status()
        s.update({
            "inbound_topic_id": self.inbound_topic_id,
            "active_connections": sum(
                1 for c in self.connections.values() if c.get("status") == "active"
            ),
            "total_connections": len(self.connections),
        })
        return s
