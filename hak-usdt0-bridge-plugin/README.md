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
