"""
Telegram Interceptor Plugin
===========================
FastAPI webhook server for Telegram bot updates.

Phase 1: Fast-lane slash commands → PacmanController (no LLM round-trip)
Phase 2+: Regular text → AI lane (OpenClaw / LLM)

Entry point: interceptor.py (uvicorn app)
"""
