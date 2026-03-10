================================================
PACMAN: AI AGENTIC TRADING PRIMITIVE
Mentor Review Script & Walkthrough 
================================================

Welcome! If you are reviewing this project for the Hedera Apex Hackathon 2026, 
this script provides a safe, curated path to test Pacman's core capabilities.

Pacman is a pure-terminal interface completely bypassing web frontends. It 
allows users, and more importantly, local AI Models (like OpenClaw/AutoGPT), to 
navigate the SaucerSwap V2 infrastructure seamlessly using Natural Language.

==============================
PHASE 1: SAFE SETUP 
==============================
Before starting, we highly recommend you use a DISPOSABLE TEST WALLET with 
roughly 5-10 HBAR. Do not use your primary HBAR holding wallet.

1. Clone and run (auto-installs environment via uv):
   git clone https://github.com/chris0x88/pacman.git
   cd pacman
   ./launch.sh

2. Run the interactive setup (if first time):
   ./launch.sh setup

3. Follow the prompts to input your Hedera Account ID and Private Key. 
   When asked, keep Simulation Mode turned ON! (This prevents actual gas loss).

4. Enter the interactive Pacman shell:
   ./launch.sh

(All commands below should be typed directly into the 'pacman>' interactive prompt).

==============================
PHASE 2: CORE ACTIONS
==============================
Run these exact commands in your terminal to see the NLP parser translate language 
into hardened EVM transaction data structures without a browser.

1. View your wallet state and tokens:
   balance

2. Test the NLP Swap Engine (Exact Input):
   swap 10 HBAR for USDC

3. Test Exact-Output Routing:
   swap USDC to get 500 HBAR

4. Test Sub-Account Derivation (Disposable Keys):
   account --new
   swap 5 HBAR for USDC

==============================
PHASE 3: PASSIVE AUTONOMY
==============================
Pacman features an autonomous local daemon for executing Limit Orders while 
the user sleeps or while an AI model does other background tasks.

1. Create a passive limit order target:
   orders buy 100 USDC below 0.15 HBAR

2. Start the autonomous daemon:
   ./launch.sh daemon-start

3. Check the daemon log stream:
   tail -f daemon_output.log

4. Stop the daemon:
   ./launch.sh daemon-stop

5. Review the massive test suite:
   uv run python tests/massive_test_suite.py
   (Verifies 50+ NLP, Routing, and Limit Order scenarios in simulation)

NOTE: Currently, the daemon runs a local background thread. We are incrementally 
adding features! Our roadmap step-up is migrating this intent-logic directly into 
the Hedera Schedule Service (HSS) & smart contracts, allowing portfolios to 
automatically rebalance on-chain 24/7 based on user demand.

==============================
PHASE 4: AGENT CONFIGURATION
==============================
The primary objective of this project is serving as the "Hand" for AI Models.
An agent like OpenClaw should be able to clone, scan, and set up the entire program 
hands-free for its own use.

Please review the following file in the repo to see exactly how an AI Agent 
hooks into these tools to act entirely autonomously on the Hedera network:

- .agent/agents.md (The system prompt instruction manual for AI agents)

Thank you for reviewing Pacman!
