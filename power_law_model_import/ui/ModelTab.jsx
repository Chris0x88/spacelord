import React, { useState } from 'react';
import {
    Bot, Zap, RefreshCw, TrendingUp, TrendingDown, ZoomIn
} from 'lucide-react';
import { InfoButton } from './CommonUI';
import HistoricalChart from './HistoricalChart';
import FullHistoryModal from './FullHistoryModal';

const ModelTab = ({
    price,
    priceChangePercent,
    hederaWbtcPrice,
    signal,
    projections,
    botStatus,
    portfolioStatus,
    marketStatus,
    isAuthorized,
    togglingBot,
    toggleBot,
    triggerRebalance,
    rebalancing,
    fmtPrice,
    fmtDate,
    getPhase,
    getVal,
    getStance,
    getDailyQuote,
    getNextPhaseInfo,
    getNextHalving,
    getDaysSinceGenesis,
    getCycleDates,
    setActiveTab,
    getTokenMeta
}) => {
    const [showCycleInfo, setShowCycleInfo] = useState(true);
    const [expandedInfo, setExpandedInfo] = useState({});

    const toggleInfo = (key) => setExpandedInfo(prev => ({ ...prev, [key]: !prev[key] }));

    const ph = signal ? getPhase(signal.phase) : null;
    const val = signal ? getVal(signal.valuation) : null;
    const st = signal ? getStance(signal.stance) : null;
    const nextHalving = getNextHalving();
    const daysSinceGenesis = getDaysSinceGenesis();
    const nextPhaseInfo = getNextPhaseInfo();
    const cycleDates = getCycleDates();

    // Calculate dot position on the wave
    const getDotPosition = () => {
        if (!signal) return { x: 20, y: 80 };
        const progress = signal.cycle_progress_pct / 100;
        const x = 20 + (progress * 260);
        const peak = 0.33;
        const sigma = 0.2;
        const gaussian = Math.exp(-Math.pow(progress - peak, 2) / (2 * sigma * sigma));
        const y = 80 - (gaussian * 60);
        return { x, y };
    };
    const dotPos = getDotPosition();

    return (
        <>
            {/* Hero Price */}
            <section className="text-center py-8">
                <h1 className="text-6xl font-black tracking-tight text-white">{fmtPrice(price)}</h1>
                <div className={`flex items-center justify-center gap-1 mt-3 text-lg font-bold ${priceChangePercent >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {priceChangePercent >= 0 ? '↑' : '↓'} {Math.abs(priceChangePercent || 0).toFixed(2)}% today
                </div>
                <div className="flex items-center justify-center gap-3 mt-2">
                    <div className="text-[11px] text-gray-500 font-medium">
                        {getTokenMeta('WBTC').name} • <a href="https://www.binance.com/en/futures/funding-history/perpetual/trading-data" target="_blank" rel="noopener noreferrer" className="text-cyan-500/80 hover:text-cyan-400 underline decoration-cyan-500/20 underline-offset-2 transition-colors">Futures</a>
                    </div>
                    {hederaWbtcPrice && price && (
                        <div className={`text-[10px] font-medium px-2 py-0.5 rounded ${Math.abs((hederaWbtcPrice - price) / price * 100) > 1
                            ? 'bg-yellow-500/20 text-yellow-400'
                            : 'bg-gray-500/20 text-gray-400'
                            }`}>
                            Hedera: {fmtPrice(hederaWbtcPrice)}
                            <span className="ml-1">
                                ({((hederaWbtcPrice - price) / price * 100) >= 0 ? '+' : ''}
                                {((hederaWbtcPrice - price) / price * 100).toFixed(2)}%)
                            </span>
                        </div>
                    )}
                </div>
            </section>

            {/* Historical Chart */}
            <HistoricalChart currentPrice={price} />

            {/* Full History Buttons */}
            <div className="flex justify-center gap-3 mb-6">
                <FullHistoryModal
                    initialView="30yr"
                    buttonLabel="30yr View"
                    buttonColor="cyan"
                />
                <FullHistoryModal
                    initialView="20yr"
                    buttonLabel="20yr Zoom"
                    buttonColor="purple"
                    buttonIcon={ZoomIn}
                />
            </div>

            {/* Bot Card - Enhanced with HBAR gas tracking */}
            {botStatus && (
                <div
                    onClick={() => { setActiveTab('wallet'); window.scrollTo(0, 0); }}
                    className="cursor-pointer bg-gradient-to-br from-cyan-500/10 via-blue-500/5 to-purple-500/5 backdrop-blur-sm rounded-2xl border border-cyan-500/20 p-5 mb-4 hover:border-cyan-500/40 transition-all shadow-lg shadow-cyan-500/5"
                >
                    <div className="flex items-center justify-between mb-4">
                        <div className="flex items-center gap-3">
                            <div className={`relative w-12 h-12 rounded-xl flex items-center justify-center ${botStatus?.bot_running ? 'bg-cyan-500/20' : 'bg-white/5'}`}>
                                <Bot size={24} className={botStatus?.bot_running ? 'text-cyan-400' : 'text-gray-500'} />
                                {botStatus?.bot_running && (
                                    <div className="absolute -top-1 -right-1 w-3 h-3 bg-emerald-500 rounded-full ring-2 ring-black animate-pulse" />
                                )}
                            </div>
                            <div>
                                <div className="font-bold text-white">Heartbeat Bot</div>
                                <div className="text-xs text-gray-500">{botStatus.trades_executed || 0} trades executed</div>
                            </div>
                        </div>
                        <div className="flex items-center gap-2">
                            <div className={`px-3 py-1.5 rounded-full text-[10px] font-bold ${botStatus?.bot_running ? 'bg-emerald-500/20 text-emerald-400 ring-1 ring-emerald-500/30' : 'bg-gray-800 text-gray-500'}`}>
                                {botStatus?.bot_running ? 'ACTIVE' : 'PAUSED'}
                            </div>
                            {isAuthorized && (
                                <button
                                    onClick={(e) => { e.stopPropagation(); toggleBot(); }}
                                    disabled={togglingBot}
                                    className={`p-2 rounded-lg transition-all ${botStatus?.bot_running
                                        ? 'bg-red-500/10 text-red-400 hover:bg-red-500/20 border border-red-500/30'
                                        : 'bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20 border border-emerald-500/30'
                                        }`}
                                    title={botStatus?.bot_running ? "Pause Bot" : "Start Bot"}
                                >
                                    {togglingBot ? <RefreshCw size={14} className="animate-spin" /> : <Zap size={14} />}
                                </button>
                            )}
                        </div>
                    </div>

                    {/* Portfolio Summary */}
                    <div className="grid grid-cols-3 gap-3 text-center mb-4">
                        <div className="bg-black/20 rounded-xl p-3">
                            <div className="text-[10px] text-gray-500 uppercase mb-1">Portfolio</div>
                            <div className="text-lg font-bold text-white">{fmtPrice(portfolioStatus?.total_value_usdc || 0, 0)}</div>
                        </div>
                        <div className="bg-black/20 rounded-xl p-3">
                            <div className="text-[10px] text-gray-500 uppercase mb-1">BTC</div>
                            <div className="text-lg font-bold text-orange-400">{(portfolioStatus?.current_btc_pct || 0).toFixed(0)}%</div>
                        </div>
                        <div className="bg-black/20 rounded-xl p-3">
                            <div className="text-[10px] text-gray-500 uppercase mb-1">Target</div>
                            <div className="text-lg font-bold text-cyan-400">{(marketStatus?.target_btc_pct || 0).toFixed(0)}%</div>
                        </div>
                    </div>

                    {/* HBAR Gas Status */}
                    <div className="bg-black/30 rounded-xl p-3">
                        <div className="flex items-center justify-between mb-2">
                            <div className="flex items-center gap-2">
                                <Zap size={14} className={(portfolioStatus?.hbar_balance || 0) > 5 ? 'text-emerald-400' : (portfolioStatus?.hbar_balance || 0) > 1 ? 'text-yellow-400' : 'text-red-400'} />
                                <span className="text-xs text-gray-400">Gas Balance</span>
                            </div>
                            <span className={`text-sm font-bold ${(portfolioStatus?.hbar_balance || 0) > 5 ? 'text-emerald-400' : (portfolioStatus?.hbar_balance || 0) > 1 ? 'text-yellow-400' : 'text-red-400'}`}>
                                {(portfolioStatus?.hbar_balance || 0).toFixed(2)} HBAR
                            </span>
                        </div>
                        <div className="flex items-center justify-between text-[10px]">
                            <span className="text-gray-600">Est. trades remaining</span>
                            <span className={`font-medium ${(botStatus?.hbar_trades_remaining || 0) > 10 ? 'text-gray-400' : (botStatus?.hbar_trades_remaining || 0) > 3 ? 'text-yellow-400' : 'text-red-400'}`}>
                                ~{botStatus?.hbar_trades_remaining || 0} trades
                            </span>
                        </div>
                        {(portfolioStatus?.hbar_balance || 0) < 2 && (
                            <div className="mt-2 text-[10px] text-amber-400 bg-amber-500/10 rounded px-2 py-1">
                                ⚠️ Low gas - top up HBAR to continue trading
                            </div>
                        )}
                    </div>

                    {/* Tap hint */}
                    <div className="text-center mt-3 text-[10px] text-gray-600">
                        Tap to view Wallet →
                    </div>
                </div>
            )}

            {/* Model Allocation Card */}
            {signal && (
                <div className="bg-gradient-to-br from-gray-900/60 to-gray-900/20 backdrop-blur-sm rounded-2xl border border-cyan-500/20 p-6 mb-4 shadow-[0_0_30px_rgba(6,182,212,0.1)]">
                    <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center">
                            <h2 className="text-xs font-bold text-gray-400 uppercase tracking-wider">Model Allocation</h2>
                            <InfoButton infoKey="allocation" expanded={expandedInfo} onToggle={toggleInfo}>
                                <p className="font-semibold text-white mb-2">What is Model Allocation?</p>
                                <p className="mb-2">The model's target BTC allocation based on current price relative to the power-law floor and cycle ceiling.</p>
                                <p className="mb-2"><span className="text-green-400">0-30%</span> = Near ceiling, defensive<br />
                                    <span className="text-yellow-400">30-60%</span> = Mid-band zone<br />
                                    <span className="text-cyan-400">60-100%</span> = Near floor, aggressive</p>
                                <p className="text-gray-500 text-[10px]">V3 uses 15% rebalance threshold.</p>
                            </InfoButton>
                        </div>
                        <span className="text-[10px] text-gray-600">Range: 0-100%</span>
                    </div>
                    <div className="flex items-center gap-4 mb-5">
                        <span className="text-6xl font-black text-cyan-400">{signal.allocation_pct.toFixed(0)}%</span>
                        <div className="flex flex-col">
                            <span className={`text-2xl font-bold ${st.color}`}>{st.label}</span>
                            <span className="text-sm text-gray-400 mt-1">{st.desc || 'Model Bitcoin exposure'}</span>
                        </div>
                    </div>
                    {/* Allocation bar visualization */}
                    <div className="relative">
                        <div className="h-3 bg-gradient-to-r from-blue-900/60 to-cyan-400/80 rounded-full" />
                        <div className="relative h-3 -mt-3">
                            <div
                                className="absolute w-4 h-4 bg-cyan-400 rounded-full border-2 border-white transform -translate-y-0.5 transition-all duration-300"
                                style={{ left: `${Math.min(signal.allocation_pct, 100)}%`, marginLeft: '-8px' }}
                            />
                        </div>
                        <div className="flex justify-between text-[10px] text-gray-400 mt-2">
                            <span>0% Defensive</span>
                            <span>50% Balanced</span>
                            <span>100% Aggressive</span>
                        </div>
                    </div>
                </div>
            )}

            {/* Cycle Position Card */}
            {signal && (
                <div className="bg-gradient-to-br from-gray-900/60 to-gray-900/20 backdrop-blur-sm rounded-2xl border border-cyan-500/20 p-6 mb-4 shadow-[0_0_30px_rgba(6,182,212,0.1)]">
                    <div className="flex justify-between items-start mb-4">
                        <div className="flex items-center">
                            <h2 className="text-xs font-bold text-gray-400 uppercase tracking-wider">Price Position</h2>
                            <InfoButton infoKey="pricePos" expanded={expandedInfo} onToggle={toggleInfo}>
                                <p className="font-semibold text-white mb-2">Price Position</p>
                                <p className="mb-2">Shows where BTC trades between the power-law floor (0%) and cycle ceiling (100%).</p>
                                <p className="mb-2"><span className="text-green-400">0-20%</span>: Deep value (accumulation zone)<br />
                                    <span className="text-yellow-400">20-50%</span>: Mid-band range<br />
                                    <span className="text-orange-400">50-80%</span>: Elevated (caution)<br />
                                    <span className="text-red-400">80-100%</span>: Near ceiling (distribution)</p>
                                <p className="text-gray-500 text-[10px]">Historically, BTC trades near floor ~76% of time.</p>
                            </InfoButton>
                        </div>
                        <button
                            onClick={() => setShowCycleInfo(!showCycleInfo)}
                            className="text-[10px] text-cyan-400 hover:text-cyan-300"
                        >
                            {showCycleInfo ? 'Hide cycle' : 'Show cycle'}
                        </button>
                    </div>

                    {/* Clear text description instead of confusing % */}
                    <div className="mb-4">
                        <div className="flex items-baseline gap-2">
                            <span className={`text-2xl font-bold ${val.color}`}>{val.label}</span>
                            <span className="text-sm text-gray-500">({signal.position_in_band_pct.toFixed(0)}% of range)</span>
                        </div>
                        <p className="text-sm text-gray-400 mt-1">
                            {signal.position_in_band_pct < 20 && 'Near historical accumulation zone — strong buy signal'}
                            {signal.position_in_band_pct >= 20 && signal.position_in_band_pct < 50 && 'Moderate premium to floor — mid-band territory'}
                            {signal.position_in_band_pct >= 50 && signal.position_in_band_pct < 80 && 'Elevated pricing — approaching ceiling, reduce exposure'}
                            {signal.position_in_band_pct >= 80 && 'Near cycle ceiling — maximum caution, protect capital'}
                        </p>
                        {/* Visual position bar */}
                        <div className="mt-3">
                            <div className="h-3 bg-gradient-to-r from-blue-900/60 via-blue-600/70 to-cyan-400/80 rounded-full" />
                            <div className="relative h-3 -mt-3">
                                <div
                                    className="absolute w-4 h-4 bg-cyan-400 rounded-full border-2 border-white shadow-lg transform -translate-y-0.5 transition-all duration-300"
                                    style={{ left: `${Math.min(signal.position_in_band_pct, 100)}%`, marginLeft: '-8px' }}
                                />
                            </div>
                            <div className="flex justify-between text-[9px] text-gray-400 mt-2">
                                <span>Floor ({fmtPrice(signal.floor, 0)})</span>
                                <span>Ceiling ({fmtPrice(signal.ceiling, 0)})</span>
                            </div>
                        </div>
                    </div>

                    {/* Smooth Wave Chart - toggleable */}
                    {showCycleInfo && (
                        <>
                            <div className="relative mt-4 mb-2" style={{ height: '100px' }}>
                                <svg viewBox="0 0 300 100" className="w-full h-full" preserveAspectRatio="none">
                                    {/* Gradient definition */}
                                    <defs>
                                        <linearGradient id="waveGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                                            <stop offset="0%" stopColor="#06b6d4" stopOpacity="0.3" />
                                            <stop offset="50%" stopColor="#06b6d4" stopOpacity="1" />
                                            <stop offset="100%" stopColor="#06b6d4" stopOpacity="0.3" />
                                        </linearGradient>
                                        <linearGradient id="waveFill" x1="0%" y1="0%" x2="0%" y2="100%">
                                            <stop offset="0%" stopColor="#06b6d4" stopOpacity="0.2" />
                                            <stop offset="100%" stopColor="#06b6d4" stopOpacity="0" />
                                        </linearGradient>
                                    </defs>
                                    {/* Filled area under curve - peak at 33% (x=106) not 50% */}
                                    <path
                                        d="M 20,80 C 50,80 80,30 106,20 C 140,30 180,70 220,78 C 250,82 265,82 280,82 L 280,100 L 20,100 Z"
                                        fill="url(#waveFill)"
                                    />
                                    {/* Main curve - peak at 33% into cycle */}
                                    <path
                                        d="M 20,80 C 50,80 80,30 106,20 C 140,30 180,70 220,78 C 250,82 265,82 280,82"
                                        fill="none"
                                        stroke="url(#waveGradient)"
                                        strokeWidth="3"
                                        strokeLinecap="round"
                                    />
                                    {/* Static dots at key points */}
                                    <circle cx="20" cy="80" r="4" fill="#06b6d4" opacity="0.5" />
                                    <circle cx="106" cy="20" r="4" fill="#6b7280" />
                                    <circle cx="280" cy="82" r="4" fill="#06b6d4" opacity="0.5" />
                                    {/* Current position dot */}
                                    <circle
                                        cx={dotPos.x}
                                        cy={dotPos.y}
                                        r="8"
                                        fill="#06b6d4"
                                        className="drop-shadow-[0_0_12px_rgba(6,182,212,0.8)]"
                                    />
                                    <circle cx={dotPos.x} cy={dotPos.y} r="4" fill="white" />
                                </svg>
                                {/* Labels with dates (slightly offset from points) */}
                                <div className="absolute text-[9px] text-gray-500" style={{ bottom: '4px', left: '0' }}>
                                    <div className="text-gray-400">Halving</div>
                                    <div>{fmtDate(cycleDates.start)}</div>
                                </div>
                                <div className="absolute text-[9px] text-gray-500 text-center" style={{ top: '-14px', left: '33%', transform: 'translateX(-50%)' }}>
                                    <div className="text-amber-400">Peak</div>
                                    <div>{fmtDate(cycleDates.peak)}</div>
                                </div>
                                <div className="absolute text-[9px] text-gray-500 text-right" style={{ bottom: '4px', right: '0' }}>
                                    <div className="text-gray-400">Next Halving</div>
                                    <div>{fmtDate(cycleDates.end)}</div>
                                </div>
                            </div>

                            <div className="text-center text-sm text-gray-400">
                                {signal.cycle_progress_pct < 25 ? 'Early cycle — building momentum' :
                                    signal.cycle_progress_pct < 40 ? 'Approaching peak zone — stay sharp' :
                                        signal.cycle_progress_pct < 50 ? 'Peak zone — maximum caution' :
                                            signal.cycle_progress_pct < 70 ? 'Post-peak — distribution phase' :
                                                'Late cycle — accumulation ahead'}
                            </div>
                            <div className="text-center text-xs text-gray-600 mt-1">
                                {signal.cycle_progress_pct.toFixed(0)}% through Cycle {signal.cycle}
                            </div>
                        </>
                    )}
                </div>
            )}

            {/* Data Grid */}
            {signal && (
                <div className="grid grid-cols-2 gap-3 mb-4">
                    <div className="bg-gradient-to-br from-gray-900/60 to-gray-900/20 backdrop-blur-sm rounded-xl border border-green-500/30 p-3 shadow-[0_0_20px_rgba(16,185,129,0.1)] hover:border-green-500/50 transition-all">
                        <div className="flex items-start justify-between gap-1">
                            <span className="flex-1 min-w-0 text-[10px] text-gray-400 uppercase tracking-wide font-bold leading-tight">Floor</span>
                            <InfoButton infoKey="floor" expanded={expandedInfo} onToggle={toggleInfo}>
                                <p className="font-semibold text-white mb-2">Power Law Floor</p>
                                <p className="mb-2">The theoretical minimum price based on Bitcoin's network growth. Calculated as:</p>
                                <p className="font-mono text-cyan-400 mb-2">10^-17 × days^5.73</p>
                                <p>Price has never stayed below this floor for long. When price touches floor = maximum buying opportunity.</p>
                            </InfoButton>
                        </div>
                        <div className="text-xl font-bold text-green-400 mt-1">{fmtPrice(signal.floor)}</div>
                        <span className="text-[11px] text-gray-600">At floor = 100% BTC</span>
                    </div>
                    <div className="bg-gradient-to-br from-gray-900/60 to-gray-900/20 backdrop-blur-sm rounded-xl border border-red-500/30 p-3 shadow-[0_0_20px_rgba(239,68,68,0.1)] hover:border-red-500/50 transition-all">
                        <div className="flex items-start justify-between gap-1">
                            <span className="flex-1 min-w-0 text-[10px] text-gray-400 uppercase tracking-wide font-bold leading-tight">Ceiling</span>
                            <InfoButton infoKey="ceiling" expanded={expandedInfo} onToggle={toggleInfo}>
                                <p className="font-semibold text-white mb-2">Cycle Ceiling</p>
                                <p className="mb-2">The estimated peak price for this halving cycle. Calculated using Kleiber's Law (biological scaling).</p>
                                <p className="mb-2">Each cycle, the ceiling-to-floor ratio decreases as Bitcoin matures.</p>
                                <p>When price approaches ceiling = maximum selling opportunity.</p>
                            </InfoButton>
                        </div>
                        <div className="text-xl font-bold text-red-400 mt-1">{fmtPrice(signal.ceiling)}</div>
                        <span className="text-[11px] text-gray-600">At ceiling = 0% BTC</span>
                    </div>
                    <div className="bg-gradient-to-br from-gray-900/60 to-gray-900/20 backdrop-blur-sm rounded-xl border border-cyan-500/30 p-3 shadow-[0_0_20px_rgba(6,182,212,0.1)] hover:border-cyan-500/50 transition-all">
                        <div className="flex items-start justify-between gap-1">
                            <span className="flex-1 min-w-0 text-[10px] text-gray-400 uppercase tracking-wide font-bold leading-tight">Fair Value</span>
                            <InfoButton infoKey="fairvalue" expanded={expandedInfo} onToggle={toggleInfo}>
                                <p className="font-semibold text-white mb-2">Model Fair Value</p>
                                <p className="mb-2">The "heartbeat" price — where the model expects BTC to trade based on cycle timing.</p>
                                <p className="mb-2">Peaks at 33% into cycle (~16 months post-halving), then declines.</p>
                                <p>Current price vs fair value indicates over/undervaluation.</p>
                            </InfoButton>
                        </div>
                        <div className="text-xl font-bold text-cyan-400 mt-1">{fmtPrice(signal.model_price)}</div>
                        <div className="text-[11px] text-gray-600">
                            {price > signal.model_price
                                ? <span className="text-orange-400">+{((price / signal.model_price - 1) * 100).toFixed(0)}% above fair value</span>
                                : <span className="text-green-400">{((price / signal.model_price - 1) * 100).toFixed(0)}% below fair value</span>
                            }
                        </div>
                    </div>
                    <div className="bg-gradient-to-br from-gray-900/60 to-gray-900/20 backdrop-blur-sm rounded-xl border border-amber-500/30 p-3 shadow-[0_0_20px_rgba(251,191,36,0.1)] hover:border-amber-500/50 transition-all">
                        <div className="flex items-start justify-between gap-1">
                            <span className="flex-1 min-w-0 text-[10px] text-gray-400 uppercase tracking-wide font-bold leading-tight">Peak Date</span>
                            <InfoButton infoKey="peakdate" expanded={expandedInfo} onToggle={toggleInfo}>
                                <p className="font-semibold text-white mb-2">Expected Cycle Peak</p>
                                <p className="mb-2">Based on the Gaussian heartbeat model, the cycle peak typically occurs at 33% into the halving cycle.</p>
                                <p className="mb-2">Historical peaks: Dec 2013, Dec 2017, Nov 2021.</p>
                                <p>This is an estimate — actual peak timing varies ±3 months.</p>
                            </InfoButton>
                        </div>
                        <div className="text-xl font-bold text-amber-400 mt-1">{fmtDate(cycleDates.peak)}</div>
                        <span className="text-[11px] text-gray-600">
                            {cycleDates.peak > new Date()
                                ? `${Math.ceil((cycleDates.peak - new Date()) / (1000 * 60 * 60 * 24))} days away`
                                : 'Peak zone passed'
                            }
                        </span>
                    </div>
                </div>
            )}

            {/* Model Projections Table - "What's Coming" */}
            {projections && (
                <div className="bg-gradient-to-br from-white/[0.06] to-transparent rounded-xl border border-white/10 p-4 mb-4">
                    <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center">
                            <span className="text-[11px] text-gray-500 uppercase tracking-wide">Model Outlook</span>
                            <InfoButton infoKey="outlook" expanded={expandedInfo} onToggle={toggleInfo}>
                                <p className="font-semibold text-white mb-2">Model Outlook</p>
                                <p className="mb-2">Shows how the model would view TODAY'S PRICE at future dates.</p>
                                <p className="mb-2"><span className="text-green-400">Floor</span>: Power-law minimum (grows ~40%/yr)<br />
                                    <span className="text-cyan-400">Fair Value</span>: Heartbeat model price<br />
                                    <span className="text-purple-400">Alloc%</span>: Model allocation at that date</p>
                                <p className="text-gray-500 text-[10px]">As time passes, today's price becomes relatively cheaper vs the rising floor.</p>
                            </InfoButton>
                        </div>
                        <span className="text-[10px] text-gray-600">If price stays at {fmtPrice(price)}</span>
                    </div>
                    <table className="w-full text-[11px]">
                        <thead>
                            <tr className="text-gray-500">
                                <th className="text-left font-medium py-1">Period</th>
                                <th className="text-right font-medium py-1">Floor</th>
                                <th className="text-right font-medium py-1">Fair Value</th>
                                <th className="text-right font-medium py-1">Alloc%</th>
                            </tr>
                        </thead>
                        <tbody>
                            {projections.projections.map((p, idx) => (
                                <tr key={p.period} className={`border-t border-white/5 ${idx >= 4 ? 'opacity-70' : ''}`}>
                                    <td className="py-1.5 text-gray-400 font-medium">
                                        {p.period}
                                        <span className="text-[9px] text-gray-600 ml-1">({p.days_out}d)</span>
                                    </td>
                                    <td className="py-1.5 text-right text-green-400">{fmtPrice(p.floor)}</td>
                                    <td className="py-1.5 text-right text-cyan-400">{fmtPrice(p.model_price)}</td>
                                    <td className="py-1.5 text-right">
                                        <span className={`${p.allocation_pct >= 60 ? 'text-green-400' : p.allocation_pct >= 30 ? 'text-yellow-400' : 'text-red-400'}`}>
                                            {p.allocation_pct}%
                                        </span>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                    <div className="text-[9px] text-gray-600 mt-2 text-center">
                        Allocation assumes current price held constant • Floor grows ~40%/year
                    </div>
                </div>
            )}

            {/* Phase Status Card - prioritize next phase info */}
            {signal && ph && (
                <div className="bg-gradient-to-br from-white/[0.08] to-white/[0.02] backdrop-blur-sm rounded-2xl border border-white/10 p-5 mb-4">
                    <div className="flex items-center gap-4 mb-3">
                        <div className="w-12 h-12 rounded-xl bg-cyan-500/10 flex items-center justify-center">
                            <span className="text-2xl">⚡</span>
                        </div>
                        <div>
                            <h3 className="font-bold text-lg">{ph.label}</h3>
                            <div className="text-sm text-gray-500">Cycle {signal.cycle} • Day {daysSinceGenesis.toLocaleString()}</div>
                        </div>
                    </div>

                    {/* Next Phase - THE KEY INFO */}
                    {nextPhaseInfo && (
                        <div className={`rounded-xl p-4 mb-3 ${nextPhaseInfo.nextPhase === 'Bear Market' ? 'bg-red-500/10 border border-red-500/20' :
                            nextPhaseInfo.nextPhase === 'Peak Zone' ? 'bg-amber-500/10 border border-amber-500/20' :
                                'bg-cyan-500/10 border border-cyan-500/20'
                            }`}>
                            <div className="flex justify-between items-center mb-3">
                                <div>
                                    <div className="text-[10px] text-gray-400 uppercase">Next Phase</div>
                                    <div className={`text-lg font-bold ${nextPhaseInfo.nextPhase === 'Bear Market' ? 'text-red-400' :
                                        nextPhaseInfo.nextPhase === 'Peak Zone' ? 'text-amber-400' :
                                            'text-cyan-400'
                                        }`}>{nextPhaseInfo.nextPhase}</div>
                                </div>
                                <div className="text-right">
                                    <div className={`text-2xl font-bold ${nextPhaseInfo.nextPhase === 'Bear Market' ? 'text-red-400' :
                                        nextPhaseInfo.nextPhase === 'Peak Zone' ? 'text-amber-400' :
                                            'text-white'
                                        }`}>{nextPhaseInfo.days}</div>
                                    <div className="text-[10px] text-gray-500">days</div>
                                </div>
                            </div>
                            {/* Projected floor at next phase */}
                            <div className="pt-2 border-t border-white/10 grid grid-cols-2 gap-2 text-xs">
                                <div>
                                    <div className="text-gray-500">Floor at phase start</div>
                                    <div className="text-green-400 font-semibold">{fmtPrice(nextPhaseInfo.futureFloor, 0)}</div>
                                </div>
                                <div className="text-right">
                                    <div className="text-gray-500">Floor growth rate</div>
                                    <div className="text-cyan-400 font-semibold">+{nextPhaseInfo.annualizedGrowth.toFixed(0)}%/yr</div>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Secondary info - halving date smaller */}
                    <div className="flex justify-between text-xs text-gray-500 pt-2 border-t border-white/5">
                        <span>Next halving: {fmtDate(nextHalving?.date)}</span>
                        <span>{nextHalving?.days} days</span>
                    </div>
                </div>
            )}

            {/* Daily Quote */}
            {signal && (
                <div className="bg-gradient-to-br from-purple-500/10 to-transparent rounded-2xl border border-purple-500/20 p-5">
                    <p className="text-sm text-purple-200/80 text-center italic leading-relaxed">
                        {getDailyQuote(signal.allocation_pct)}
                    </p>
                </div>
            )}
        </>
    );
};

export default ModelTab;
