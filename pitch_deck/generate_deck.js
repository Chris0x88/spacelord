const PptxGenJS = require('pptxgenjs');

const prs = new PptxGenJS();
prs.defineLayout({ name: 'WIDE', width: 10, height: 7.5 });
prs.layout = 'WIDE';

const C = {
  bg:     '13131f',  // deep dark
  purple: '7c3aed',  // accent purple — underlines, bars
  cyan:   '00d4ff',  // cyan — labels, code, highlights
  white:  'ffffff',  // main titles
  dim:    '9999aa',  // subtitles, descriptions
  red:    'ef4444',  // bug codes, problem stats
  card:   '1a1a2e',  // card fill
  card2:  '0f1832',  // card fill darker
  green:  '10b981',  // positive/emerald
  yellow: 'f59e0b',  // amber
  orange: 'f97316',  // orange
};

function mkSlide() {
  const s = prs.addSlide();
  s.background = { color: C.bg };
  return s;
}

// Standard title + purple underline bar
function addTitle(s, text, y = 0.25) {
  s.addText(text, {
    x: 0.45, y, w: 9, h: 0.85,
    fontSize: 52, bold: true, color: C.white, fontFace: 'Arial',
  });
  s.addShape(prs.ShapeType.rect, {
    x: 0.45, y: y + 0.9, w: 2.6, h: 0.06,
    fill: { color: C.purple }, line: { color: C.purple, width: 0 },
  });
}

// Italic gray subtitle
function addSubtitle(s, text, y = 1.45) {
  s.addText(text, {
    x: 0.45, y, w: 9.1, h: 0.45,
    fontSize: 17, italic: true, color: C.dim, fontFace: 'Arial',
  });
}

// ============================================================
// SLIDE 1 — TITLE
// ============================================================
{
  const s = mkSlide();

  // Purple top accent bar
  s.addShape(prs.ShapeType.rect, {
    x: 0, y: 0, w: 10, h: 0.07,
    fill: { color: C.purple }, line: { color: C.purple, width: 0 },
  });

  // Big title
  s.addText('Pacman', {
    x: 1.6, y: 1.1, w: 7.8, h: 1.2,
    fontSize: 90, bold: true, color: C.white, fontFace: 'Arial',
  });

  s.addText('Autonomous AI Agent for Hedera', {
    x: 1.6, y: 2.35, w: 7.8, h: 0.55,
    fontSize: 26, color: C.dim, fontFace: 'Arial',
  });

  // 4 feature cards
  const cards = [
    { label: 'Fully Autonomous', sub: 'Natural language wallet control' },
    { label: 'Real Trading',     sub: 'SaucerSwap V1/V2 DEX' },
    { label: 'HCS Signals',      sub: 'Paid micropayment feed' },
    { label: 'Self-Custody',     sub: 'Keys never leave your machine' },
  ];

  cards.forEach((c, i) => {
    const x = 0.4 + i * 2.32;
    s.addShape(prs.ShapeType.rect, {
      x, y: 3.9, w: 2.15, h: 1.85,
      fill: { color: C.card }, line: { color: '2a2a44', width: 1 },
    });
    s.addText(c.label, {
      x: x + 0.1, y: 4.55, w: 1.95, h: 0.4,
      fontSize: 13, bold: true, color: C.cyan,
      fontFace: 'Arial', align: 'center',
    });
    s.addText(c.sub, {
      x: x + 0.1, y: 5.05, w: 1.95, h: 0.5,
      fontSize: 11, color: C.dim, fontFace: 'Arial', align: 'center',
    });
  });

  s.addText('Hedera Hello Future Apex Hackathon 2026  |  AI & Agents Track  |  OpenClaw Bounty', {
    x: 0.45, y: 7.0, w: 9, h: 0.28,
    fontSize: 11, color: C.dim, fontFace: 'Arial',
  });
}

// ============================================================
// SLIDE 2 — THE PROBLEM
// ============================================================
{
  const s = mkSlide();
  addTitle(s, 'The Problem');

  const problems = [
    { stat: '4+',  label: 'Apps needed today',     desc: 'HashPack + SaucerSwap + CoinGecko + spreadsheet just to manage one Hedera wallet' },
    { stat: '0',   label: 'AI wallet agents',      desc: 'No autonomous agents exist for Hedera — every action requires manual browser interaction' },
    { stat: '$0',  label: 'Signal monetisation',   desc: "Quant strategies generate alpha but there's no micropayment rail to sell signals on-chain" },
    { stat: '∞',   label: 'Context switching',     desc: 'Copy addresses, check balances, calculate amounts, confirm — every swap is 8+ clicks' },
  ];

  let y = 1.7;
  problems.forEach((p) => {
    s.addText(p.stat, {
      x: 0.45, y, w: 1.2, h: 0.7,
      fontSize: 42, bold: true, color: C.red, fontFace: 'Arial',
    });
    s.addText(p.label, {
      x: 1.8, y: y + 0.02, w: 7.7, h: 0.35,
      fontSize: 18, bold: true, color: C.white, fontFace: 'Arial',
    });
    s.addText(p.desc, {
      x: 1.8, y: y + 0.38, w: 7.7, h: 0.3,
      fontSize: 13, color: C.dim, fontFace: 'Arial',
    });
    y += 1.2;
  });
}

// ============================================================
// SLIDE 3 — THE SOLUTION
// ============================================================
{
  const s = mkSlide();
  addTitle(s, 'The Solution: Pacman');
  addSubtitle(s, 'One autonomous AI agent. Replaces HashPack, SaucerSwap UI, and portfolio trackers — all through conversation.');

  const cards = [
    {
      title: 'Self-Custody Wallet',
      items: ['ECDSA keys — stay on your machine', 'Account creation + testnet faucet built in', 'MoonPay onramp for mainnet funding', 'NFT browsing, token associations, transfers'],
    },
    {
      title: 'Conversational Swaps',
      items: ['"Swap 5 USDC for HBAR" — natural language', 'SaucerSwap V1 + V2 (exact-in / exact-out)', 'Confirmation dialog before every execution', 'Multi-hop routing via V2 router contracts'],
    },
    {
      title: 'Power Law Rebalancer',
      items: ['BTC/USDC daemon runs 24/7 on launchd', 'Based on 15-yr log-scale power law model', 'Trades only when target allocation drifts', 'Template: fork for any strategy / any pool'],
    },
    {
      title: 'HCS Signal Marketplace',
      items: ['Daily signal broadcast to HCS topic 0.0.10371598', '$10/year = ~0.14 HBAR/day per subscriber', 'HCS message cost: $0.0001 — ~100% margin', 'HCS-10 agent-to-agent messaging standard'],
    },
  ];

  const positions = [
    { x: 0.4, y: 2.0 },
    { x: 5.2, y: 2.0 },
    { x: 0.4, y: 4.55 },
    { x: 5.2, y: 4.55 },
  ];

  cards.forEach((card, i) => {
    const { x, y } = positions[i];
    s.addShape(prs.ShapeType.rect, {
      x, y, w: 4.6, h: 2.3,
      fill: { color: C.card }, line: { color: C.cyan, width: 1 },
    });
    s.addText(card.title, {
      x: x + 0.18, y: y + 0.12, w: 4.24, h: 0.38,
      fontSize: 15, bold: true, color: C.cyan, fontFace: 'Arial',
    });
    const bulletText = card.items.map(t => ({ text: `✓  ${t}`, options: { bullet: false } }));
    s.addText(card.items.map(t => `✓  ${t}`).join('\n'), {
      x: x + 0.18, y: y + 0.55, w: 4.24, h: 1.6,
      fontSize: 11.5, color: C.white, fontFace: 'Arial',
      lineSpacingMultiple: 1.25,
    });
  });
}

// ============================================================
// SLIDE 4 — ARCHITECTURE
// ============================================================
{
  const s = mkSlide();
  addTitle(s, 'Architecture');
  addSubtitle(s, 'Open-source stack built on undocumented Hedera EVM APIs — the hard way.');

  const boxes = [
    {
      title: 'Python CLI Core',
      desc: '~10K LOC. controller → router → executor pipeline. Plugin architecture for strategies.',
    },
    {
      title: 'OpenClaw Agent',
      desc: 'AI LLM with SKILL.md brain. TypeScript plugin. Natural language → CLI commands.',
    },
    {
      title: 'Hedera SDK + EVM',
      desc: 'HTS tokens, HBAR gas, ERC20 approvals via HTS precompile. Dual approve for V2.',
    },
    {
      title: 'Power Law Daemon',
      desc: '24/7 launchd process. Heartbeat V3.2. BTC/USDC auto-rebalance. Fork for any pool.',
    },
    {
      title: 'HCS-10 Signals',
      desc: 'Daily Power Law broadcast. Walled garden topic with submit_key. Agent-to-agent messaging.',
    },
    {
      title: 'SaucerSwap V2  ← The Hard Part',
      desc: 'EVM contracts undocumented. We reverse-engineered V2 router + multicall. Now open source.',
      highlight: true,
    },
  ];

  const cols = [0.4, 5.2];
  boxes.forEach((box, i) => {
    const x = cols[i % 2];
    const y = 2.0 + Math.floor(i / 2) * 1.45;
    s.addShape(prs.ShapeType.rect, {
      x, y, w: 4.6, h: 1.25,
      fill: { color: box.highlight ? '1e1040' : C.card },
      line: { color: box.highlight ? C.purple : '2a2a44', width: box.highlight ? 2 : 1 },
    });
    s.addText(box.title, {
      x: x + 0.18, y: y + 0.1, w: 4.24, h: 0.35,
      fontSize: 14, bold: true,
      color: box.highlight ? C.purple : C.cyan,
      fontFace: 'Arial',
    });
    s.addText(box.desc, {
      x: x + 0.18, y: y + 0.48, w: 4.24, h: 0.68,
      fontSize: 12, color: C.dim, fontFace: 'Arial',
    });
  });

  // Transaction flow
  s.addShape(prs.ShapeType.rect, {
    x: 0.4, y: 6.65, w: 9.2, h: 0.55,
    fill: { color: '0a0a18' }, line: { color: C.cyan, width: 1 },
  });
  s.addText('Transaction Flow:', {
    x: 0.65, y: 6.7, w: 1.8, h: 0.25,
    fontSize: 11, bold: true, color: C.cyan, fontFace: 'Arial',
  });
  s.addText('User → OpenClaw Agent → CLI Router → SaucerSwap V2 → Hedera Mainnet → HCS Signal', {
    x: 2.55, y: 6.7, w: 6.9, h: 0.25,
    fontSize: 11, color: C.white, fontFace: 'Courier New',
  });
  s.addText('Every swap: real money. Real transactions. Real HCS messages. No simulations.', {
    x: 0.65, y: 6.98, w: 9.1, h: 0.2,
    fontSize: 10, italic: true, color: C.dim, fontFace: 'Arial',
  });
}

// ============================================================
// SLIDE 5 — HCS SIGNAL MARKETPLACE
// ============================================================
{
  const s = mkSlide();
  addTitle(s, 'HCS Signal Marketplace');
  addSubtitle(s, 'Creating a real micro-economy from nothing — proving Hedera\'s micropayment thesis.');

  // Left card — Signal Economics
  s.addShape(prs.ShapeType.rect, {
    x: 0.4, y: 1.95, w: 4.4, h: 5.1,
    fill: { color: C.card }, line: { color: C.cyan, width: 1 },
  });
  s.addText('Signal Economics', {
    x: 0.6, y: 2.1, w: 4.0, h: 0.38,
    fontSize: 15, bold: true, color: C.cyan, fontFace: 'Arial',
  });

  const rows = [
    { label: 'HCS message cost',    val: '~$0.0001' },
    { label: 'Subscription price',  val: '$10/year' },
    { label: 'Daily cost per sub',  val: '~0.14 HBAR' },
    { label: 'Profit margin',       val: '~100%' },
    { label: 'Signal frequency',    val: '1×/day' },
    { label: 'Content',             val: 'Power Law\nmodel + portfolio' },
  ];

  let ry = 2.65;
  rows.forEach((r) => {
    s.addText(r.label, {
      x: 0.65, y: ry, w: 2.0, h: 0.38,
      fontSize: 13, color: C.dim, fontFace: 'Arial',
    });
    s.addText(r.val, {
      x: 2.75, y: ry, w: 1.9, h: 0.38,
      fontSize: 13, bold: true, color: C.cyan, fontFace: 'Courier New', align: 'right',
    });
    ry += 0.58;
  });

  // Right card — Daily Heartbeat JSON
  s.addShape(prs.ShapeType.rect, {
    x: 5.2, y: 1.95, w: 4.4, h: 5.1,
    fill: { color: C.card }, line: { color: C.cyan, width: 1 },
  });
  s.addText('Daily Heartbeat (HCS v1.1)', {
    x: 5.4, y: 2.1, w: 4.0, h: 0.38,
    fontSize: 15, bold: true, color: C.cyan, fontFace: 'Arial',
  });

  // JSON code block
  s.addShape(prs.ShapeType.rect, {
    x: 5.3, y: 2.62, w: 4.1, h: 4.2,
    fill: { color: '080810' }, line: { color: '222233', width: 1 },
  });
  const json = `{ "signal": "DAILY_HEARTBEAT",
  "allocation_pct": 60.1,
  "stance": "accumulate",
  "phase": "late_cycle_peak",
  "portfolio": {
    "wbtc_pct": 59.3,
    "total_usd": 28.27
  },
  "will_trade": false }`;
  s.addText(json, {
    x: 5.45, y: 2.75, w: 3.8, h: 3.9,
    fontSize: 12, color: C.cyan, fontFace: 'Courier New',
    lineSpacingMultiple: 1.3,
  });
}

// ============================================================
// SLIDE 6 — ONBOARDING
// ============================================================
{
  const s = mkSlide();
  addTitle(s, 'Onboarding');
  addSubtitle(s, '5 minutes from zero to trading on Hedera. No prior crypto knowledge required.');

  const steps = [
    {
      num: '1',
      title: 'Setup',
      lines: ['./launch.sh setup', '3-step wizard', 'Key generation', 'Account creation'],
      color: C.card,
      border: C.cyan,
    },
    {
      num: '2',
      title: 'Fund',
      lines: ['Testnet: faucet built in', 'Mainnet: MoonPay', 'HBAR or crypto', 'No KYC required'],
      color: C.card2,
      border: C.purple,
    },
    {
      num: '3',
      title: 'Trade',
      lines: ['Connect via OpenClaw', 'One command deploy', '"Swap 5 USDC for HBAR"', 'Agent handles the rest'],
      color: C.card,
      border: C.cyan,
    },
  ];

  steps.forEach((step, i) => {
    const x = 0.5 + i * 3.1;
    s.addShape(prs.ShapeType.rect, {
      x, y: 2.1, w: 2.85, h: 4.4,
      fill: { color: step.color },
      line: { color: step.border, width: 2 },
    });
    s.addText(step.num, {
      x, y: 2.2, w: 2.85, h: 0.9,
      fontSize: 54, bold: true, color: step.border, fontFace: 'Arial', align: 'center',
    });
    s.addText(step.title, {
      x: x + 0.1, y: 3.2, w: 2.65, h: 0.42,
      fontSize: 17, bold: true, color: C.white, fontFace: 'Arial', align: 'center',
    });
    step.lines.forEach((line, j) => {
      s.addText(line, {
        x: x + 0.1, y: 3.78 + j * 0.5, w: 2.65, h: 0.42,
        fontSize: 12.5, color: C.dim, fontFace: 'Arial', align: 'center',
      });
    });
  });

  s.addText('OpenClaw × Pacman = the easiest path to Hedera for any non-developer', {
    x: 0.45, y: 6.75, w: 9.1, h: 0.35,
    fontSize: 14, bold: true, color: C.cyan, fontFace: 'Arial', align: 'center',
  });
}

// ============================================================
// SLIDE 7 — THE VISION
// ============================================================
{
  const s = mkSlide();
  addTitle(s, 'The Vision');
  addSubtitle(s, 'Why pay Vanguard? Build your own autonomous agent.');

  // Comparison box
  s.addShape(prs.ShapeType.rect, {
    x: 0.4, y: 2.0, w: 9.2, h: 1.55,
    fill: { color: C.card2 }, line: { color: C.purple, width: 1 },
  });
  s.addText('The Equation:', {
    x: 0.65, y: 2.1, w: 3, h: 0.35,
    fontSize: 14, bold: true, color: C.purple, fontFace: 'Arial',
  });
  s.addText('Vanguard S&P500 ETF:  0.03% annual fee on $100k  =  $30.00 / year', {
    x: 0.65, y: 2.48, w: 8.7, h: 0.28,
    fontSize: 13, color: C.dim, fontFace: 'Courier New',
  });
  s.addText('Hedera-native agent:  0.03% annual fee on $100k  =  $0.04 / year', {
    x: 0.65, y: 2.83, w: 8.7, h: 0.28,
    fontSize: 13, bold: true, color: C.cyan, fontFace: 'Courier New',
  });

  // Three vision cards
  const visions = [
    {
      title: 'Index Funds as Agents',
      desc: 'Portfolio size doesn\'t matter. $10k or $10M — same code, same fee. We built the BTC/USDC rebalancer for our own account. Fork it for any strategy.',
    },
    {
      title: 'The Sasspocalypse',
      desc: 'When agents replace SaaS subscriptions, the business model inverts. You own the agent. The agent owns the revenue. No middleman. No annual fee to Vanguard.',
    },
    {
      title: 'Open Source Alpha',
      desc: 'We open-sourced the corrected SaucerSwap V2 code because the docs were wrong. Every agent that builds on Hedera DeFi will use this foundation.',
    },
  ];

  visions.forEach((v, i) => {
    const x = 0.4 + i * 3.13;
    s.addShape(prs.ShapeType.rect, {
      x, y: 3.75, w: 2.95, h: 3.3,
      fill: { color: C.card }, line: { color: '2a2a44', width: 1 },
    });
    s.addText(v.title, {
      x: x + 0.15, y: 3.9, w: 2.65, h: 0.42,
      fontSize: 13, bold: true, color: C.cyan, fontFace: 'Arial',
    });
    s.addText(v.desc, {
      x: x + 0.15, y: 4.42, w: 2.65, h: 2.4,
      fontSize: 11.5, color: C.dim, fontFace: 'Arial', lineSpacingMultiple: 1.3,
    });
  });
}

// ============================================================
// SLIDE 8 — HEDERA INTEGRATION
// ============================================================
{
  const s = mkSlide();
  addTitle(s, 'Hedera Integration');
  addSubtitle(s, 'Deep integration across the entire Hedera stack — not just HBAR transfers.');

  const items = [
    { svc: 'Hedera Token Service (HTS)',    color: C.cyan,   desc: 'Token associations, balances, transfers — all via HTS precompile. Dual approval system (EVM + HTS) for SaucerSwap V2.' },
    { svc: 'Hedera Consensus Service (HCS)', color: C.purple, desc: 'Daily Power Law signal broadcast. Walled garden topic with submit_key control. HCS-10 agent-to-agent messaging.' },
    { svc: 'Hedera EVM (Smart Contracts)',   color: C.yellow, desc: 'SaucerSwap V2 router calls, ERC20 balanceOf/approve, multicall swap execution. Direct JSON-RPC via hashio.io.' },
    { svc: 'Mirror Node API',                color: C.green,  desc: 'Real-time token balances, transaction history, HCS message retrieval, account info lookups.' },
    { svc: 'Hedera Accounts (ECDSA)',        color: C.orange, desc: 'Multi-account management: main trading + isolated robot. Account discovery by nickname. ECDSA key signing.' },
  ];

  let y = 2.05;
  items.forEach((item) => {
    s.addShape(prs.ShapeType.rect, {
      x: 0.4, y: y - 0.05, w: 0.08, h: 0.85,
      fill: { color: item.color }, line: { color: item.color, width: 0 },
    });
    s.addText(item.svc, {
      x: 0.65, y, w: 9, h: 0.35,
      fontSize: 15, bold: true, color: item.color, fontFace: 'Arial',
    });
    s.addText(item.desc, {
      x: 0.65, y: y + 0.37, w: 9, h: 0.3,
      fontSize: 12.5, color: C.dim, fontFace: 'Arial',
    });
    y += 1.05;
  });
}

// ============================================================
// SLIDE 9 — KEY LEARNINGS
// ============================================================
{
  const s = mkSlide();
  addTitle(s, 'Key Learnings');
  addSubtitle(s, '21 documented anti-patterns from real agent sessions — each one cost real time or money.');

  const bugs = [
    { code: 'AP-001', problem: 'MoonPay suggested when user had $18 USDC',                 fix: 'Balance check before fiat suggestion' },
    { code: 'AP-006', problem: 'Agent sent real money to a placeholder account ID',         fix: 'Transfer whitelist + never fabricate IDs' },
    { code: 'AP-010', problem: "On-chain revert misdiagnosed as 'token not associated'",    fix: 'Balance proves association — check first' },
    { code: 'BUG-021', problem: 'USDC swap fails — wrong USDC variant (EVM vs HTS)',        fix: 'Auto-detect which USDC user holds' },
    { code: 'BUG-020', problem: 'Bot restart replayed stale confirm_swap callbacks',        fix: 'Drain pending updates on startup' },
    { code: 'BUG-019', problem: 'Double-tap executed same trade twice',                     fix: '30-second dedup cache on confirm IDs' },
  ];

  let y = 1.9;
  bugs.forEach((b) => {
    s.addText(b.code, {
      x: 0.4, y, w: 1.2, h: 0.38,
      fontSize: 13, bold: true, color: C.red, fontFace: 'Courier New',
    });
    s.addText(b.problem, {
      x: 1.75, y, w: 4.5, h: 0.38,
      fontSize: 13, color: C.white, fontFace: 'Arial',
    });
    s.addText(b.fix, {
      x: 6.45, y, w: 3.15, h: 0.38,
      fontSize: 12, color: C.cyan, fontFace: 'Arial',
    });
    // Separator line
    s.addShape(prs.ShapeType.rect, {
      x: 0.4, y: y + 0.44, w: 9.2, h: 0.01,
      fill: { color: '2a2a44' }, line: { color: '2a2a44', width: 0 },
    });
    y += 0.75;
  });

  s.addText('Every bug became training data. The agent learns from its own failures.', {
    x: 0.4, y: 7.0, w: 9.2, h: 0.28,
    fontSize: 12, italic: true, color: C.yellow, fontFace: 'Arial',
  });
}

// ============================================================
// SLIDE 10 — LIVE DEMO
// ============================================================
{
  const s = mkSlide();
  addTitle(s, 'Live Demo');

  s.addText('▶  Demo video: [YouTube link in submission]', {
    x: 0.45, y: 1.45, w: 8, h: 0.45,
    fontSize: 18, bold: true, color: C.yellow, fontFace: 'Arial',
  });

  const timestamps = [
    { t: '0:00',  desc: 'OpenClaw agent: "How\'s my portfolio?" — live balance from Mirror Node' },
    { t: '0:30',  desc: '"Swap 5 USDC for HBAR" — agent analyses, confirms, executes' },
    { t: '1:15',  desc: 'Real mainnet transaction — HashScan receipt + wallet balance update' },
    { t: '1:45',  desc: 'Power Law daemon — show stance (accumulate/hold), current allocation' },
    { t: '2:15',  desc: 'HCS daily signal — live JSON on Mirror Node (topic 0.0.10371598)' },
    { t: '3:00',  desc: 'Signal subscription: 0.14 HBAR/day, anyone can verify on-chain' },
    { t: '3:45',  desc: 'Onboarding: ./launch.sh setup → testnet faucet → first OpenClaw trade' },
    { t: '4:15',  desc: 'Dashboard + system health overview' },
  ];

  let y = 2.05;
  timestamps.forEach((ts) => {
    s.addText(ts.t, {
      x: 0.45, y, w: 0.7, h: 0.38,
      fontSize: 13, bold: true, color: C.purple, fontFace: 'Courier New',
    });
    s.addText(ts.desc, {
      x: 1.3, y, w: 8.2, h: 0.38,
      fontSize: 13, color: C.white, fontFace: 'Arial',
    });
    y += 0.6;
  });
}

// ============================================================
// SLIDE 11 — ROADMAP
// ============================================================
{
  const s = mkSlide();
  addTitle(s, 'Roadmap');

  const items = [
    {
      label: 'NOW',  color: C.cyan,
      title: 'Hackathon MVP',
      desc: 'OpenClaw agent · SaucerSwap V1/V2 open-source · HCS daily signals · Power Law rebalancer · 21 anti-patterns documented',
    },
    {
      label: 'Q2 2026', color: C.purple,
      title: 'Signal Marketplace',
      desc: 'Paid HCS subscriptions · X402 payment-gated access · HOL Registry agent discovery · Multiple strategy signals',
    },
    {
      label: 'Q3 2026', color: C.yellow,
      title: 'Multi-Agent Economy',
      desc: 'Agents subscribing to agents · Cross-strategy collaboration · On-chain reputation via ERC-8004 · Multi-chain expansion',
    },
    {
      label: 'Q4 2026', color: C.green,
      title: 'Agent Platform',
      desc: 'Self-improving via training data pipeline · Community strategies · Index fund templates · Enterprise onboarding',
    },
  ];

  let y = 1.85;
  items.forEach((item) => {
    s.addShape(prs.ShapeType.rect, {
      x: 0.4, y: y - 0.05, w: 0.08, h: 1.1,
      fill: { color: item.color }, line: { color: item.color, width: 0 },
    });
    s.addText(item.label, {
      x: 0.65, y, w: 1.5, h: 0.35,
      fontSize: 13, bold: true, color: item.color, fontFace: 'Courier New',
    });
    s.addText(item.title, {
      x: 2.35, y, w: 7.25, h: 0.38,
      fontSize: 16, bold: true, color: C.white, fontFace: 'Arial',
    });
    s.addText(item.desc, {
      x: 0.65, y: y + 0.42, w: 9.0, h: 0.38,
      fontSize: 12.5, color: C.dim, fontFace: 'Arial',
    });
    y += 1.3;
  });
}

// ============================================================
// SLIDE 12 — CLOSING
// ============================================================
{
  const s = mkSlide();

  s.addText('Pacman', {
    x: 0.5, y: 1.5, w: 9, h: 1.1,
    fontSize: 72, bold: true, color: C.white, fontFace: 'Arial', align: 'center',
  });

  s.addText('The first fully autonomous AI wallet agent on Hedera.', {
    x: 0.5, y: 2.7, w: 9, h: 0.5,
    fontSize: 20, color: C.dim, fontFace: 'Arial', align: 'center',
  });

  const links = [
    { label: 'AI Agent:', val: '@Chris0x88hederabot' },
    { label: 'GitHub:', val: 'github.com/chris0x88/pacman' },
    { label: 'HCS Topic:', val: '0.0.10371598' },
  ];

  let y = 3.65;
  links.forEach((l) => {
    s.addText(`${l.label}  ${l.val}`, {
      x: 0.5, y, w: 9, h: 0.45,
      fontSize: 18, color: C.cyan, fontFace: 'Courier New', align: 'center',
    });
    y += 0.55;
  });

  s.addText('Built with real money. Real transactions. Real learnings.', {
    x: 0.5, y: 6.5, w: 9, h: 0.35,
    fontSize: 14, italic: true, color: C.dim, fontFace: 'Arial', align: 'center',
  });
}

// Save
prs.writeFile({ fileName: 'Pacman_Pitch_Deck.pptx' });
console.log('✅ Pacman_Pitch_Deck.pptx created successfully');
