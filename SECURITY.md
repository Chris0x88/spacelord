# Security Guide & Risk Disclosure

## ⚠️ MANDATORY WARNING
**Pacman CLI is an experimental tool. It is NOT intended for production use with significant capital.**

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
- Always run Pacman in simulation mode (`PACMAN_SIMULATE=true`) first to verify routes and expected outcomes before committing real capital.

---

## 🏗️ Technical Implementation Risks
- **Plain Text Processing**: While Pacman does not store or transmit your key to any 3rd party (it only interacts with the Hedera JSON-RPC and Consensus nodes), the key *does* exist in your machine's memory while the script is running.
- **Local Logs**: Pacman generates local JSON execution records in `execution_records/`. These do **not** contain your private key, but they do show your trade history. Keep this folder private.

## ⚖️ Liability
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND. The authors and contributors are not responsible for any financial loss, bugs, or security breaches resulting from the use of this tool.

**Trade safe. Trade small. Stay secure.**
