import { describe, it, expect } from "vitest";
import { SUPPORTED_CHAINS, HEDERA_CONFIG, USDT0_DECIMALS } from "../src/contracts/addresses";

describe("USDT0 Bridge Constants", () => {
  it("has correct Hedera OFT address", () => {
    expect(HEDERA_CONFIG.oftAddress).toBe("0xe3119e23fC2371d1E6b01775ba312035425A53d6");
  });

  it("has correct Hedera token address", () => {
    expect(HEDERA_CONFIG.tokenAddress).toBe("0x00000000000000000000000000000000009Ce723");
  });

  it("has correct Hedera EID", () => {
    expect(HEDERA_CONFIG.eid).toBe(30285);
  });

  it("has Arbitrum chain config", () => {
    const arb = SUPPORTED_CHAINS["arbitrum"];
    expect(arb).toBeDefined();
    expect(arb.eid).toBe(30110);
    expect(arb.chainId).toBe(42161);
  });

  it("uses 6 decimals", () => {
    expect(USDT0_DECIMALS).toBe(6);
  });
});
