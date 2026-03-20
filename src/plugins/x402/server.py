"""
X402 Payment-Gated Signal Access Server

This module implements HTTP 402 (Payment Required) for agent-to-agent commerce.
Clients can access trading signals and HCS history, but must submit proof of payment first.

Flow:
1. Client requests /signal without payment → HTTP 402 with payment instructions
2. Client sends micro-payment (0.14 HBAR) to the account specified in response
3. Client re-requests /signal with X-Payment-Tx header containing transaction hash
4. Server verifies payment via Hedera Mirror Node and returns signal data

This is a proof-of-concept scaffold showing the X402 pattern. Not production-ready.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

try:
    from fastapi import FastAPI, Header, HTTPException
    from fastapi.responses import JSONResponse
    import uvicorn
except ImportError:
    raise ImportError(
        "FastAPI required for X402 server. Install: pip install fastapi uvicorn"
    )


# ─── Configuration ───────────────────────────────────────────
HEDERA_ACCOUNT_ID = os.getenv("HEDERA_ACCOUNT_ID", "0.0.10289160")
MIRRORNODE_URL = os.getenv(
    "HEDERA_MIRRORNODE_URL", "https://mainnet-public.mirrornode.hedera.com"
)
X402_RATE_HBAR = 0.14  # 0.14 HBAR ≈ $0.03 at $0.19/HBAR, ~$10/year
X402_MEMO = "pacman-signal-access"

DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
ROBOT_STATE_PATH = DATA_DIR / "robot_state.json"

# ─── FastAPI App ────────────────────────────────────────────
app = FastAPI(
    title="Pacman X402 Signal Server",
    description="Payment-gated access to trading signals via HTTP 402",
    version="0.1.0",
)


def load_robot_state() -> Dict:
    """Load the latest robot state from robot_state.json."""
    if ROBOT_STATE_PATH.exists():
        with open(ROBOT_STATE_PATH, "r") as f:
            return json.load(f)
    return {
        "error": "robot_state.json not found",
        "last_signal": None,
        "trades_executed": 0,
    }


def payment_required_response() -> JSONResponse:
    """
    Return HTTP 402 with payment instructions.

    Clients should:
    1. Note the hedera_account and amount_hbar
    2. Send a payment transaction from their account
    3. Re-request with X-Payment-Tx header containing the tx hash
    """
    return JSONResponse(
        status_code=402,
        content={
            "status": "payment_required",
            "payment_destination": {
                "hedera_account": HEDERA_ACCOUNT_ID,
                "amount_hbar": X402_RATE_HBAR,
                "memo": X402_MEMO,
            },
            "details": f"Send {X402_RATE_HBAR} HBAR to {HEDERA_ACCOUNT_ID} with memo '{X402_MEMO}'. "
            f"Then retry with X-Payment-Tx header containing the transaction hash.",
            "mirror_node": MIRRORNODE_URL,
        },
    )


def verify_payment_on_mirrornode(tx_hash: str) -> bool:
    """
    Verify payment transaction on Hedera Mirror Node.

    For now, this is a stub that logs the attempt.
    In production, you would:
    - Query Mirror Node: GET /api/v1/transactions/{tx_hash}
    - Verify: amount >= X402_RATE_HBAR, recipient == HEDERA_ACCOUNT_ID, memo matches
    - Check: transaction success (result == "SUCCESS")

    Args:
        tx_hash: Hedera transaction ID (format: shard.realm.num-nonce-timestamp)

    Returns:
        True if payment is valid, False otherwise
    """
    # Stub implementation. In production, call Mirror Node API.
    print(f"[X402] Would verify payment tx: {tx_hash}")
    print(f"[X402] Against account: {HEDERA_ACCOUNT_ID}")
    print(f"[X402] Expected amount: {X402_RATE_HBAR} HBAR")

    # For demo/testing, accept any non-empty tx hash
    # In real use, validate against Mirror Node
    return bool(tx_hash and len(tx_hash) > 5)


@app.get("/signal")
async def get_signal(x_payment_tx: Optional[str] = Header(None)) -> Dict:
    """
    Get the latest robot trading signal.

    Returns HTTP 402 (Payment Required) unless a valid payment proof is provided.

    Query Parameters:
        None

    Headers:
        X-Payment-Tx: Transaction hash from payment transaction (optional)

    Returns:
        - 402: Payment required. Includes account and rate in body.
        - 200: Signal data if payment is verified.
        - 400: Invalid payment proof.
    """
    # Check for payment proof
    if not x_payment_tx:
        return payment_required_response()

    # Verify payment on Mirror Node
    if not verify_payment_on_mirrornode(x_payment_tx):
        raise HTTPException(
            status_code=400,
            detail="Invalid or unverified payment transaction",
        )

    # Payment verified! Return signal
    robot_state = load_robot_state()
    signal = robot_state.get("last_signal", {})

    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "signal": signal,
        "metadata": {
            "trades_executed": robot_state.get("trades_executed", 0),
            "last_rebalance": robot_state.get("last_rebalance"),
            "portfolio": robot_state.get("last_portfolio"),
        },
    }


@app.get("/signal/history")
async def get_signal_history(
    limit: int = 10, x_payment_tx: Optional[str] = Header(None)
) -> Dict:
    """
    Get recent signal history from HCS topic.

    In a real implementation, this would query the Hedera Consensus Service
    topic to return recent messages. For now, it returns a stub with metadata.

    Query Parameters:
        limit: Number of recent signals to return (default: 10)

    Headers:
        X-Payment-Tx: Transaction hash from payment transaction (optional)

    Returns:
        - 402: Payment required.
        - 200: Signal history if payment is verified.
    """
    # Check for payment proof
    if not x_payment_tx:
        return payment_required_response()

    # Verify payment
    if not verify_payment_on_mirrornode(x_payment_tx):
        raise HTTPException(
            status_code=400,
            detail="Invalid or unverified payment transaction",
        )

    # Payment verified! Return history stub
    robot_state = load_robot_state()
    activity_log = robot_state.get("activity_log", [])[:limit]

    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "count": len(activity_log),
        "history": activity_log,
        "note": "In production, this would be populated from HCS topic messages",
    }


@app.get("/health")
async def health_check() -> Dict:
    """Health check endpoint. No payment required."""
    return {
        "status": "healthy",
        "service": "pacman-x402-signal-server",
        "version": "0.1.0",
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/")
async def root() -> Dict:
    """Root endpoint with service info."""
    return {
        "service": "Pacman X402 Signal Server",
        "description": "Payment-gated access to trading signals via HTTP 402",
        "endpoints": {
            "GET /signal": "Get latest robot signal (requires X-Payment-Tx or HTTP 402)",
            "GET /signal/history": "Get recent signal history (requires payment)",
            "GET /health": "Health check (no payment required)",
        },
        "payment_rate": {
            "amount_hbar": X402_RATE_HBAR,
            "destination": HEDERA_ACCOUNT_ID,
            "memo": X402_MEMO,
        },
        "docs": "http://localhost:8000/docs",
    }


def run_server(host: str = "127.0.0.1", port: int = 8000, reload: bool = False):
    """
    Start the X402 server.

    Args:
        host: Server hostname (default: 127.0.0.1)
        port: Server port (default: 8000)
        reload: Auto-reload on code changes (default: False)
    """
    print(f"Starting X402 Signal Server on {host}:{port}")
    print(f"Payment destination: {HEDERA_ACCOUNT_ID}")
    print(f"Payment rate: {X402_RATE_HBAR} HBAR")
    print(f"API docs: http://{host}:{port}/docs")
    uvicorn.run(app, host=host, port=port, reload=reload)


if __name__ == "__main__":
    run_server()
