import React, { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import { ComposedChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine, ReferenceArea, Customized } from 'recharts';
import { RotateCcw, Lock } from 'lucide-react';

// ============================================================================
// MODEL CONSTANTS - Exact match to heartbeat_model.py
// ----------------------------------------------------------------------------
// CRITICAL: THIS MODEL IS LOCKED. 
// NO CHANGES TO CONSTANTS OR LOGIC WITHOUT EXPLICIT USER APPROVAL.
// ============================================================================
const GENESIS = new Date('2009-01-03');
const HALVINGS = [
    new Date('2012-11-28'),
    new Date('2016-07-09'),
    new Date('2020-05-11'),
    new Date('2024-04-20'),
];
const DAYS_PER_CYCLE = 1461;

// Power-law floor constants
const FLOOR_A = -17.0;
const FLOOR_B = 5.73;

// Spike envelope constants
const SPIKE_A = 40.0;
const KLEIBER = 0.75;
const HALVING_BASE = 0.5;

// ============================================================================
// MODEL FUNCTIONS - Exact replication of heartbeat_model.py
// ============================================================================

function daysSinceGenesis(date) {
    return Math.max(1, Math.floor((date - GENESIS) / (1000 * 60 * 60 * 24)));
}

function floorPrice(date) {
    const d = daysSinceGenesis(date);
    return Math.pow(10, FLOOR_A + FLOOR_B * Math.log10(d));
}

function getHalvingDate(n) {
    if (n < 1) return GENESIS;
    if (n <= HALVINGS.length) return HALVINGS[n - 1];
    const lastKnown = HALVINGS[HALVINGS.length - 1];
    const cyclesAhead = n - HALVINGS.length;
    return new Date(lastKnown.getTime() + cyclesAhead * DAYS_PER_CYCLE * 24 * 60 * 60 * 1000);
}

function cycleIndex(date) {
    for (let i = 0; i < HALVINGS.length; i++) {
        if (date < HALVINGS[i]) return i + 1;
    }
    const lastHalving = HALVINGS[HALVINGS.length - 1];
    const daysSinceLast = (date - lastHalving) / (1000 * 60 * 60 * 24);
    return HALVINGS.length + 1 + Math.floor(daysSinceLast / DAYS_PER_CYCLE);
}

function cycleBounds(c) {
    if (c === 1) return [GENESIS, HALVINGS[0]];
    const start = getHalvingDate(c - 1);
    const end = getHalvingDate(c);
    return [start, end];
}

function cycleProgress(date) {
    const c = cycleIndex(date);
    const [start, end] = cycleBounds(c);
    const total = (end - start) / (1000 * 60 * 60 * 24);
    const elapsed = (date - start) / (1000 * 60 * 60 * 24);
    if (total <= 0) return 0;
    return Math.max(0, Math.min(1, elapsed / total));
}

function spikeMax(c) {
    const kleiber_term = Math.pow(c, -KLEIBER);
    const halving_term = Math.pow(HALVING_BASE, c - 2);
    return 1 + SPIKE_A * kleiber_term * halving_term;
}

function ceilingPrice(date) {
    /** 
     * Elegant continuous ceiling that intersects the speculative peaks (at 33% progress).
     * Peak-centered effective cycle index ensures smooth decay without piecewise bumps.
     * Synchronized with heartbeat_model.py (Jan 2026 - Peak-Intersecting Envelope).
     */
    const c = cycleIndex(date);
    const p = cycleProgress(date);

    // Peak-centered effective cycle index: 
    // C_peak is exactly an integer (e.g., 4.0, 5.0) when p=0.33
    const c_peak = c + (p - 0.33);

    return floorPrice(date) * spikeMax(c_peak);
}

function heartbeatPulse(progress, cycle = 5) {
    /** 
     * Asymmetric 'Up the Escalator, Down the Elevator' Pulse.
     * Synchronized with heartbeat_model.py (Jan 2026).
     * 
     * progress: 0.0 to 1.0 within halving cycle.
     * cycle: used for maturity scaling (crashes become slightly wider).
     */
    const peak = 0.33;
    const w_up = 0.18;
    const w_down = 0.08 + (cycle * 0.01);

    let val;
    if (progress < peak) {
        val = Math.exp(-Math.pow(progress - peak, 2) / (2 * w_up * w_up));
    } else {
        val = Math.exp(-Math.pow(progress - peak, 2) / (2 * w_down * w_down));
    }

    // Boundary Pinning: Ensure pulse hits exactly 0 at boundaries
    const v0 = Math.exp(-Math.pow(-peak, 2) / (2 * w_up * w_up));
    const v1 = Math.exp(-Math.pow(1 - peak, 2) / (2 * w_down * w_down));
    const offset = (v0 * (1 - progress) + v1 * progress);

    return Math.max(0, val - offset);
}

function modelPrice(date) {
    const fl = floorPrice(date);
    const ceil = ceilingPrice(date);
    const p = cycleProgress(date);
    const c = cycleIndex(date);
    const hb = heartbeatPulse(p, c);
    return fl + (ceil - fl) * hb;
}

function positionScore(date, price) {
    const fl = floorPrice(date);
    const ceil = ceilingPrice(date);
    if (price <= fl) return 0;
    if (price >= ceil) return 1;
    return (price - fl) / (ceil - fl);
}

function shiftedHeartbeat(date, shiftDays = 90) {
    const futureDate = new Date(date.getTime() + shiftDays * 24 * 60 * 60 * 1000);
    const p = cycleProgress(futureDate);
    const c = cycleIndex(futureDate);
    return heartbeatPulse(p, c);
}

/**
 * ALLOCATION SIGNAL - V3.2 (Natively Continuous + Skewed Elevator)
 */
function allocationSignal(date, price, shiftDays = 90) {
    const pos = positionScore(date, price);
    const prog = cycleProgress(date);
    const c = cycleIndex(date);

    // 1. VALUE COMPONENT: Sigmoid on position (Kelly-style)
    const z_equiv = (pos - 0.5) * 4;
    const value_alloc = 1.0 / (1.0 + Math.exp(z_equiv * 2.0));

    // 2. CYCLE PHASE PENALTY: Post-peak caution
    let phase_penalty = 0;
    if (prog >= 0.35 && prog <= 0.85) {
        if (prog <= 0.55) {
            phase_penalty = ((prog - 0.35) / 0.20) * 0.50;
        } else if (prog <= 0.70) {
            phase_penalty = 0.50;
        } else {
            phase_penalty = ((0.85 - prog) / 0.15) * 0.50;
        }
    }

    // 3. MOMENTUM COMPONENT: Heartbeat direction
    const hb_now = heartbeatPulse(prog, c);
    const hb_future = shiftedHeartbeat(date, shiftDays);
    let momentum_delta = (hb_future - hb_now) * 0.3;
    momentum_delta = Math.max(-0.10, Math.min(0.10, momentum_delta));

    // 4. COMBINE
    let raw_alloc = value_alloc - phase_penalty + momentum_delta;

    // 5. V3 FLOOR BOOST
    const FLOOR_BOOST = 0.30;
    const DEEP_VALUE_THRESHOLD = 0.15;
    const VALUE_THRESHOLD = 0.30;
    const boost_scale = Math.max(0, 1 - phase_penalty * 2);

    if (pos < DEEP_VALUE_THRESHOLD) {
        const boost_factor = (DEEP_VALUE_THRESHOLD - pos) / DEEP_VALUE_THRESHOLD;
        raw_alloc = Math.min(1.0, raw_alloc + FLOOR_BOOST * boost_factor * boost_scale);
    } else if (pos < VALUE_THRESHOLD) {
        const boost_factor = (VALUE_THRESHOLD - pos) / (VALUE_THRESHOLD - DEEP_VALUE_THRESHOLD);
        raw_alloc = Math.min(1.0, raw_alloc + FLOOR_BOOST * 0.5 * boost_factor * boost_scale);
    }

    return Math.max(0, Math.min(1, raw_alloc)) * 100;
}

// ============================================================================
// MOMENTUM RIBBON - Miniature SMA100 momentum band (small top chart)
// ============================================================================
const MomentumRibbon = ({ data, xScale, chartOffset }) => {
    if (!data || data.length === 0 || !xScale || !chartOffset) return null;

    const trackHeight = 24;
    const trackY = chartOffset.top - 45; // Reserve a band above the main plot
    const centerY = trackY + (trackHeight / 2);

    // Filter for valid historical points only
    const validPoints = data.filter(d => d.sma100 && !d.isFuture && d.price !== null);
    if (validPoints.length === 0) return null;

    // Split into segments to handle bullish/bearish color changes
    const segments = [];
    let currentSegment = [];

    validPoints.forEach((d) => {
        const x = xScale(d.timestamp);
        const delta = (d.price - d.sma100) / d.sma100;
        const sensitivity = 5;
        const yOffset = Math.max(-1, Math.min(1, delta * sensitivity)) * (trackHeight / 2);
        const y = centerY - yOffset;
        const isBullish = d.price > d.sma100;

        if (currentSegment.length === 0 || currentSegment[0].isBullish === isBullish) {
            currentSegment.push({ x, y, isBullish });
        } else {
            segments.push(currentSegment);
            currentSegment = [{ x, y, isBullish }];
        }
    });
    if (currentSegment.length > 0) segments.push(currentSegment);

    return (
        <g style={{ pointerEvents: 'none' }}>
            {/* Background track */}
            <rect
                x={chartOffset.left}
                y={trackY}
                width={chartOffset.width}
                height={trackHeight}
                fill="#ffffff"
                fillOpacity={0.03}
                rx={4}
            />

            {/* Center line */}
            <line
                x1={chartOffset.left}
                y1={centerY}
                x2={chartOffset.left + chartOffset.width}
                y2={centerY}
                stroke="#374151"
                strokeWidth={1}
                strokeDasharray="2 2"
            />

            {/* Fluctuating momentum line */}
            {segments.map((segment, idx) => (
                <path
                    key={`momentum-path-${idx}`}
                    d={`M ${segment.map(p => `${p.x},${p.y}`).join(' L ')}`}
                    fill="none"
                    stroke={segment[0].isBullish ? '#22d3ee' : '#ef4444'}
                    strokeWidth={2.5}
                    strokeLinecap="round"
                    strokeLinejoin="round"
                />
            ))}

            {/* Label */}
            <text
                x={chartOffset.left}
                y={trackY - 8}
                fontSize="10"
                fontWeight="900"
                fill="#6b7280"
                textAnchor="start"
                letterSpacing="1"
            >
                SMA100 MOMENTUM OSCILLATOR
            </text>
        </g>
    );
};


// ============================================================================
// ALLOCATION HEATMAP - Shows allocation ONLY between floor and ceiling
// ============================================================================
const AllocationHeatmap = ({ data, xScale, yScale, chartOffset }) => {
    const clipId = React.useMemo(
        () => `heatmap-clip-${Math.random().toString(36).slice(2)}`,
        []
    );

    if (!data || data.length === 0 || !xScale || !yScale) return null;

    // Calculate grid resolution
    const timeSteps = 60;
    const priceSteps = 40;

    // Get time bounds
    const timeRange = [data[0].timestamp, data[data.length - 1].timestamp];

    const cells = [];

    for (let i = 0; i < timeSteps; i++) {
        // Calculate time value
        const t = timeRange[0] + (i / timeSteps) * (timeRange[1] - timeRange[0]);
        const date = new Date(t);

        // Get floor and ceiling for this specific time
        const floor = floorPrice(date);
        const ceiling = ceilingPrice(date);

        // Convert to pixel position using xScale
        const tNext = timeRange[0] + ((i + 1) / timeSteps) * (timeRange[1] - timeRange[0]);
        const x1 = xScale(t);
        const x2 = xScale(tNext);
        if (!Number.isFinite(x1) || !Number.isFinite(x2)) continue;
        const x = Math.min(x1, x2);
        const cellWidth = Math.abs(x2 - x1);
        if (cellWidth <= 0) continue;

        for (let j = 0; j < priceSteps; j++) {
            // Calculate price ONLY between floor and ceiling for this time
            const pricePc = j / priceSteps;
            const price = ceiling - pricePc * (ceiling - floor);

            // Convert to pixel position using yScale
            const nextPrice = ceiling - ((j + 1) / priceSteps) * (ceiling - floor);
            const y1 = yScale(price);
            const y2 = yScale(nextPrice);
            if (!Number.isFinite(y1) || !Number.isFinite(y2)) continue;
            const y = Math.min(y1, y2);
            const cellHeight = Math.abs(y2 - y1);
            if (cellHeight <= 0) continue;

            // Calculate allocation at this (time, price) coordinate
            const allocation = allocationSignal(date, price);

            // Map allocation to color intensity
            // V3 gives high allocation across most of floor-ceiling range
            // Use linear scale with lower max opacity for better visual spread
            // 0% allocation -> 0.05 opacity (nearly invisible)
            // 100% allocation -> 0.55 opacity (medium green, not overwhelming)
            const normalizedAlloc = allocation / 100;
            const intensity = 0.05 + normalizedAlloc * 0.50;

            cells.push({
                x,
                y,
                width: cellWidth,
                height: cellHeight,
                opacity: intensity,
                date,
                price,
                allocation
            });
        }
    }

    // No cell click handler - let main chart click take precedence
    // Heatmap is purely visual; allocation info shows in main tooltip

    return (
        <>
            {chartOffset && (
                <defs>
                    <clipPath id={clipId}>
                        <rect
                            x={chartOffset.left}
                            y={chartOffset.top}
                            width={chartOffset.width}
                            height={chartOffset.height}
                        />
                    </clipPath>
                </defs>
            )}

            <g
                clipPath={chartOffset ? `url(#${clipId})` : undefined}
                style={{ pointerEvents: 'none' }}  // Let clicks pass through to chart
            >
                {cells.map((cell, idx) => (
                    <rect
                        key={idx}
                        x={cell.x}
                        y={cell.y}
                        width={cell.width}
                        height={cell.height}
                        fill="#10b981"
                        opacity={cell.opacity}
                    />
                ))}
            </g>
        </>
    );
};

// ============================================================================
// CHART COMPONENT
// ============================================================================
export default function HistoricalChart({ currentPrice, onSimulationChange }) {
    const [historicalData, setHistoricalData] = useState([]);
    const [loading, setLoading] = useState(true);
    const [selectedPoint, setSelectedPoint] = useState(null);
    const [useLogScale, setUseLogScale] = useState(false);
    const [showAnalogs, setShowAnalogs] = useState(false);
    const [showMA, setShowMA] = useState(false);
    const [analogs, setAnalogs] = useState({});

    // Calculate Golden Window Peak Zones for current and next cycles
    const peakZones = React.useMemo(() => {
        const zones = [];
        // We show data from last halving (Cycle 5 start) up to 3 years in future
        // Cycle 5: 2024-2028
        const [s5, e5] = cycleBounds(5);
        const t5 = e5.getTime() - s5.getTime();
        zones.push({
            start: s5.getTime() + t5 * 0.26,
            end: s5.getTime() + t5 * 0.39,
            id: 'cycle5',
            label: 'Peak',
            center: s5.getTime() + t5 * 0.325  // Midpoint of 26% and 39%
        });

        // Cycle 6: 2028-2032 (starts in future projections)
        const [s6, e6] = cycleBounds(6);
        const t6 = e6.getTime() - s6.getTime();
        zones.push({
            start: s6.getTime() + t6 * 0.26,
            end: s6.getTime() + t6 * 0.39,
            id: 'cycle6',
            label: 'Peak',
            center: s6.getTime() + t6 * 0.325  // Midpoint of 26% and 39%
        });

        return zones;
    }, []);

    // Load cached chart data immediately for instant display
    useEffect(() => {
        const CACHE_KEY = 'hb_chart_klines';
        try {
            const cached = localStorage.getItem(CACHE_KEY);
            if (cached) {
                const klines = JSON.parse(cached);
                if (klines && klines.length > 0) {
                    processAndSetData(klines);
                    setLoading(false);
                    console.log('[HistoricalChart] Loaded from cache:', klines.length, 'candles');
                }
            }
        } catch (e) {
            console.warn('[HistoricalChart] Cache load error:', e);
        }
        // Then fetch fresh data
        fetchHistoricalData();
    }, []);

    const processAndSetData = (data) => {
        const processed = data.map((candle, idx, arr) => {
            const date = new Date(candle[0]);
            const close = parseFloat(candle[4]);

            // Calculate SMA 100
            let sma100 = null;
            if (idx >= 99) {
                const window = arr.slice(idx - 99, idx + 1);
                const sum = window.reduce((acc, curr) => acc + parseFloat(curr[4]), 0);
                sma100 = sum / 100;
            }

            return {
                date,
                timestamp: candle[0],
                price: close,
                floor: floorPrice(date),
                ceiling: ceilingPrice(date),
                modelPrice: modelPrice(date),
                allocation: allocationSignal(date, close),
                cycleProgress: cycleProgress(date) * 100,
                sma100,
                isFuture: false,
                range: [floorPrice(date), ceilingPrice(date)],
            };
        });

        // Add future projections
        const c3PositionPath = [0.55, 0.50, 0.45, 0.40, 0.35, 0.30, 0.25, 0.20, 0.15, 0.12, 0.10, 0.08, 0.12, 0.18];
        const c4PositionPath = [0.55, 0.48, 0.35, 0.20, 0.15, 0.10, 0.08, 0.12, 0.15, 0.10, 0.05, 0.03, 0.08, 0.12];
        const lastDate = new Date(processed[processed.length - 1].date);

        for (let i = 7; i <= 1095; i += 7) {
            const futureDate = new Date(lastDate.getTime() + i * 24 * 60 * 60 * 1000);
            const weeksOut = Math.floor(i / 7);
            const fl = floorPrice(futureDate);
            const ceil = ceilingPrice(futureDate);

            let c3Price = null, c4Price = null;
            if (weeksOut < c3PositionPath.length) {
                c3Price = fl + (ceil - fl) * c3PositionPath[weeksOut];
                c4Price = fl + (ceil - fl) * c4PositionPath[weeksOut];
            }

            processed.push({
                date: futureDate,
                timestamp: futureDate.getTime(),
                price: null,
                floor: fl,
                ceiling: ceil,
                modelPrice: modelPrice(futureDate),
                c3Analog: c3Price,
                c4Analog: c4Price,
                allocation: null,
                cycleProgress: cycleProgress(futureDate) * 100,
                isFuture: true,
                range: [fl, ceil],
            });
        }

        setHistoricalData(processed);
    };

    const fetchHistoricalData = async () => {
        const CACHE_KEY = 'hb_chart_klines';
        try {
            const startTime = HALVINGS[HALVINGS.length - 1].getTime();
            const endTime = Date.now();

            const res = await fetch(
                `https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1d&startTime=${startTime}&endTime=${endTime}&limit=1000`
            );
            const data = await res.json();

            if (data && data.length > 0) {
                // Save raw klines to cache
                localStorage.setItem(CACHE_KEY, JSON.stringify(data));
                console.log('[HistoricalChart] Saved to cache:', data.length, 'candles');

                // Process and display
                processAndSetData(data);
            }
            setLoading(false);
        } catch (error) {
            console.error('Failed to fetch historical data:', error);
            setLoading(false);
        }
    };

    const handleChartClick = (data) => {
        if (data && data.activePayload && data.activePayload[0]) {
            const point = data.activePayload[0].payload;
            setSelectedPoint(point);
            if (onSimulationChange) {
                onSimulationChange({
                    date: point.date,
                    price: point.price,
                    model: {
                        floor: point.floor,
                        ceiling: point.ceiling,
                        model_price: point.modelPrice,
                        allocation_pct: point.allocation,
                        cycle_progress_pct: point.cycleProgress,
                        position_in_band_pct: point.price ? positionScore(point.date, point.price) * 100 : null,
                    }
                });
            }
        }
    };

    const handleReset = () => {
        setSelectedPoint(null);
        if (onSimulationChange) onSimulationChange(null);
    };

    const CustomTooltip = ({ active, payload }) => {
        if (active && payload && payload.length) {
            const d = payload[0].payload;
            return (
                <div className="bg-gray-900/95 backdrop-blur-sm border border-accent/30 rounded-lg p-3 text-xs shadow-2xl">
                    <p className="text-accent font-semibold mb-2">
                        {d.date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                        {d.isFuture && <span className="ml-2 text-amber-400">(Projection)</span>}
                    </p>
                    <div className="space-y-1">
                        {d.price && <p className="text-white">Price: <span className="font-bold">${d.price.toLocaleString()}</span></p>}
                        {d.sma100 && showMA && <p className="text-accent/70">SMA 100: ${d.sma100.toLocaleString(undefined, { maximumFractionDigits: 0 })}</p>}
                        <p className="text-green-400">Floor: ${d.floor.toLocaleString(undefined, { maximumFractionDigits: 0 })}</p>
                        <p className="text-red-400">Ceiling: ${d.ceiling.toLocaleString(undefined, { maximumFractionDigits: 0 })}</p>
                        <p className="text-purple-400">Model: ${d.modelPrice.toLocaleString(undefined, { maximumFractionDigits: 0 })}</p>
                        {d.c3Analog && showAnalogs && <p className="text-gray-400">Cycle 3: ${d.c3Analog.toLocaleString(undefined, { maximumFractionDigits: 0 })}</p>}
                        {d.c4Analog && showAnalogs && <p className="text-gray-500">Cycle 4: ${d.c4Analog.toLocaleString(undefined, { maximumFractionDigits: 0 })}</p>}
                        {d.allocation !== null && <p className="text-accent font-bold">Allocation: {d.allocation.toFixed(0)}%</p>}
                    </div>
                </div>
            );
        }
        return null;
    };

    if (loading) {
        return (
            <div className="bg-gradient-to-br from-gray-900/60 to-gray-900/20 backdrop-blur-sm rounded-2xl border border-accent/20 p-6 mb-4">
                <div className="text-center text-accent animate-pulse">Loading historical data...</div>
            </div>
        );
    }

    const currentData = historicalData.filter(d => !d.isFuture);
    const todayIndex = currentData.length - 1;

    return (
        <div className="bg-gradient-to-br from-gray-900/60 to-gray-900/20 backdrop-blur-sm rounded-2xl border border-accent/20 p-6 mb-4 shadow-[0_0_30px_rgba(6,182,212,0.1)]">
            <div className="flex justify-between items-center mb-4">
                <div>
                    <h2 className="text-lg font-bold text-white mb-1">Historical Analysis</h2>
                    <p className="text-xs text-gray-400">
                        {selectedPoint ? (
                            <>
                                <Lock size={10} className="inline mr-1 text-amber-400" />
                                <span className="text-amber-400 font-bold">LOCKED:</span>{' '}
                                <span className="text-accent font-semibold">{selectedPoint.date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}</span>
                            </>
                        ) : (
                            'Click any point to lock • Drag to explore'
                        )}
                    </p>
                </div>
                <div className="flex items-center gap-2">
                    <button
                        onClick={() => setShowAnalogs(!showAnalogs)}
                        className={`flex items-center gap-1 px-2 py-1.5 rounded-lg text-[10px] font-bold transition-all border ${showAnalogs
                            ? 'bg-gray-500/20 border-gray-500/50 text-gray-400'
                            : 'bg-gray-800 border-gray-700 text-gray-500 hover:text-gray-300'
                            }`}
                        title="Show Cycle 3/4 Analogs"
                    >
                        ANALOGS
                    </button>
                    <button
                        onClick={() => setShowMA(!showMA)}
                        className={`flex items-center gap-1 px-2 py-1.5 rounded-lg text-[10px] font-bold transition-all border ${showMA
                            ? 'bg-accent/20 border-accent/50 text-accent'
                            : 'bg-gray-800 border-gray-700 text-gray-500 hover:text-gray-300'
                            }`}
                        title="Show 100-day Moving Average"
                    >
                        SMA100
                    </button>
                    <button
                        onClick={() => setUseLogScale(!useLogScale)}
                        className={`flex items-center gap-1 px-2 py-1.5 rounded-lg text-[10px] font-bold transition-all border ${useLogScale
                            ? 'bg-accent/20 border-accent/50 text-accent'
                            : 'bg-gray-800 border-gray-700 text-gray-500 hover:text-gray-300'
                            }`}
                    >
                        LOG
                    </button>
                    {selectedPoint && (
                        <button
                            onClick={handleReset}
                            className="flex items-center gap-2 px-3 py-1.5 bg-amber-500/10 border border-amber-500/30 rounded-lg text-amber-400 text-xs font-semibold hover:bg-amber-500/20 transition-all"
                        >
                            <RotateCcw size={14} />
                            Unlock
                        </button>
                    )}
                </div>
            </div>

            <ResponsiveContainer width="100%" height={320}>
                <ComposedChart
                    data={historicalData}
                    onClick={handleChartClick}
                    margin={{ top: 60, right: 10, left: 0, bottom: 0 }}
                >
                    <defs>
                        {/* Allocation Zone Gradient - Green (Floor) to Transparent (Ceiling) */}
                        <linearGradient id="allocationGradient" x1="0" y1="1" x2="0" y2="0">
                            <stop offset="0%" stopColor="#10b981" stopOpacity={0.25} />
                            <stop offset="100%" stopColor="#10b981" stopOpacity={0} />
                        </linearGradient>
                        {/* BTC Price Gradient */}
                        <linearGradient id="priceGradient" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.4} />
                            <stop offset="95%" stopColor="#06b6d4" stopOpacity={0} />
                        </linearGradient>
                    </defs>

                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.2} />
                    <XAxis
                        dataKey="timestamp"
                        type="number"
                        domain={['dataMin', 'dataMax']}
                        tickFormatter={(ts) => new Date(ts).toLocaleDateString('en-US', { month: 'short', year: '2-digit' })}
                        stroke="#6b7280"
                        style={{ fontSize: '10px' }}
                    />
                    <YAxis
                        stroke="#6b7280"
                        style={{ fontSize: '10px' }}
                        scale={useLogScale ? 'log' : 'auto'}
                        domain={useLogScale ? ['auto', 'auto'] : undefined}
                        tickFormatter={(value) => `$${(value / 1000).toFixed(0)}k`}
                    />
                    <Tooltip content={<CustomTooltip />} />

                    {/* Golden Window Shading (Peak Zones) */}
                    {peakZones.map(zone => (
                        <ReferenceArea
                            key={zone.id}
                            x1={zone.start}
                            x2={zone.end}
                            fill="#fbbf24"
                            fillOpacity={0.05}
                            stroke="#fbbf24"
                            strokeOpacity={0.15}
                            strokeDasharray="3 3"
                            label={{
                                value: zone.label,
                                position: 'insideTop',
                                fill: '#fbbf24',
                                fontSize: 9,
                                fontWeight: '900',
                                opacity: 0.4
                            }}
                        />
                    ))}

                    {/* Time-Varying Allocation Heatmap */}
                    <Customized component={(props) => {
                        const { xAxisMap, yAxisMap, offset } = props;
                        if (!xAxisMap || !yAxisMap) return null;
                        const xAxis = Object.values(xAxisMap)[0];
                        const yAxis = Object.values(yAxisMap)[0];
                        if (!xAxis || !yAxis) return null;
                        return (
                            <>
                                <AllocationHeatmap
                                    data={historicalData}
                                    xScale={xAxis.scale}
                                    yScale={yAxis.scale}
                                    chartOffset={offset}
                                />
                                {showMA && (
                                    <MomentumRibbon
                                        data={historicalData}
                                        xScale={xAxis.scale}
                                        chartOffset={offset}
                                    />
                                )}
                            </>
                        );
                    }} />

                    {/* Ceiling Line */}
                    <Line type="monotone" dataKey="ceiling" stroke="#ef4444" strokeWidth={2} dot={false} />

                    {/* Floor */}
                    <Line type="monotone" dataKey="floor" stroke="#10b981" strokeWidth={2} dot={false} />

                    {/* SMA 100 */}
                    {showMA && (
                        <Line type="monotone" dataKey="sma100" stroke="#22d3ee" strokeWidth={2} strokeDasharray="5 5" dot={false} opacity={1} />
                    )}

                    {/* Cycle Analogs - high-def projections */}
                    {showAnalogs && (
                        <>
                            <Line type="monotone" dataKey="c3Analog" stroke="#f8fafc" strokeWidth={2.5} dot={false} strokeDasharray="4 4" opacity={0.9} />
                            <Line type="monotone" dataKey="c4Analog" stroke="#fbbf24" strokeWidth={2.5} dot={false} strokeDasharray="4 4" opacity={0.8} />
                        </>
                    )}

                    {/* Model Fair Value - bold dashed */}
                    <Line type="monotone" dataKey="modelPrice" stroke="#a855f7" strokeWidth={3} dot={false} strokeDasharray="8 4" />

                    {/* BTC Price - Line only, no fill */}
                    <Line type="monotone" dataKey="price" stroke="#06b6d4" strokeWidth={3} dot={false} connectNulls={false} />

                    {/* Today marker - FIXED position */}
                    {currentData[todayIndex] && (
                        <ReferenceLine
                            x={currentData[todayIndex].timestamp}
                            stroke="#f97316"
                            strokeWidth={1}
                            strokeDasharray="2 4"
                            label={{
                                value: 'NOW',
                                position: 'insideBottomLeft',
                                fill: '#f97316',
                                fontSize: 8,
                                fontWeight: '900',
                                opacity: 0.6,
                                offset: 5
                            }}
                        />
                    )}

                    {/* Halving Markers - Subtle dashed lines */}
                    {[...HALVINGS, getHalvingDate(HALVINGS.length + 1)].map((hDate, idx) => (
                        <ReferenceLine
                            key={`halving-${idx}`}
                            x={hDate.getTime()}
                            stroke="#374151"
                            strokeWidth={1}
                            strokeDasharray="2 4"
                            label={{
                                value: 'HALVING',
                                position: 'insideBottomLeft',
                                fill: '#6b7280',
                                fontSize: 8,
                                fontWeight: '900',
                                opacity: 0.6,
                                offset: 5
                            }}
                        />
                    ))}

                    {/* Selected point - orange lock line */}
                    {selectedPoint && (
                        <ReferenceLine
                            x={selectedPoint.timestamp}
                            stroke="#f97316"
                            strokeWidth={1.5}
                            strokeDasharray="3 3"
                            label={{
                                value: 'LOCKED',
                                position: 'insideTopRight',
                                fill: '#f97316',
                                fontSize: 9,
                                fontWeight: '900',
                                opacity: 0.8,
                                offset: 10
                            }}
                        />
                    )}
                </ComposedChart>
            </ResponsiveContainer>

            {/* Locked data display */}
            {selectedPoint && (
                <div className="mt-4 p-3 bg-amber-500/10 border border-amber-500/30 rounded-lg">
                    <div className="grid grid-cols-5 gap-2 text-xs text-center">
                        <div>
                            <div className="text-gray-400">Date</div>
                            <div className="text-amber-400 font-bold">{selectedPoint.date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}</div>
                        </div>
                        <div>
                            <div className="text-gray-400">Floor</div>
                            <div className="text-green-400 font-bold">${(selectedPoint.floor / 1000).toFixed(0)}k</div>
                        </div>
                        <div>
                            <div className="text-gray-400">Ceiling</div>
                            <div className="text-red-400 font-bold">${(selectedPoint.ceiling / 1000).toFixed(0)}k</div>
                        </div>
                        <div>
                            <div className="text-gray-400">Model</div>
                            <div className="text-purple-400 font-bold">${(selectedPoint.modelPrice / 1000).toFixed(0)}k</div>
                        </div>
                        {selectedPoint.allocation !== null && (
                            <div>
                                <div className="text-gray-400">Alloc</div>
                                <div className="text-accent font-bold">{selectedPoint.allocation.toFixed(0)}%</div>
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* Legend - compact for mobile */}
            <div className="flex flex-wrap justify-between gap-x-2 gap-y-2 mt-4 text-[10px]">
                <div className="flex items-center gap-1.5">
                    <div className="w-2 h-2 rounded-full bg-accent" />
                    <span className="text-gray-500">Price</span>
                </div>
                <div className="flex items-center gap-1.5">
                    <div className="w-2 h-2 rounded-full bg-green-500" />
                    <span className="text-gray-500">Floor</span>
                </div>
                <div className="flex items-center gap-1.5">
                    <div className="w-2 h-2 rounded-full bg-red-500" />
                    <span className="text-gray-500">Ceiling</span>
                </div>
                <div className="flex items-center gap-1.5">
                    <div className="w-4 h-0.5" style={{ borderTop: '2px dashed #a855f7' }} />
                    <span className="text-gray-500">Model</span>
                </div>
                <div className="flex items-center gap-1.5">
                    <div className="w-3 h-2 bg-[#fbbf24]/20 border border-[#fbbf24]/40 rounded-sm" />
                    <span className="text-gray-500">Peak</span>
                </div>
                {showMA && (
                    <div className="flex items-center gap-1.5">
                        <div className="w-4 h-0.5" style={{ borderTop: '2px dashed #22d3ee' }} />
                        <span className="text-gray-500">SMA100</span>
                    </div>
                )}
                {showAnalogs && (
                    <>
                        <div className="flex items-center gap-1.5">
                            <div className="w-4 h-0.5" style={{ borderTop: '1.5px dashed #f3f4f6' }} />
                            <span className="text-gray-500">Cycle 3</span>
                        </div>
                        <div className="flex items-center gap-1.5">
                            <div className="w-4 h-0.5" style={{ borderTop: '1.5px dashed #9ca3af' }} />
                            <span className="text-gray-500">Cycle 4</span>
                        </div>
                    </>
                )}
            </div>
        </div>
    );
}
