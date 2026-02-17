# SaucerSwap API & Price Discovery Guide

This document explains how Pacman handles price discovery and why configuring a personal SaucerSwap API key is recommended for professional trading.

## 1. Authentication Levels

### Public Mode (Default)
Out of the box, Pacman uses a **Public Demo Key** provided by SaucerSwap. 
- **Pros**: Works immediately without configuration.
- **Cons**: Globally rate-limited. If many users are using it simultaneously, price updates may fail or lag.

### Private Mode (Recommended)
By adding your own API key to the `.env` file, you unlock dedicated rate limits and higher reliability.
- **Key Format**: `apiXXXXXXXXXXXXXXXXXXXXXXXXXXXX`
- **How to Get One**: Contact `support@saucerswap.finance`.

## 2. Price Discovery & Fallbacks

When pool data cannot be fetched or is restricted, Pacman uses a multi-tier fallback system:

1.  **Primary**: SaucerSwap V2 Pool Data (HTS & ERC20 variants).
2.  **Fallback 1**: **CoinGecko API** (Public) - Good for major tokens (HBAR, SAUCE, USDC).
3.  **Fallback 2**: **Binance API** (Public) - Used primarily for HBAR/USDT reference prices.

## 3. The Accuracy Trade-off

> [!WARNING]
> **Limited Accuracy in Public Mode**
> Without a personal SaucerSwap API key, you may not be able to fetch **Full Pool Depth and Liquidity Distribution**. This means:
> 1.  **Higher Slippage Risk**: The router cannot accurately predict price impact for large trades.
> 2.  **Stale Prices**: Public fallbacks may lag behind on-chain reality during high volatility.
> 3.  **Missing Variants**: Some niche HTS tokens may not have public fallback prices on Binance or CoinGecko.

For high-accuracy price discovery and safe execution of larger swaps, we strongly recommend obtaining and setting your own `SAUCERSWAP_API_KEY_MAINNET` in your `.env` file.
