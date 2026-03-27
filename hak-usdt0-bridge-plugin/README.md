# hak-usdt0-bridge-plugin

USDT0 cross-chain bridge plugin for the Hedera Agent Kit, powered by LayerZero OFT.

## Tools

- **usdt0_get_supported_chains** - List supported bridge destinations
- **usdt0_quote_bridge** - Get fee estimate without executing
- **usdt0_bridge** - Execute a bridge transaction (approve + quote + send)
- **usdt0_check_bridge_status** - Check delivery status via LayerZero Scan

## Install

```bash
npm install hak-usdt0-bridge-plugin
```

## Usage

```typescript
import { USDT0BridgePlugin } from "hak-usdt0-bridge-plugin";

const plugin = new USDT0BridgePlugin();
const tools = plugin.getTools();
```

## Supported Chains

| Chain | EID | Chain ID |
|-------|-----|----------|
| Hedera (source) | 30285 | 295 |
| Arbitrum One | 30110 | 42161 |

## Contract Addresses

| Chain | USDT0 Token | OFT Contract |
|-------|------------|--------------|
| Hedera | `0x...009Ce723` (HTS: 0.0.642851) | `0xe3119e23fC2371d1E6b01775ba312035425A53d6` |
| Arbitrum | `0xFd086bC7...FCbb9` | `0x14E4A1B1...298D92` |

## How It Works

1. **Quote** — Calls `quoteOFT()` + `quoteSend()` on the Hedera OFT contract
2. **Approve** — Approves OFT contract to spend USDT0 (exact amount per tx)
3. **Send** — Calls `send()` with LayerZero messaging fee as native value
4. **Track** — Check delivery via LayerZero Scan API (30s-3min typical)

## License

MIT
