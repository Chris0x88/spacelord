#!/usr/bin/env python3
"""
Example X402 client demonstrating the payment-gated signal access flow.

This shows how an agent would interact with the X402 server:
1. Request signal without payment → HTTP 402
2. Initiate payment transaction
3. Re-request with payment proof → HTTP 200 + data

For demo purposes, we simulate the payment step and use a mock tx hash.
"""

import json
from typing import Dict, Optional


class X402Client:
    """Minimal client for X402 payment-gated endpoints."""

    def __init__(self, server_url: str = "http://127.0.0.1:8000"):
        self.server_url = server_url
        self.payment_destination: Optional[Dict] = None

    def request_signal(self, payment_tx: Optional[str] = None) -> Dict:
        """
        Request the latest trading signal.

        Flow:
        1. First call (no payment_tx) → Server returns HTTP 402 with payment instructions
        2. Client sends payment transaction
        3. Second call (with payment_tx) → Server returns signal data

        Args:
            payment_tx: Transaction hash from payment (optional on first call)

        Returns:
            Response dict with either payment instructions or signal data
        """
        print(f"\n{'='*60}")
        print("X402 SIGNAL REQUEST")
        print(f"{'='*60}")

        if not payment_tx:
            print("Step 1: Request without payment")
            print(f"GET {self.server_url}/signal")
            print(
                "\n→ Expected: HTTP 402 (Payment Required) with payment instructions"
            )

            # Simulate what server would return
            response = {
                "status_code": 402,
                "status": "payment_required",
                "payment_destination": {
                    "hedera_account": "0.0.10289160",
                    "amount_hbar": 0.14,
                    "memo": "pacman-signal-access",
                },
                "details": "Send 0.14 HBAR to 0.0.10289160 with memo 'pacman-signal-access'. Then retry with X-Payment-Tx header containing the transaction hash.",
            }

            self.payment_destination = response["payment_destination"]
            print(f"\nResponse:\n{json.dumps(response, indent=2)}")
            return response

        else:
            print(f"Step 2: Request with payment proof")
            print(f"GET {self.server_url}/signal")
            print(f'Header: X-Payment-Tx: "{payment_tx}"')
            print("\n→ Expected: HTTP 200 (OK) with signal data")

            # Simulate what server would return with valid payment
            response = {
                "status_code": 200,
                "status": "ok",
                "timestamp": "2026-03-21T12:34:56.789Z",
                "signal": {
                    "date": "2026-03-20",
                    "price": 69924.55947606776,
                    "allocation_pct": 60.1,
                    "floor": 58115.14,
                    "ceiling": 134819.11,
                    "stance": "accumulate",
                    "phase": "late_cycle_peak_zone",
                    "valuation": "deep_value",
                    "tagline": "Cycle 5 | 48% complete | Late Cycle Peak Zone | Price at 15% of range (deep value) | Favorable accumulation: 60% BTC recommended",
                },
                "metadata": {
                    "trades_executed": 39,
                    "last_rebalance": "2026-03-19T20:50:18.175781",
                    "portfolio": {
                        "wbtc_balance": 0.00023978,
                        "usdc_balance": 11.501914,
                        "hbar_balance": 39.20598938,
                        "total_value_usd": 28.26842487117153,
                    },
                },
            }

            print(f"\nResponse:\n{json.dumps(response, indent=2)}")
            return response

    def simulate_payment(self) -> str:
        """
        Simulate sending a payment transaction to the server.

        In reality, this would:
        1. Create a TransferTransaction from agent's account to HEDERA_ACCOUNT_ID
        2. Set amount to 0.14 HBAR and memo to "pacman-signal-access"
        3. Sign and submit to the Hedera network
        4. Return the transaction ID (hash)

        For demo, we return a mock tx ID.

        Returns:
            Hedera transaction ID (format: shard.realm.num-nonce-timestamp)
        """
        print(f"\n{'='*60}")
        print("PAYMENT SIMULATION")
        print(f"{'='*60}")

        if not self.payment_destination:
            print("ERROR: No payment destination. Call request_signal() first.")
            return ""

        print(f"Destination: {self.payment_destination['hedera_account']}")
        print(f"Amount:      {self.payment_destination['amount_hbar']} HBAR")
        print(f"Memo:        {self.payment_destination['memo']}")
        print("\nIn a real agent:")
        print(
            "  1. Create TransferTransaction from agent account → destination account"
        )
        print("  2. Set amount and memo")
        print("  3. Sign with agent's private key")
        print("  4. Submit to Hedera network via client")
        print("  5. Wait for receipt")
        print("  6. Extract transaction ID from receipt")

        # Return mock tx ID
        mock_tx_id = "0.0.456-789-1234567890"
        print(f"\n✓ Payment sent! Transaction ID: {mock_tx_id}")
        return mock_tx_id


def main():
    """Demonstrate the X402 flow."""
    print("\n" + "=" * 60)
    print("X402 PAYMENT-GATED SIGNAL ACCESS DEMO")
    print("=" * 60)

    client = X402Client()

    # Step 1: Request signal without payment
    resp1 = client.request_signal()
    assert resp1["status_code"] == 402, "Expected 402 Payment Required"

    # Step 2: Simulate payment
    tx_id = client.simulate_payment()

    # Step 3: Request signal with payment proof
    resp2 = client.request_signal(payment_tx=tx_id)
    assert resp2["status_code"] == 200, "Expected 200 OK"
    assert "signal" in resp2, "Expected signal data in response"

    print(f"\n{'='*60}")
    print("✓ X402 FLOW COMPLETE")
    print(f"{'='*60}")
    print("\nAgent received trading signal after micropayment:")
    signal = resp2["signal"]
    print(f"  - Allocation: {signal['allocation_pct']}% BTC")
    print(f"  - Stance: {signal['stance']}")
    print(f"  - Tagline: {signal['tagline']}")


if __name__ == "__main__":
    main()
