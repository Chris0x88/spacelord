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
except ImportError:
    _HAS_HIERO_SDK = False

class HcsManager(BasePlugin):
    """
    Manages HCS topics and messaging for the Pacman ecosystem.
    """
    
    def __init__(self, app):
        super().__init__(app, "HCS")
        self.topic_id: Optional[str] = app.config.hcs_topic_id
        
    def create_topic(self, memo: str = "Pacman HCS Topic") -> Optional[str]:
        """Create a new HCS topic and set it as the active one."""
        try:
            from hiero_sdk_python.crypto.private_key import PrivateKey
            
            # Reconstruct operator's public key from account manager
            pk_str = self.app.account_manager._operator_raw_key
            
            # Robust key interpretation as seen in AccountManager
            key_bytes = bytes.fromhex(pk_str)
            if len(key_bytes) == 32:
                pk = PrivateKey.from_bytes_ecdsa(key_bytes)
            else:
                pk = PrivateKey.from_string(pk_str)
            
            pub_key = pk.public_key()
            
            client = self.app.account_manager.client
            tx = TopicCreateTransaction() \
                .set_memo(memo) \
                .set_admin_key(pub_key) \
                .set_submit_key(pub_key)
            
            tx.freeze_with(client)
            response = tx.execute(client)
            
            if hasattr(response, "get_receipt"):
                receipt = response.get_receipt(client)
            else:
                receipt = response
            
            if hasattr(receipt, "topic_id") and receipt.topic_id:
                topic_id = str(receipt.topic_id)
                self.topic_id = topic_id
                from src.config import PacmanConfig
                PacmanConfig.set_env_value("HCS_TOPIC_ID", topic_id)
                logger.info(f"✅ Created HCS Topic: {topic_id}")
                return topic_id
            else:
                logger.error(f"❌ Failed to create topic. Status: {getattr(receipt, 'status', 'Unknown')}")
            return None
        except Exception as e:
            import traceback
            logger.error(f"❌ Failed to create HCS topic: {e}")
            logger.error(traceback.format_exc())
            return None

    def run_loop(self):
        """No background processing needed for now, just keep the thread alive."""
        import time
        time.sleep(60)

    def submit_message(self, message: str, topic_id: Optional[str] = None) -> bool:
        """Submit a message to an HCS topic."""
        target_topic = (topic_id or self.topic_id or "").strip("'").strip('"')
        if not target_topic:
            logger.error("❌ No HCS Topic ID configured.")
            return False
            
        try:
            client = self.app.account_manager.client
            tx = TopicMessageSubmitTransaction() \
                .set_topic_id(TopicId.from_string(target_topic)) \
                .set_message(message)
            
            tx.freeze_with(client)
            response = tx.execute(client)
            
            if hasattr(response, "get_receipt"):
                receipt = response.get_receipt(client)
            else:
                receipt = response
            
            return receipt.status == 22 # SUCCESS
        except Exception as e:
            logger.error(f"❌ Failed to submit HCS message: {e}")
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
        """Broadcast an investment signal as a JSON-encoded HCS message with rich metadata."""
        from datetime import datetime
        now = datetime.utcnow()
        
        # Metadata mapping for premium presentation
        emojis = {
            "REBALANCE_BUY_BTC": "🚀 BUY SIGNAL",
            "REBALANCE_SELL_BTC": "💎 SELL SIGNAL",
            "SIGNAL_HEARTBEAT": "📊 MARKET PULSE",
            "SIGNAL_ALERT": "⚠️ ALERT"
        }
        
        display_type = emojis.get(signal_type, signal_type.replace("_", " "))
        
        payload = {
            "version": "1.1",
            "type": "SIGNAL",
            "signal": signal_type,
            "display_title": display_type,
            "timestamp_utc": now.strftime("%Y-%m-%d %H:%M:%S"),
            "timestamp_unix": now.timestamp(),
            "sender": self.app.account_id,
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
