# Integration Guide: AI Infrastructure & Agentic Frameworks

Pacman is designed to be "Agent-First" software. This guide outlines how to integrate Pacman with existing AI agent infrastructure, such as OpenClaw, AutoGPT, or custom MCP (Model Context Protocol) servers.

## 1. Integration Patterns

### A. The "Black Box" CLI Pattern (Lowest Friction)
Most agentic frameworks (like OpenClaw) can interact with Pacman simply by executing shell commands. Security wise, this is loose! 
 Security wise, this is loose! 
- **Workflow**: Agent generates an NL string -> Calls `python3 pacman_cli.py "[string]"` -> Parses standard output.
- **Example**:
  ```bash
  python3 pacman_cli.py "swap 10 HBAR for USDC"
  ```
- **Pro**: No code changes needed. Full access to hardened pipeline.

### B. The Python SDK Pattern (Highest Control)
If you are building a custom Python agent, import the core components directly.
```python
from pacman_translator import translate
from pacman_variant_router import PacmanVariantRouter
from pacman_executor import PacmanExecutor

# 1. Translate NL to Intent
req = translate("swap 5 HBAR for USDC")

# 2. Get Recommended Route
router = PacmanVariantRouter()
router.load_pools()
route = router.recommend_route(req['from_token'], req['to_token'])

# 3. Execute with Hardened Safety
executor = PacmanExecutor(private_key=os.getenv("PACMAN_PRIVATE_KEY"))
result = executor.execute_swap(route, amount_usd=req['amount'])
```

### C. The MCP Pattern (Modern Standard)
You can wrap Pacman into an **MCP Server** to expose it as a toolset for LLMs (Claude, GPT-4).
- **Tool 1**: `get_token_list` -> Calls `router.get_supported_tokens()`.
- **Tool 2**: `preview_swap` -> Calls `router.recommend_route()` and returns `route.explain()`.
- **Tool 3**: `execute_swap` -> Calls `executor.execute_swap()`.

## 2. Framework-Specific Guidance

### OpenClaw / AutoGPT
- Set `PACMAN_AUTO_CONFIRM=true` to allow the agent to skip interactive prompts.
- Ensure `PACMAN_SIMULATE=true` is set during the "Planning" phase of the agent's loop to verify routes without risk.

### LangChain / AutoGen
- Use the `PacmanTranslator` as a custom parser tool.
- Pass the professional transaction receipt back into the agent's context to update its "Internal Ledger".

## 3. High-Security Integration
For public-facing AI agents:
1. **Simulation First**: Force all swaps through simulation mode until a threshold of confidence is met.
2. **Approval Ceiling**: Use Pacman's `HTS Approval Hardening` to ensure the agent cannot approve more tokens than the swap requires.
3. **Audit Logging**: Use the `execution_records/` (locally recorded) to provide a transparent audit trail for all agent actions.
