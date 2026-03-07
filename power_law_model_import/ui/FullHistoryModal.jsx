import React, { useState } from 'react';
import { X, History, ZoomIn, Maximize2 } from 'lucide-react';

export default function FullHistoryModal({ initialView = '30yr', buttonLabel, buttonIcon: Icon = History, buttonColor = 'cyan' }) {
    const [isOpen, setIsOpen] = useState(false);
    const [viewType, setViewType] = useState(initialView);

    // Sync view type with prop when modal opens
    const handleOpen = () => {
        setViewType(initialView);
        setIsOpen(true);
    };

    if (!isOpen) {
        const colorClasses = buttonColor === 'purple' 
            ? "bg-gradient-to-r from-purple-500/10 to-blue-500/10 border-purple-500/30 text-purple-400 hover:bg-purple-500/20 shadow-[0_0_20px_rgba(168,85,247,0.2)]"
            : "bg-gradient-to-r from-accent/10 to-purple-500/10 border-accent/30 text-accent hover:bg-accent/20 shadow-[0_0_20px_rgba(6,182,212,0.2)]";

        return (
            <button
                onClick={handleOpen}
                className={`flex items-center gap-2 px-4 py-2 border rounded-xl text-sm font-semibold transition-all ${colorClasses}`}
            >
                <Icon size={16} />
                {buttonLabel || (initialView === '30yr' ? 'Full History (30yr)' : 'Zoom View (20yr)')}
            </button>
        );
    }

    const imageSrc = viewType === '30yr' 
        ? `/model_full_history.png?v=${new Date().getUTCHours()}`
        : `/model_zoom_view.png?v=${new Date().getUTCHours()}`;

    return (
        <div className="fixed inset-0 z-[100] bg-black/95 backdrop-blur-md flex flex-col items-center justify-center p-4 overflow-hidden" onClick={() => setIsOpen(false)}>
            <div className="relative w-full h-full flex flex-col max-w-7xl" onClick={e => e.stopPropagation()}>
                
                {/* Header Controls */}
                <div className="flex items-center justify-between mb-4 px-2">
                    <div className="flex bg-gray-900/80 rounded-xl p-1 border border-white/10">
                        <button 
                            onClick={() => setViewType('30yr')}
                            className={`px-4 py-2 rounded-lg text-xs font-bold transition-all ${viewType === '30yr' ? 'bg-accent/20 text-accent shadow-[0_0_15px_rgba(6,182,212,0.3)]' : 'text-gray-500 hover:text-gray-300'}`}
                        >
                            30 YEAR VIEW
                        </button>
                        <button 
                            onClick={() => setViewType('20yr')}
                            className={`px-4 py-2 rounded-lg text-xs font-bold transition-all ${viewType === '20yr' ? 'bg-purple-500/20 text-purple-400 shadow-[0_0_15px_rgba(168,85,247,0.3)]' : 'text-gray-500 hover:text-gray-300'}`}
                        >
                            20 YEAR ZOOM
                        </button>
                    </div>

                    <button
                        onClick={() => setIsOpen(false)}
                        className="p-2 bg-white/5 hover:bg-white/10 rounded-full text-gray-400 hover:text-white transition-all border border-white/10"
                    >
                        <X size={20} />
                    </button>
                </div>

                {/* Interactive Chart Area */}
                <div className="flex-1 bg-gray-900/40 rounded-3xl border border-white/5 overflow-auto custom-scrollbar shadow-2xl relative group">
                    <div className="min-w-[1000px] h-full flex items-center justify-center p-4">
                        <img
                            src={imageSrc}
                            alt={`Bitcoin Heartbeat Model - ${viewType === '30yr' ? 'Full History' : 'Zoom View'}`}
                            className="max-w-none w-full h-auto rounded-xl object-contain select-none"
                        />
                    </div>
                    
                    {/* Floating Zoom Hint for mobile */}
                    <div className="absolute bottom-6 left-1/2 -translate-x-1/2 px-4 py-2 bg-black/60 backdrop-blur-md rounded-full border border-white/10 text-[10px] text-gray-400 flex items-center gap-2 pointer-events-none md:hidden">
                        <Maximize2 size={12} className="text-accent" />
                        Scroll / Pinch to zoom chart
                    </div>
                </div>

                {/* Footer Info */}
                <div className="mt-4 flex flex-col md:flex-row items-center justify-between px-2 gap-4">
                    <p className="text-gray-500 text-[10px] italic">
                        * Binance BTCUSDT price history • Model projections include 4-year forward outlook
                    </p>
                    <div className="flex items-center gap-4 text-[10px] font-medium text-gray-400">
                        <span className="flex items-center gap-1.5"><div className="w-2 h-2 rounded-full bg-green-500" /> Power Law Floor</span>
                        <span className="flex items-center gap-1.5"><div className="w-2 h-2 rounded-full bg-red-500" /> Cycle Ceiling</span>
                        <span className="flex items-center gap-1.5"><div className="w-2 h-2 rounded-full bg-purple-500" /> Fair Value</span>
                    </div>
                </div>
            </div>
        </div>
    );
}
