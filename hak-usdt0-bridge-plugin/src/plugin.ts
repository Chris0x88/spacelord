import { usdt0GetSupportedChains } from "./tools/get-supported-chains";
import { usdt0QuoteBridge } from "./tools/quote-bridge";
import { usdt0Bridge } from "./tools/bridge";
import { usdt0CheckBridgeStatus } from "./tools/check-bridge-status";

export class USDT0BridgePlugin {
  name = "usdt0-bridge";
  description = "Bridge USDT0 between Hedera and other chains via LayerZero OFT";

  getTools() {
    return [
      usdt0GetSupportedChains,
      usdt0QuoteBridge,
      usdt0Bridge,
      usdt0CheckBridgeStatus,
    ];
  }
}
