# CRITICAL: Hedera Gas Safety & Address Format Lessons

## ⚠️ THE GAS CLIFF (CRITICAL FAILURE)
On Hedera, if a contract call reverts (especially via the HTS precompile/redirect addresses), **100% of the gas limit is consumed and never returned.** 

- **Rule 1**: NEVER set an arbitrarily high gas limit (e.g., 5,000,000) on a transaction that hasn't been verified via a simulation.
- **Rule 2**: ALWAYS perform a local simulation (`eth_call`) before sending a live transaction (`send_raw_transaction`). If the simulation reverts, **DO NOT PROCEED**.
- **Rule 3**: If a transaction reverts during execution, do not just "increase gas". Investigate the logic (address format, association, balance) first.

## 🛑 ADDRESS FORMAT RULES
Hedera's EVM behaves inconsistently with "Long-Zero" vs "Alias" addresses.

- **Rule 4**: Use the **Alias Address** (e.g., `0x76D2...`) for EVERYTHING:
    - Signing (`from`)
    - Contract arguments (`account`, `recipient`, `owner`, `spender`)
    - Allowance/Balance queries
- **Rule 5**: Avoid using/deriving the **Long-Zero Address** (e.g., `0x00...`) for any logic within the `PacmanExecutor` (`src/executor.py`). It causes silent reverts in the HTS precompile that burn 100% of gas.

## ✅ SAFE EXECUTION PATTERN
1. **Check Allowance**: Use `eth_call` to check if `allowance >= amount`.
2. **Conditional Approval**: Only call `approve()` if allowance is insufficient.
3. **Simulate Operation**: Use `contract.functions.method(...).call()` to verify the transaction will succeed.
4. **Execute**: Only after 1-3 pass, broadcast the transaction with a tight, sensible gas limit.
