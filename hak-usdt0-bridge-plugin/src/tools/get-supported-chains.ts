import { SUPPORTED_CHAINS, HEDERA_CONFIG, USDT0_DECIMALS } from "../contracts/addresses";

export const usdt0GetSupportedChains = {
  name: "usdt0_get_supported_chains",
  description: "List all chains supported for USDT0 bridging via LayerZero, with endpoint IDs and contract addresses.",
  parameters: {},
  handler: async () => {
    const chains = Object.entries(SUPPORTED_CHAINS).map(([key, config]) => ({
      key,
      ...config,
    }));
    return {
      source: { name: "Hedera", ...HEDERA_CONFIG },
      destinations: chains,
      decimals: USDT0_DECIMALS,
    };
  },
};
