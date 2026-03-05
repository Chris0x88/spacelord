# Pacman: macOS File Locking Crisis — Action Required

**Date:** 2026-03-02  
**Status:** Blocked on Mac M4 (Apple Silicon)  
**Severity:** High — prevents all CLI usage

## Problem

Running `./pacman balance` on macOS results in:
- Complete hang (no output)
- `Resource deadlock avoided` errors on all file operations
- Python import failures (`OSError: [Errno 11]`)

Root cause: iCloud Drive/Spotlight locking + Python bytecode cache deadlocks in venv.

## Immediate Mitigation (Manual)

1. Move project out of iCloud Drive to local-only path
2. Delete `__pycache__/` and all `.pyc` files
3. Kill all Python processes: `killall -9 python3`
4. Use fresh clone instead of archived copies

## Proposed Fix: uv + HTTP API

Switch from venv/pip to **uv** (Astral's Rust-based Python manager):
- No file locks, 100x faster, auto Python version management
- Single command: `uv run pacman_cli.py`
- Or better: Convert to HTTP API (FastAPI) for agent access

See full analysis: `docs/MACOS_LOCKING_AND_UV_SOLUTION.md`

## Action Items

- [ ] Create `pyproject.toml` for uv
- [ ] Test uv workflow on Mac M4
- [ ] Prototype FastAPI server version
- [ ] Build Docker container
- [ ] Update docs with uv instructions

**Blocked until uv migration is tested and deployed.**
