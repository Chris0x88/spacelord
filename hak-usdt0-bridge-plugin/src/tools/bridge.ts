import { ethers } from "ethers";
import { SUPPORTED_CHAINS, HEDERA_CONFIG, USDT0_DECIMALS } from "../contracts/addresses";
import { OFT_ABI } from "../contracts/oft-abi";
import { ERC20_ABI } from "../contracts/erc20-abi";
import type { BridgeResult } from "../types";

export const usdt0Bridge = {
  name: "usdt0_bridge",
  description: "Bridge USDT0 from Hedera to a destination chain via LayerZero OFT. Handles approval, quoting, and sending.",
  parameters: {
    type: "object",
    properties: {
      amount: { type: "number", description: "Amount of USDT0 to bridge" },
      destChain: { type: "string", description: "Destination chain key (e.g. 'arbitrum')" },
      recipientAddress: { type: "string", description: "Destination EVM address (0x...)" },
    },
    required: ["amount", "destChain", "recipientAddress"],
  },
  handler: async (
    params: { amount: number; destChain: string; recipientAddress: string },
    provider: ethers.Provider,
    signer: ethers.Signer,
  ): Promise<BridgeResult> => {
    const chain = SUPPORTED_CHAINS[params.destChain];
    if (!chain) {
      return { success: false, error: `Unsupported chain: ${params.destChain}` };
    }

    if (!/^0x[0-9a-fA-F]{40}$/.test(params.recipientAddress)) {
      return { success: false, error: `Invalid EVM address: ${params.recipientAddress}` };
    }

    const amountRaw = BigInt(Math.floor(params.amount * 10 ** USDT0_DECIMALS));
    const signerAddress = await signer.getAddress();
    const toBytes32 = ethers.zeroPadValue(params.recipientAddress, 32);

    const oft = new ethers.Contract(HEDERA_CONFIG.oftAddress, OFT_ABI, signer);
    const token = new ethers.Contract(HEDERA_CONFIG.tokenAddress, ERC20_ABI, signer);

    try {
      const balance = await token.balanceOf(signerAddress);
      if (balance < amountRaw) {
        return {
          success: false,
          error: `Insufficient USDT0. Have: ${ethers.formatUnits(balance, USDT0_DECIMALS)}, Need: ${params.amount}`,
        };
      }

      const allowance = await token.allowance(signerAddress, HEDERA_CONFIG.oftAddress);
      if (allowance < amountRaw) {
        const approveTx = await token.approve(HEDERA_CONFIG.oftAddress, amountRaw);
        await approveTx.wait();
      }

      const sendParam = [chain.eid, toBytes32, amountRaw, 0n, "0x", "0x", "0x"];
      const [, , oftReceipt] = await oft.quoteOFT(sendParam);
      const minReceived = oftReceipt.amountReceivedLD;

      const sendParamFinal = [chain.eid, toBytes32, amountRaw, minReceived, "0x", "0x", "0x"];
      const msgFee = await oft.quoteSend(sendParamFinal, false);

      const tx = await oft.send(sendParamFinal, [msgFee.nativeFee, 0n], signerAddress, {
        value: msgFee.nativeFee,
      });
      const receipt = await tx.wait();

      return {
        success: true,
        txHash: receipt.hash,
        lzMessageGuid: receipt.hash,
        amountSent: params.amount.toString(),
        estimatedArrival: "30s-3min",
      };
    } catch (e: any) {
      return { success: false, error: `Bridge failed: ${e.message}` };
    }
  },
};
