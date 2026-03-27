import type { BridgeStatusResult } from "../types";

export const usdt0CheckBridgeStatus = {
  name: "usdt0_check_bridge_status",
  description: "Check the delivery status of a USDT0 bridge transaction via the LayerZero Scan API.",
  parameters: {
    type: "object",
    properties: {
      txHash: { type: "string", description: "Source transaction hash from the bridge call" },
      lzMessageGuid: { type: "string", description: "LayerZero message GUID (alternative to txHash)" },
    },
    required: [],
  },
  handler: async (params: { txHash?: string; lzMessageGuid?: string }): Promise<BridgeStatusResult> => {
    const lookupId = params.txHash || params.lzMessageGuid;
    if (!lookupId) {
      return { status: "unknown", error: "Provide either txHash or lzMessageGuid" };
    }
    try {
      const url = `https://scan.layerzero-api.com/v1/messages/tx/${lookupId}`;
      const resp = await fetch(url);

      if (!resp.ok) {
        return { status: "unknown", error: `LZ Scan returned ${resp.status}` };
      }

      const data = await resp.json();
      const messages = data.messages || data.data || [];

      if (!messages.length) {
        return { status: "pending" };
      }

      const msg = Array.isArray(messages) ? messages[0] : messages;
      return {
        status: msg.status || "unknown",
        srcTxHash: msg.srcTxHash || lookupId,
        dstTxHash: msg.dstTxHash || "",
      };
    } catch (e: any) {
      return { status: "unknown", error: e.message };
    }
  },
};
