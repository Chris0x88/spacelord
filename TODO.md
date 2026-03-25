# Pacman Project Plan

**Last Updated:** 2026-03-26 05:01 AEST

## 🎯 High Priority Initiatives

### 1. LayerZero USDT0 → Arbitrum Bridge (Hedera → Hyperliquid)
**Status:** Planned  
**Owner:** TBD  

**Objective:** Enable seamless cross-chain transfers of USDT0 from Hedera to Arbitrum, then to Hyperliquid for trading.

**Key Tasks:**
- [ ] Research LayerZero USDT0 contract architecture and bridge mechanics
- [ ] Integrate LayerZero messaging/endpoint into Pacman CLI
- [ ] Implement Hedera → Arbitrum bridge transaction flow
- [ ] Implement Arbitrum → Hyperliquid transfer path
- [ ] Add gas estimation and fee calculation for bridge operations
- [ ] Test on testnet (Hedera Testnet → Arbitrum Sepolia)
- [ ] Safety checks: bridge status monitoring, refund handling, failure recovery
- [ ] CLI commands: `pacman bridge layerzero usdt0 from:hedera to:hyperliquid`

**Dependencies:**
- LayerZero contract deployment on Hedera and Arbitrum
- USDT0 token contracts on both chains
- Hyperliquid deposit address handling

**Notes:**
- This is a high-value feature for arbitrage and liquidity management
- Consider speed vs cost tradeoffs (LayerZero is ~1-2 mins)
- Need to track bridge transaction status and receipts

---

### 2. OpenWallet Key Management Integration
**Status:** Planned  
**Owner:** TBD  

**Objective:** Integrate OpenWallet for secure, hardware-backed private key storage and transaction signing on Hedera.

**Key Tasks:**
- [ ] Evaluate OpenWallet API/SDK capabilities and authentication models
- [ ] Design key derivation and session management flow
- [ ] Implement OpenWallet connector module in `lib/` or `cli/`
- [ ] Add wallet connection command: `pacman wallet connect openwallet`
- [ ] Implement transaction signing delegation (wallet signs, CLI broadcasts)
- [ ] Support multiple wallet profiles (wallet A for trading, wallet B for staking)
- [ ] Add wallet status commands: balance, chain ID, account info
- [ ] Test with OpenWallet mobile app (Bluetooth/USB) and browser extension
- [ ] Documentation: setup guide, security considerations, troubleshooting

**Dependencies:**
- OpenWallet SDK/API availability for Python/macOS
- Hedera wallet address derivation compatibility (ED25519 keys)
- User device compatibility testing

**Security Requirements:**
- Private keys NEVER leave the OpenWallet device
- All signing happens on-device; CLI only gets raw signed transactions
- Session timeout and revocation mechanisms
- Clear user consent prompts for every transaction
- Audit trail of wallet-connected operations

**Notes:**
- This improves security posture vs local keystores
- Enables mobile-first workflows (phone signs, Mac broadcasts)
- Consider fallback to local keystore if OpenWallet unavailable

---

## 📋 Other Active Projects (Context)

See also:
- `MEMORY.md` for ongoing project context
- `docs/roadmap.md` (if exists) for longer-term vision
- `backups/` for historical project artifacts

---

## ✨ Contributing

Found an issue or want to help? Check `CONTRIBUTING.md` and open a PR!
