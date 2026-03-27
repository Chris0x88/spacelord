import { describe, it, expect } from "vitest";

describe("usdt0_bridge validation", () => {
  it("rejects unsupported chain", async () => {
    const { usdt0Bridge } = await import("../src/tools/bridge");
    const mockProvider = {} as any;
    const mockSigner = { getAddress: async () => "0x1234567890abcdef1234567890abcdef12345678" } as any;

    const result = await usdt0Bridge.handler(
      { amount: 50, destChain: "polygon", recipientAddress: "0x1234567890abcdef1234567890abcdef12345678" },
      mockProvider,
      mockSigner,
    );
    expect(result.success).toBe(false);
    expect(result.error).toContain("Unsupported chain");
  });

  it("rejects invalid EVM address", async () => {
    const { usdt0Bridge } = await import("../src/tools/bridge");
    const mockProvider = {} as any;
    const mockSigner = { getAddress: async () => "0x1234567890abcdef1234567890abcdef12345678" } as any;

    const result = await usdt0Bridge.handler(
      { amount: 50, destChain: "arbitrum", recipientAddress: "not-an-address" },
      mockProvider,
      mockSigner,
    );
    expect(result.success).toBe(false);
    expect(result.error).toContain("Invalid EVM address");
  });
});

describe("USDT0 Bridge Plugin", () => {
  it("exports plugin class with 4 tools", async () => {
    const { USDT0BridgePlugin } = await import("../src/plugin");
    const plugin = new USDT0BridgePlugin();
    expect(plugin.name).toBe("usdt0-bridge");
    expect(plugin.getTools()).toHaveLength(4);
  });

  it("get_supported_chains returns data", async () => {
    const { usdt0GetSupportedChains } = await import("../src/tools/get-supported-chains");
    const result = await usdt0GetSupportedChains.handler();
    expect(result.source.eid).toBe(30285);
    expect(result.destinations.length).toBeGreaterThan(0);
    expect(result.decimals).toBe(6);
  });
});
