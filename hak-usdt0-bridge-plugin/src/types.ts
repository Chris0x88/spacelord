export interface ChainConfig {
  name: string;
  eid: number;
  chainId: number;
  tokenAddress: string;
  oftAddress: string;
}

export interface SendParam {
  dstEid: number;
  to: string;
  amountLD: bigint;
  minAmountLD: bigint;
  extraOptions: string;
  composeMsg: string;
  oftCmd: string;
}

export interface MessagingFee {
  nativeFee: bigint;
  lzTokenFee: bigint;
}

export interface QuoteResult {
  success: boolean;
  estimatedReceived?: string;
  nativeFee?: string;
  minReceived?: string;
  error?: string;
}

export interface BridgeResult {
  success: boolean;
  txHash?: string;
  lzMessageGuid?: string;
  amountSent?: string;
  estimatedArrival?: string;
  error?: string;
}

export interface BridgeStatusResult {
  status: "pending" | "inflight" | "delivered" | "failed" | "unknown";
  srcTxHash?: string;
  dstTxHash?: string;
  error?: string;
}
