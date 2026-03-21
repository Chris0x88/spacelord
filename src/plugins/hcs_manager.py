"""
Pacman HCS Manager Plugin
=========================

Handles Hedera Consensus Service (HCS) operations:
- Topic Creation and Management
- Message Broadcasting (Investment Signals, etc.)
- Message Monitoring/Reading
- Fee Collection for Topic Access (Walled Garden)
"""

import json
from typing import Optional, List, Dict
from src.logger import logger
from src.core.base_plugin import BasePlugin

# Optional dependency — HCS operations require hiero-sdk-python.
# Basic plugin load still works without it; operations fail gracefully.
try:
    from hiero_sdk_python.consensus.topic_create_transaction import TopicCreateTransaction
    from hiero_sdk_python.consensus.topic_message_submit_transaction import TopicMessageSubmitTransaction
    from hiero_sdk_python.consensus.topic_id import TopicId
    from hiero_sdk_python.account.account_id import AccountId
    _HAS_HIERO_SDK = True
except Exception:
    # Catch all exceptions (ImportError, ModuleNotFoundError, AttributeError, etc.)
    # to ensure _HAS_HIERO_SDK is always defined
    _HAS_HIERO_SDK = False

class HcsManager(BasePlugin):
    """
    Manages HCS topics and messaging for the Pacman ecosystem.
    """
    
    def __init__(self, app):
        super().__init__(app, "HCS")
        self.topic_id: Optional[str] = getattr(app.config, "hcs_topic_id", None)
        
    def create_topic(self, memo: str = "Pacman HCS Topic") -> Optional[str]:
        """Create a new HCS topic and set it as the active one."""
        try:
            client = self.app.account_manager.client
            tx = TopicCreateTransaction() \
                .set_topic_memo(memo) \
                .set_admin_key(client.operator_public_key) \
                .set_submit_key(client.operator_public_key)
            
            tx.freeze_with(client)
            response = tx.execute(client)
            receipt = response.get_receipt(client) if hasattr(response, "get_receipt") else response

            if receipt.topic_id:
                topic_id = str(receipt.topic_id)
                self.topic_id = topic_id
                from src.config import PacmanConfig
                PacmanConfig.set_env_value("HCS_TOPIC_ID", topic_id)
                logger.info(f"✅ Created HCS Topic: {topic_id}")
                return topic_id
            return None
        except Exception as e:
            logger.error(f"❌ Failed to create HCS topic: {e}")
            return None

    def run_loop(self):
        """No background processing needed for now, just keep the thread alive."""
        import time
        time.sleep(60)

    def submit_message(self, message: str, topic_id: Optional[str] = None) -> bool:
        """Submit a message to an HCS topic."""
        if not _HAS_HIERO_SDK:
            logger.error("❌ hiero_sdk_python not installed — cannot submit HCS message.")
            return False

        target_topic = topic_id or self.topic_id
        if not target_topic:
            logger.error("❌ No HCS Topic ID configured.")
            return False

        try:
            client = self.app.account_manager.client
            tx = TopicMessageSubmitTransaction() \
                .set_topic_id(TopicId.from_string(target_topic)) \
                .set_message(message)

            tx.freeze_with(client)

            # Topics with submit_key need explicit signing with the key that
            # CREATED the topic. The operator (MAIN_OPERATOR_KEY) may differ from
            # the signing key (PRIVATE_KEY) that was used for topic creation.
            # Always sign with PRIVATE_KEY to match the topic's submit_key.
            import os
            signing_key = os.getenv("PRIVATE_KEY", "").strip().replace("0x", "")
            if signing_key and len(signing_key) == 64:
                from hiero_sdk_python.crypto.private_key import PrivateKey as _PK
                key_bytes = bytes.fromhex(signing_key)
                pk = _PK.from_bytes_ecdsa(key_bytes) if len(key_bytes) == 32 else _PK.from_string(signing_key)
                tx.sign(pk)

            response = tx.execute(client)
            receipt = response.get_receipt(client) if hasattr(response, "get_receipt") else response

            status = receipt.status
            # Status 22 = SUCCESS; handle both int and enum
            if status == 22 or str(status) == "22" or (hasattr(status, 'name') and status.name == 'SUCCESS'):
                return True
            else:
                _status_names = {7: "INVALID_SIGNATURE", 11: "INVALID_TOPIC_ID", 22: "SUCCESS"}
                status_int = int(status) if isinstance(status, int) else status
                label = _status_names.get(status_int, str(status))
                logger.error(f"❌ HCS message submission failed with status {status} ({label})")
                if status_int == 7:
                    logger.error(
                        "   Topic %s submit_key doesn't match the current operator key. "
                        "Check that HEDERA_ACCOUNT_ID and PRIVATE_KEY in .env are correct.",
                        target_topic,
                    )
                return False
        except Exception as e:
            logger.error(f"❌ Failed to submit HCS message: {e}", exc_info=True)
            return False

    def submit_with_fee(self, message: str, collector_id: str, fee_hbar: float = 0.01) -> bool:
        """
        Submit a message on behalf of a user after they pay a fee.
        This is a mock for the 'walled garden' fee collection.
        In a real app, this would be a backend service or smart contract.
        """
        logger.info(f"💰 Collecting {fee_hbar} HBAR fee to {collector_id} for HCS access...")
        # Simulate / Check for payment (In this CLI version, we just log it)
        # In a real implementation, we would wait for a transaction or use a smart contract.
        success = self.submit_message(message)
        if success:
            logger.info(f"✅ Fee collected and message submitted to walled garden.")
        return success

    def broadcast_signal(self, signal_type: str, data: Dict) -> bool:
        """Broadcast an investment signal as a JSON-encoded HCS message.

        Schema v1.1 — designed for both human-readable dashboards and
        machine consumption by subscribing agents.
        """
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        # Display titles for common signal types
        _TITLES = {
            "REBALANCE_BUY_BTC": "🚀 BUY BTC",
            "REBALANCE_SELL_BTC": "📉 SELL BTC",
            "DAILY_HEARTBEAT": "📊 DAILY SIGNAL",
            "SIGNAL_ALERT": "⚠️ ALERT",
        }
        payload = {
            "version": "1.1",
            "type": "SIGNAL",
            "signal": signal_type,
            "display_title": _TITLES.get(signal_type, f"📡 {signal_type}"),
            "sender": self.app.account_id,
            "timestamp_utc": now.strftime("%Y-%m-%d %H:%M:%S"),
            "timestamp_unix": int(now.timestamp()),
            "data": data,
        }
        return self.submit_message(json.dumps(payload))

    def get_messages(self, limit: int = 10) -> List[Dict]:
        """Fetch recent messages from the HCS topic using Mirror Node."""
        if not self.topic_id:
            return []
            
        try:
            import requests
            network = self.app.config.network
            base_url = "https://mainnet-public.mirrornode.hedera.com" if network == "mainnet" else "https://testnet-public.mirrornode.hedera.com"
            url = f"{base_url}/api/v1/topics/{self.topic_id}/messages?limit={limit}&order=desc"
            
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                messages = []
                import base64
                for msg in response.json().get("messages", []):
                    try:
                        raw_payload = base64.b64decode(msg['message']).decode('utf-8')
                        payload = json.loads(raw_payload)
                        messages.append({
                            "timestamp": msg['consensus_timestamp'],
                            "sender": payload.get("sender"),
                            "type": payload.get("type"),
                            "signal": payload.get("signal"),
                            "data": payload.get("data")
                        })
                    except:
                        continue
                return messages
            return []
        except Exception as e:
            logger.error(f"❌ Failed to fetch HCS messages: {e}")
            return []

    def get_status(self) -> dict:
        status = super().get_status()
        status.update({
            "topic_id": self.topic_id,
        })
        return status
