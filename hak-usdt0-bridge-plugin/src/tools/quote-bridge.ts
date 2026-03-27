import { ethers } from "ethers";
import { SUPPORTED_CHAINS, HEDERA_CONFIG, USDT0_DECIMALS } from "../contracts/addresses";
import { OFT_ABI } from "../contracts/oft-abi";
import type { QuoteResult } from "../types";

export const usdt0QuoteBridge = {
  name: "usdt0_quote_bridge",
  description: "Get a fee estimate for bridging USDT0 from Hedera to a destination chain. Does not execute.",
  parameters: {
    type: "object",
    properties: {
      amount: { type: "number", description: "Amount of USDT0 to bridge" },
      destChain: { type: "string", description: "Destination chain key (e.g. 'arbitrum')" },
    },
    required: ["amount", "destChain"],
  },
  handler: async (
    params: { amount: number; destChain: string },
    provider: ethers.Provider,
    signer: ethers.Signer,
  ): Promise<QuoteResult> => {
    const chain = SUPPORTED_CHAINS[params.destChain];
    if (!chain) {
      return { success: false, error: `Unsupported chain: ${params.destChain}` };
    }

    const amountRaw = BigInt(Math.floor(params.amount * 10 ** USDT0_DECIMALS));
    const signerAddress = await signer.getAddress();
    const toBytes32 = ethers.zeroPadValue(signerAddress, 32);

    const oft = new ethers.Contract(HEDERA_CONFIG.oftAddress, OFT_ABI, provider);
    const sendParam = [chain.eid, toBytes32, amountRaw, 0n, "0x", "0x", "0x"];

    try {
      const [, , oftReceipt] = await oft.quoteOFT(sendParam);
      const minReceived = oftReceipt.amountReceivedLD;

      const sendParamWithMin = [chain.eid, toBytes32, amountRaw, minReceived, "0x", "0x", "0x"];
      const msgFee = await oft.quoteSend(sendParamWithMin, false);

      return {
        success: true,
        estimatedReceived: ethers.formatUnits(minReceived, USDT0_DECIMALS),
        nativeFee: ethers.formatEther(msgFee.nativeFee),
        minReceived: ethers.formatUnits(minReceived, USDT0_DECIMALS),
      };
    } catch (e: any) {
      return { success: false, error: `Quote failed: ${e.message}` };
    }
  },
};
