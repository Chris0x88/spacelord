# Security Guide & Risk Disclosure

## ⚠️ MANDATORY WARNING
**Pacman CLI is an experimental tool in active testing. It is NOT intended for production use with capital.** 
Not all functions may work as desired; use with extreme caution.

By using this software, you acknowledge that you are handling your own cryptographic private keys. **If your machine is compromised, your funds are at risk.**

---

## 🔒 Key Management Best Practices

### 1. Use a "Hot Account"
Do **NOT** use your main savings account or any account with high-value balances. 
- Create a dedicated Hedera account specifically for experimentation.
- Only transfer the amount of HBAR/Tokens you intend to trade in the immediate session.

### 2. Secure Environment Variables
Pacman reads your private key from an `.env` file. 
- Ensure your `.env` file is **never** committed to version control. (The provided `.gitignore` already handles this).
- Do not store your private key in plain text in any other shared or backed-up file.

### 3. Simulation First
Always run Pacman in simulation mode (`PACMAN_SIMULATE=true`) first to verify routes and expected outcomes before committing real capital.

---

## 🔍 Deep Dive: Plain Text Memory Risk

When you run Pacman, your private key is loaded from the `.env` file into the Python process's memory (the heap). 

### The Risk
- **Memory Dumps**: If your machine is infected with malware, an attacker with sufficiently high privileges can perform a "memory dump" of the Python process and extract your private key in plain text.
- **Process Inspection**: Tools like `gdb` or memory scanners can see the key while the script is active.
- **Insecure Cleanup**: Python's garbage collector does not immediately wipe the string from memory after the script finishies.

### Mitigation Ideas
- **Dedicated VM/Docker**: Run Pacman inside a hardened, minimal Docker container or a dedicated Virtual Machine. This limits the "blast radius" to just that isolated environment.
- **Immediate Initialization**: Only load the key at the exact moment of signing, and attempt to clear the variable immediately after (though Python's memory management makes "zeroing out" difficult).

---

## 🗺️ Security Hardening Roadmap

We are exploring several industry-standard ways to upgrade Pacman's security:

### 1. MPC Wallets (Privy / Turnkey)
Instead of a single private key, we could integrate Multi-Party Computation (MPC). 
- **How it works**: Your key is split into "shares". One share stays on your machine, another with a provider (like Privy). No single party ever has the full key. This is the gold standard for agentic apps.

### 2. Cloud KMS (AWS / Google Cloud)
For cloud deployments, we can use a **Hardware Security Module (HSM)**.
- **How it works**: Your key lives in an Amazon/Google data center and *never* leaves. Pacman sends the transaction to the KMS, which signs it and sends back the signature. Your script never sees the actual key.

### 3. Encrypted Keystores
Moving away from `.env` to encrypted JSON files (similar to Ethereum's `UTC--...` files).
- **How it works**: You would need to type a password every time you launch Pacman to decrypt the key for that session only.

### 4. Hardware Wallet Support
Direct integration with Ledger or Trezor.
- **How it works**: You would manually confirm every swap on your physical device. Pacman would purely be the routing and transaction-building engine. This is the most secure option but not suitable for ai agents and so we are unlikely to pursue this direction. 

## ⚖️ Liability
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND. The authors and contributors are not responsible for any financial loss, bugs, or security breaches resulting from the use of this tool.

**Stay secure.**
