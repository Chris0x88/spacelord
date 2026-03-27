export const OFT_ABI = [
  {
    inputs: [{ components: [
      { name: "dstEid", type: "uint32" },
      { name: "to", type: "bytes32" },
      { name: "amountLD", type: "uint256" },
      { name: "minAmountLD", type: "uint256" },
      { name: "extraOptions", type: "bytes" },
      { name: "composeMsg", type: "bytes" },
      { name: "oftCmd", type: "bytes" },
    ], name: "_sendParam", type: "tuple" }],
    name: "quoteOFT",
    outputs: [
      { components: [
        { name: "minAmountLD", type: "uint256" },
        { name: "maxAmountLD", type: "uint256" },
      ], name: "oftLimit", type: "tuple" },
      { components: [
        { name: "feeAmountLD", type: "uint256" },
        { name: "description", type: "string" },
      ], name: "oftFeeDetails", type: "tuple[]" },
      { components: [
        { name: "amountSentLD", type: "uint256" },
        { name: "amountReceivedLD", type: "uint256" },
      ], name: "oftReceipt", type: "tuple" },
    ],
    stateMutability: "view",
    type: "function",
  },
  {
    inputs: [
      { components: [
        { name: "dstEid", type: "uint32" },
        { name: "to", type: "bytes32" },
        { name: "amountLD", type: "uint256" },
        { name: "minAmountLD", type: "uint256" },
        { name: "extraOptions", type: "bytes" },
        { name: "composeMsg", type: "bytes" },
        { name: "oftCmd", type: "bytes" },
      ], name: "_sendParam", type: "tuple" },
      { name: "_payInLzToken", type: "bool" },
    ],
    name: "quoteSend",
    outputs: [{ components: [
      { name: "nativeFee", type: "uint256" },
      { name: "lzTokenFee", type: "uint256" },
    ], name: "msgFee", type: "tuple" }],
    stateMutability: "view",
    type: "function",
  },
  {
    inputs: [
      { components: [
        { name: "dstEid", type: "uint32" },
        { name: "to", type: "bytes32" },
        { name: "amountLD", type: "uint256" },
        { name: "minAmountLD", type: "uint256" },
        { name: "extraOptions", type: "bytes" },
        { name: "composeMsg", type: "bytes" },
        { name: "oftCmd", type: "bytes" },
      ], name: "_sendParam", type: "tuple" },
      { components: [
        { name: "nativeFee", type: "uint256" },
        { name: "lzTokenFee", type: "uint256" },
      ], name: "_fee", type: "tuple" },
      { name: "_refundAddress", type: "address" },
    ],
    name: "send",
    outputs: [
      { components: [
        { name: "guid", type: "bytes32" },
        { name: "nonce", type: "uint64" },
        { components: [
          { name: "nativeFee", type: "uint256" },
          { name: "lzTokenFee", type: "uint256" },
        ], name: "fee", type: "tuple" },
      ], name: "msgReceipt", type: "tuple" },
      { components: [
        { name: "amountSentLD", type: "uint256" },
        { name: "amountReceivedLD", type: "uint256" },
      ], name: "oftReceipt", type: "tuple" },
    ],
    stateMutability: "payable",
    type: "function",
  },
] as const;
