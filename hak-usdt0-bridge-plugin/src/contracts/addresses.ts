import { ChainConfig } from "../types";

export const HEDERA_CONFIG = {
  eid: 30285,
  chainId: 295,
  tokenAddress: "0x00000000000000000000000000000000009Ce723",
  oftAddress: "0xe3119e23fC2371d1E6b01775ba312035425A53d6",
  hederaTokenId: "0.0.642851",
};

export const SUPPORTED_CHAINS: Record<string, ChainConfig> = {
  arbitrum: {
    name: "Arbitrum One",
    eid: 30110,
    chainId: 42161,
    tokenAddress: "0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9",
    oftAddress: "0x14E4A1B13bf7F943c8ff7C51fb60FA964A298D92",
  },
};

export const USDT0_DECIMALS = 6;
