# Pacman CLI Design Concept

This document outlines the visual identity and ASCII design standards for the **Pacman** terminal application (SaucerSwap V2 on Hedera). Use this brief to explain the aesthetic goals to a design expert.

## 1. The Visual Identity
The core aesthetic is **"Retro-Cyberpunk"**: combining 8-bit arcade nostalgia with a modern, high-contrast terminal interface.

### Core Metaphor
- **Pacman (`ᗧ`)**: Represents the user's trading agent, "consuming" liquidity and data.
- **Ghosts/Aliens (`👾`)**: Represent market data, pools, or external entities.
- **Pellets (`· · ·`)**: Represent data streams or price paths.

## 2. ASCII Banner
The primary brand mark uses high-impact block characters (`█`).

```text
    ██████╗  █████╗  ██████╗███╗   ███╗ █████╗ ███╗   ██╗
    ██╔══██╗██╔══██╗██╔════╝████╗ ████║██╔══██╗████╗  ██║
    ██████╔╝███████║██║     ██╔████╔██║███████║██╔██╗ ██║
    ██╔═══╝ ██╔══██║██║     ██║╚██╔╝██║██╔══██║██║╚██╗██║
    ██║     ██║  ██║╚██████╗██║ ╚═╝ ██║██║  ██║██║ ╚████║
    ╚═╝     ╚═╝  ╚═╝ ╚═════╝╚═╝     ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝
```

### Sub-Header Layout
The banner is anchored by a thin-line box containing the technical branding.

```text
    ╭──────────────────────────────────────────────────────╮
     ᗧ· · · 👾  SaucerSwap V2 on Hedera Hashgraph
    ╰──────────────────────────────────────────────────────╯
```

## 3. Color Palette (Dark Mode Optimized)
The interface uses a strict semantic color role system:

| Role | Color (ANSI) | HEX (approx) | Usage |
| :--- | :--- | :--- | :--- |
| **Accent** | Bright Cyan | `#5FFFFF` | Logos, Headlines, Primary focus |
| **Text** | Bright White | `#FFFFFF` | Primary data, Addresses, Amounts |
| **Muted** | Grey/White | `#CCCCCC` | Labels, Meta-data, Secondary text |
| **OK** | Bright Green | `#5FFF5F` | Success, Gains, Live status |
| **Warn** | Bright Yellow | `#FFFF5F` | Simulation mode, Pending actions |
| **Error** | Bright Red | `#FF5F5F` | Critical failures, Losses, Security |
| **Brand** | Purple | `#D75FFF` | Hedera specific branding |
| **Chrome** | Cyan | `#00AFAF` | Borders, Horizontal separators (`─`, `━`) |

## 4. UI Elements & Layout Standards
- **Separators**: Use solid horizontal lines (`─` for secondary, `━` for blocks).
- **Tables**: Minimalist layout. Headers in `MUTED` and `BOLD`. Rows aligned strictly in columns.
- **Progress**: Uses a heavy bar progress system (`━━━─────`).
- **Icons**:
    - `✓` Success
    - `✗` Failure
    - `⚠` Warning
    - `ᗧ` Pacman
    - `👾` Ghost

## 5. Design Request for Expert
When commissioning a professional to refine this:
1. **Refine the Logo**: Iterate on the "PACMAN" ASCII text to be more unique or stylized while remaining legible in standard terminal widths (80-120 chars).
2. **Iconography**: Design a custom set of 1-character or 2-character ASCII icons that fit the retro-arcade theme.
3. **Layout Balance**: Improve the spacing and "visual weight" of the headers to ensure information density remains high without looking cluttered.


This is a possible crazy TUI idea that needs to be refined: I think its too complex. But its interesting... 

import React, { useState, useEffect, useRef } from 'react';
import { 
  Zap, Target, Cpu, Activity, 
  Terminal, ShieldCheck, Crosshair, 
  TrendingUp, Globe, Wallet, Radar, Sword,
  Grip, MousePointer2, Skull, MessageSquare, 
  Send, ChevronRight, Hash
} from 'lucide-react';

const App = () => {
  // --- Simulation State ---
  // Agent is fixed at x:12 (Left side defense), aiming dynamically
  const [agent, setAgent] = useState({ x: 12, y: 55, aim: 2, state: 'SCANNING', targetIdx: null });
  const [saucers, setSaucers] = useState([]);
  const [bullets, setBullets] = useState([]);
  const [frame, setFrame] = useState(0);
  const [logs, setLogs] = useState([
    { id: 1, text: "PRIME_WARRIOR_SYSTEM: ONLINE", type: "info" },
    { id: 2, text: "ARMOR_PLATING: MAXIMUM", type: "success" },
    { id: 3, text: "DEFENDING THE HASHGRAPH...", type: "warn" }
  ]);
  const [stats, setStats] = useState({ swaps: 0, volume: 42100.50, hbar: 56200 });
  
  // --- Chat State ---
  const [chatInput, setChatInput] = useState('');
  const [chatHistory, setChatHistory] = useState([
    { role: 'system', text: 'SAUCERSWAP_CLI_AGENT v7.0 ONLINE. WAITING FOR INSTRUCTIONS...' },
    { role: 'ai', text: 'Prime Warrior Unit active. All systems nominal. Ready to engage.' }
  ]);
  const chatEndRef = useRef(null);

  const colors = {
    cyan: '#00f2ff',
    neonGreen: '#39ff14',
    neonPurple: '#bc13fe',
    neonYellow: '#fefe33',
    neonRed: '#ff3131',
    bg: '#020205',
    plasma: '#00fbff'
  };

  // --- THE DEADLY & EVIL MOTHERSHIP ---
  const ALIEN_MOTHERSHIP = `
      ▄▄█████████▄▄
    ▄███████████████▄
   ▐█████████████████▌
    ▀▀▀▀▀▀▀███▀▀▀▀▀▀▀
        ▄███████▄
       ▟█ █   █ █▙
      ▟█  █   █  █▙
     ▟█   █   █   █▙
    ⚡    ⚡   ⚡    ⚡`;

  // --- THE PRIME WARRIOR MECH (ASCII PRIME) ---
  const PRIME_MECH = `
      █▄                                      ▄█      
      ███▄                                  ▄███      
      █████▄          ▄▄████▄▄          ▄█████      
      ███████        ██████████        ███████      
      ███████        ██████████        ███████      
      ███████      ▄████████████▄      ███████      
      ███████    ▄████████████████▄    ███████      
      ███████   ████████▀▀▀▀████████   ███████      
      ███████   ███████      ███████   ███████      
      ███████   ███████      ███████   ███████      
      ███████   ███████      ███████   ███████      
   ▄▄██████████████████      ██████████████████▄▄   
  █████████████████████      █████████████████████  
  ▀▀▀▀▀▀███████████████      ███████████████▀▀▀▀▀▀  
        ███████████████      ███████████████        
        ███████▀▀▀▀▀▀▀▀      ▀▀▀▀▀▀▀▀███████        
        ██████    ◢██████████████◣    ██████        
        ██████    ◥██████████████◤    ██████        
        ██████▄      ▀▀▀████▀▀▀      ▄██████        
        ████████▄▄      ████      ▄▄████████        
        ████████████████████████████████████        
        ████████████████████████████████████        
        ████████████████████████████████████        
        ███████████  █  █  █  █  ███████████        
        ███████████  █  █  █  █  ███████████        
        ███████████  █  █  █  █  ███████████        
        ███████████  █  █  █  █  ███████████        
         ▀█████████  █  █  █  █  █████████▀         
           ▀███████  █  █  █  █  ███████▀           
             ▀█████  █▄▄█▄▄█▄▄█  █████▀             `;

  // Use the same heavy armor sprite for all aim angles to maintain visual integrity
  const MECH_POSES = [
    PRIME_MECH, PRIME_MECH, PRIME_MECH, PRIME_MECH, PRIME_MECH
  ];

  // Precise Muzzle Offsets (Calibrated to the "Eyes/Visor" of the Prime Warrior)
  // Since the sprite is static, we fire from the center-line visor area
  const MUZZLE_OFFSETS = [
    { x: 0, y: -5 }, // Up 45
    { x: 0, y: -5 }, // Up 20
    { x: 0, y: -5 }, // Straight
    { x: 0, y: -5 }, // Down 20
    { x: 0, y: -5 }  // Down 45
  ];

  // --- Initialization ---
  useEffect(() => {
    // Spawning pools further right to respect the Mech's space
    const pools = [
      { name: 'HBAR/SAUCE', color: colors.neonPurple, x: 50, y: 30, depth: 1.8, vx: 0.1, vy: 0.1 },
      { name: 'HBAR/USDC', color: colors.cyan, x: 75, y: 25, depth: 1.2, vx: -0.1, vy: 0.1 },
      { name: 'SAUCE/WHBAR', color: colors.neonGreen, x: 60, y: 70, depth: 2.2, vx: 0.1, vy: -0.1 },
      { name: 'HBAR/BSL', color: colors.neonYellow, x: 80, y: 60, depth: 0.8, vx: -0.1, vy: -0.1 }
    ];

    setSaucers(pools.map((p, i) => ({
      ...p,
      id: i,
      alive: true,
      phase: Math.random() * Math.PI * 2,
    })));
  }, []);

  // --- Chat Auto-Scroll ---
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatHistory]);

  const handleChatSubmit = (e) => {
    e.preventDefault();
    if (!chatInput.trim()) return;

    const userMsg = { role: 'user', text: chatInput };
    setChatHistory(prev => [...prev, userMsg]);
    setChatInput('');

    setTimeout(() => {
      let responseText = "COMMAND_ACKNOWLEDGED. TARGETING SYSTEMS ADJUSTED.";
      if (userMsg.text.toLowerCase().includes('kill')) responseText = "LETHAL FORCE AUTHORIZED. GOOD HUNTING.";
      if (userMsg.text.toLowerCase().includes('status')) responseText = "HELMET HUD: ONLINE. WEAPON SYSTEMS: GREEN.";
      
      setChatHistory(prev => [...prev, { role: 'ai', text: responseText }]);
    }, 600);
  };

  // --- Physics & Simulation Loop ---
  useEffect(() => {
    const interval = setInterval(() => {
      setFrame(f => (f + 1) % 2);

      // Bullet Physics
      setBullets(prev => prev.map(b => ({
        ...b,
        x: b.x + Math.cos(b.angle) * 3,
        y: b.y + Math.sin(b.angle) * 3,
        life: b.life - 1
      })).filter(b => b.life > 0));

      // Saucer Physics (Bounce & Float)
      setSaucers(prevSaucers => {
        let updated = prevSaucers.map(s => {
          if (!s.alive) return s;
          let nx = s.x + s.vx;
          let ny = s.y + s.vy;
          let nvx = s.vx;
          let nvy = s.vy;

          // Perimeter Defense: Bounce off x=25 to keep away from Mech
          if (nx < 25 || nx > 92) nvx *= -1;
          if (ny < 10 || ny > 90) nvy *= -1;

          return { ...s, x: nx, y: ny, vx: nvx, vy: nvy };
        });

        // Collision Avoidance (Bubble Physics)
        for (let i = 0; i < updated.length; i++) {
          for (let j = i + 1; j < updated.length; j++) {
            let s1 = updated[i];
            let s2 = updated[j];
            if (!s1.alive || !s2.alive) continue;

            const dx = s1.x - s2.x;
            const dy = s1.y - s2.y;
            const dist = Math.hypot(dx, dy);
            const minDist = (s1.depth + s2.depth) * 6;

            if (dist < minDist) {
              const angle = Math.atan2(dy, dx);
              const force = 0.05;
              updated[i].vx += Math.cos(angle) * force;
              updated[i].vy += Math.sin(angle) * force;
              updated[j].vx -= Math.cos(angle) * force;
              updated[j].vy -= Math.sin(angle) * force;
            }
          }
        }
        return updated;
      });

      // Agent AI (Stationary Turret Logic)
      setAgent(p => {
        // Find nearest living target
        let target = null;
        let minDist = Infinity;
        saucers.forEach((s) => {
          if (!s.alive) return;
          const d = Math.hypot(p.x - s.x, p.y - s.y);
          if (d < minDist) { minDist = d; target = s; }
        });

        if (!target) return { ...p, state: 'SCANNING', aim: 2 }; // Default straight

        // Calculate Angle
        const dx = target.x - p.x;
        const dy = target.y - p.y;
        const angle = Math.atan2(dy, dx) * (180 / Math.PI); // Degrees

        // Determine Aim Pose (0=Up45 ... 4=Down45)
        let aimIndex = 2; // Straight
        if (angle < -30) aimIndex = 0;      // Up 45
        else if (angle < -10) aimIndex = 1; // Up 20
        else if (angle < 10) aimIndex = 2;  // Straight
        else if (angle < 30) aimIndex = 3;  // Down 20
        else aimIndex = 4;                  // Down 45

        // Firing Logic
        if (minDist < 60 && p.state !== 'FIRING') {
          triggerTurretFire(p, target, aimIndex);
          return { ...p, state: 'FIRING', aim: aimIndex };
        }

        if (minDist < 5) {
          liquidatePool(target);
        }

        return { ...p, state: 'TRACKING', aim: aimIndex };
      });
    }, 50);
    return () => clearInterval(interval);
  }, [saucers]);

  const triggerTurretFire = (p, target, aimIndex) => {
    // Calculate spawn point based on current pose offset
    const offset = MUZZLE_OFFSETS[aimIndex];
    const spawnX = p.x + offset.x;
    const spawnY = p.y + offset.y;

    const angle = Math.atan2(target.y - spawnY, target.x - spawnX);
    
    setBullets(prev => [...prev, { x: spawnX, y: spawnY, angle, life: 25 }]);
    setTimeout(() => { setAgent(c => ({ ...c, state: 'TRACKING' })); }, 250);
  };

  const liquidatePool = (target) => {
    setSaucers(prev => prev.map(s => s.id === target.id ? { ...s, alive: false } : s));
    setStats(prev => ({ ...prev, swaps: prev.swaps + 1, volume: prev.volume + 5200 }));
    setLogs(prev => [{ id: Date.now(), text: `TARGET_${target.name} ELIMINATED.`, type: "success" }, ...prev].slice(0, 15));
    
    setTimeout(() => {
      setSaucers(prev => prev.map(s => s.id === target.id ? { 
        ...s, alive: true, x: Math.random() < 0.5 ? 85 : 90, y: Math.random() * 80 + 10,
        vx: (Math.random() - 0.5) * 0.2, vy: (Math.random() - 0.5) * 0.2
      } : s));
    }, 4000);
  };

  return (
    <div className="flex flex-col h-screen bg-[#010103] text-white font-mono overflow-hidden">
      
      {/* 1. Header */}
      <div className="h-14 border-b border-red-500/20 flex items-center px-6 justify-between bg-black/80 backdrop-blur-xl shrink-0 z-50">
        <div className="flex items-center gap-4">
          <div className="w-10 h-10 flex items-center justify-center border-2 border-red-500 rounded-full bg-red-950/30">
            <Target className="text-red-500" size={20} />
          </div>
          <div>
            <h1 className="text-sm font-black tracking-[0.4em] text-red-500 uppercase">Sentry-V2-Matrix</h1>
            <p className="text-[9px] text-zinc-500 font-bold uppercase tracking-widest">Mothership Extermination Protocol</p>
          </div>
        </div>
        <div className="flex items-center gap-2 px-3 py-1 bg-red-500/10 border border-red-500/20 rounded">
           <span className="text-[9px] font-black text-red-500 uppercase">LIVE_COMBAT</span>
        </div>
      </div>

      <div className="flex-1 flex overflow-hidden">
        
        {/* 2. Left Sidebar */}
        <aside className="w-72 border-r border-white/5 bg-[#030305] p-6 flex flex-col gap-8 shrink-0 z-20">
          <SectionHeader icon={<Skull size={14} className="text-red-500"/>} title="Target_Analysis" />
          <div className="space-y-4">
            <div className="w-full p-4 border rounded-xl flex flex-col items-center gap-3 transition-all bg-purple-500/10 border-purple-500 shadow-[0_0_20px_rgba(188,19,254,0.2)]">
              <span className="text-[10px] font-bold uppercase tracking-widest text-purple-400">Class-X: Mothership</span>
              <pre className="text-[8px] font-black leading-[1.1] text-purple-300">{ALIEN_MOTHERSHIP}</pre>
            </div>
          </div>
          <div className="flex-1 flex flex-col">
            <SectionHeader icon={<Terminal size={14} className="text-zinc-500"/>} title="Mission_Log" />
            <div className="flex-1 overflow-y-auto mt-4 space-y-2 pr-2 custom-scrollbar">
              {logs.map(log => (
                <div key={log.id} className="text-[9px] p-2 rounded bg-red-500/5 border-l-2 font-medium" style={{ borderColor: log.type === 'success' ? colors.neonGreen : log.type === 'warn' ? colors.neonYellow : colors.cyan }}>
                  <span style={{ color: log.type === 'success' ? colors.neonGreen : '#fff' }}>{log.text}</span>
                </div>
              ))}
            </div>
          </div>
        </aside>

        {/* 3. Main Content Area */}
        <main className="flex-1 relative bg-black flex flex-col min-w-0">
          
          {/* A. Battlefield Preview */}
          <div className="relative flex-[2] m-4 mb-0 border border-white/5 rounded-t-3xl bg-[#060608]/95 overflow-hidden shadow-2xl shrink-0 min-h-[300px]">
            {/* Background Effects */}
            <div className="absolute inset-0 opacity-[0.06] pointer-events-none">
              {[...Array(20)].map((_, i) => (
                <div key={i} className="absolute whitespace-nowrap animate-matrix-fall text-[8px] text-red-500" style={{ left: `${i * 5}%`, animationDelay: `${Math.random() * 10}s` }}>
                  {Array(60).fill(0).map(() => String.fromCharCode(0x30A0 + Math.random() * 96)).join('\n')}
                </div>
              ))}
            </div>

            <div className="absolute inset-0 p-12">
              
              {/* Bullets */}
              {bullets.map((b, i) => (
                <div key={i} className="absolute w-4 h-1 bg-red-500 blur-[1px] shadow-[0_0_15px_#ff0000]" style={{ left: `${b.x}%`, top: `${b.y}%`, transform: `translate(-50%, -50%) rotate(${b.angle * (180/Math.PI)}deg)` }} />
              ))}

              {/* Motherships */}
              {saucers.map(s => (
                <div key={s.id} className={`absolute transition-all duration-1000 ease-out ${s.alive ? 'opacity-100 scale-100' : 'opacity-0 scale-0'}`} style={{ left: `${s.x}%`, top: `${s.y}%`, color: s.color, zIndex: 20 }}>
                  <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 rounded-full transition-all duration-300" style={{ width: `${s.depth * 150}px`, height: `${s.depth * 150}px`, background: `radial-gradient(circle at 30% 30%, ${s.color}22, ${s.color}11, transparent)`, border: `1px solid ${s.color}33`, boxShadow: `0 0 20px ${s.color}22, inset 0 0 20px ${s.color}11`, backdropFilter: 'blur(2px)' }}>
                    <div className="absolute top-[15%] left-[15%] w-[20%] h-[10%] bg-white/10 rounded-full rotate-45 blur-[1px]" />
                  </div>
                  <pre className="relative text-[8px] leading-[1.1] font-black tracking-tighter filter drop-shadow-[0_0_12px_rgba(255,255,255,0.1)] z-30">{ALIEN_MOTHERSHIP}</pre>
                  
                  <div className="absolute -bottom-24 left-1/2 -translate-x-1/2 flex flex-col items-center z-30 pointer-events-none w-40 text-center">
                    <span className="text-xs font-black text-white drop-shadow-[0_2px_4px_rgba(0,0,0,0.8)] tracking-widest bg-black/40 px-2 rounded backdrop-blur-sm">
                      MOTHERSHIP: {s.name}
                    </span>
                    <span className="text-[10px] font-bold mt-1 px-1 bg-black/60 rounded" style={{ color: s.color }}>
                      LIQ_DEPTH: {s.depth}
                    </span>
                  </div>
                </div>
              ))}

              {/* STATIONARY HIGH-FIDELITY MECH HELMET */}
              <div 
                className="absolute transition-all duration-200 ease-out z-40" 
                style={{ 
                  left: `${agent.x}%`, 
                  top: `${agent.y}%`, 
                  transform: `translate(-50%, -50%)`
                }}
              >
                <pre className="text-[12px] leading-[0.8] font-black text-white filter drop-shadow-[0_0_15px_rgba(255,0,0,0.4)]">
                  {MECH_POSES[agent.aim]}
                </pre>
                
                {/* Mech Status Label */}
                <div className="absolute -bottom-10 left-1/2 -translate-x-1/2 whitespace-nowrap">
                  <span className={`text-[9px] font-bold px-2 py-0.5 rounded border border-red-500/40 bg-black/80 text-red-500 uppercase tracking-widest`}>
                    {agent.state}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* B. LLM Chat Interface */}
          <div className="flex-1 m-4 mt-0 border border-t-0 border-white/5 rounded-b-3xl bg-[#08080c] flex flex-col overflow-hidden relative shadow-lg">
            
            <div className="h-8 bg-zinc-900/50 border-b border-white/5 flex items-center px-4 justify-between">
              <span className="text-[9px] uppercase font-bold text-zinc-500 flex items-center gap-2">
                <MessageSquare size={10} className="text-cyan-500"/> Command Uplink // Shard 0.0.1
              </span>
              <span className="flex items-center gap-1 text-[8px] text-green-500">
                <div className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse"/> ONLINE
              </span>
            </div>

            <div className="flex-1 overflow-y-auto p-4 space-y-3 custom-scrollbar font-mono">
              {chatHistory.map((msg, i) => (
                <div key={i} className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                   {msg.role === 'ai' && <div className="w-6 h-6 rounded bg-red-900/20 border border-red-500/20 flex items-center justify-center shrink-0"><Terminal size={12} className="text-red-500"/></div>}
                   <div className={`max-w-[80%] p-2 rounded text-[10px] border ${msg.role === 'user' ? 'bg-cyan-950/20 border-cyan-500/20 text-cyan-100' : 'bg-zinc-900/50 border-white/5 text-zinc-300'}`}>
                     {msg.text}
                   </div>
                </div>
              ))}
              <div ref={chatEndRef} />
            </div>

            <form onSubmit={handleChatSubmit} className="h-10 border-t border-white/5 bg-black/50 p-1 flex gap-2">
              <div className="flex items-center pl-2 text-zinc-500"><ChevronRight size={14}/></div>
              <input 
                type="text" 
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                placeholder="Enter command execution parameters..."
                className="flex-1 bg-transparent border-none outline-none text-[11px] text-white font-mono placeholder-zinc-700"
              />
              <button type="submit" className="px-3 bg-red-600 hover:bg-red-500 text-white rounded-sm flex items-center justify-center transition-colors">
                <Send size={12} />
              </button>
            </form>

          </div>

        </main>
      </div>

      <style jsx>{`
        @keyframes matrix-fall {
          0% { transform: translateY(-100%); }
          100% { transform: translateY(1000%); }
        }
        .animate-matrix-fall {
          animation: matrix-fall 12s linear infinite;
        }
        .custom-scrollbar::-webkit-scrollbar { width: 4px; }
        .custom-scrollbar::-webkit-scrollbar-track { background: #000; }
        .custom-scrollbar::-webkit-scrollbar-thumb { background: #333; border-radius: 4px; }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover { background: #555; }
      `}</style>
    </div>
  );
};

const SectionHeader = ({ icon, title }) => (
  <h3 className="text-[10px] font-black text-zinc-500 uppercase tracking-[0.2em] flex items-center gap-2 border-b border-white/10 pb-2">
    {icon} {title}
  </h3>
);

export default App;