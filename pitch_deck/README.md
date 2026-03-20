# Pacman Pitch Deck Generator

Rebuilt pitch deck for Pacman — autonomous AI agent for DeFi on Hedera.

## Files

- `generate_deck.js` - Main script that generates the PPTX deck
- `package.json` - Node.js dependencies (pptxgenjs v4.0.1)
- `Pacman_Pitch_Deck.pptx` - Generated PowerPoint deck

## Generating the Deck

```bash
node generate_deck.js
```

This creates `Pacman_Pitch_Deck.pptx`.

## Slide Structure (11 slides)

1. **Title Slide** - Pacman, Hackathon, Track/Bounty
2. **The Problem** - Why DeFi is manual labor
3. **The Solution** - 4 core capabilities (wallet, swaps, rebalancer, HCS signals)
4. **Architecture** - Plugin system moat, SaucerSwap V2 CLI story
5. **Onboarding** - 5 minutes from zero to trading (3-step process)
6. **The Vision** - Why pay Vanguard? Sasspocalypse
7. **Hedera Integration** - Depth across HTS, HCS, EVM, Mirror Node
8. **Real Mainnet Trading** - No simulations, real transactions
9. **What We've Learned** - 11 anti-patterns documented
10. **Team & Timeline** - Solo build, phased approach
11. **Call to Action** - Contact, GitHub, HCS topic

## Key Narrative Changes

### Slide 3: Solution
**Old:** Two-bot architecture  
**New:** One autonomous AI agent with 4 core capabilities
- Self-custody wallet (🟡)
- Conversational swaps (💱)
- Power Law rebalancer (⚙️)
- HCS signal marketplace (📡)

### Slide 4: Architecture
**Old:** Probably generic architecture  
**New:** The real story — built SaucerSwap V2 CLI from scratch because docs were incomplete. Now open source. Plugin architecture as the moat.

### Slide 5: Onboarding (NEW)
**Added:** 5-minute flow from zero to trading
- Step 1: `./launch.sh setup` (wizard)
- Step 2: Fund wallet (testnet/mainnet)
- Step 3: Connect via OpenClaw (instant deployment)
- "OpenClaw × Pacman = easiest path to Hedera"

### Slide 6: The Vision (NEW)
**Added:** "Why Pay Vanguard?" narrative
- Vanguard: $30/year on $100k
- Hedera: $0.04/year on $100k
- Index funds as autonomous agents
- The Sasspocalypse vision

## Design

- Dark theme: `#0a0a0f` background
- Cyan accents: `#00d4ff`
- Card-based layout with colored boxes
- Professional, startup-style design
- No external images (all procedural)

## Requirements Met

✅ Slide 3: ONE autonomous AI agent, 4 capabilities (no two-bot split)
✅ Slide 4: Real architecture story (SaucerSwap V2 CLI, plugin moat)
✅ NEW Slide 5: Onboarding journey (5 minutes)
✅ NEW Slide 6: Vision narrative (Sasspocalypse)
✅ Slide 1-2: Problem/title (kept)
✅ Slides 7-11: Deep integration, lessons, timeline, CTA (kept/improved)
✅ Dark theme maintained
✅ PptxGenJS library used
