import React from 'react';
import { createPortal } from 'react-dom';
import { X, HelpCircle, AlertTriangle } from 'lucide-react';

// Reusable info tooltip component - Uses Portal to render at document body level
export const InfoButton = ({ infoKey, expanded, onToggle, children }) => (
    <>
        <button
            onClick={(e) => { e.stopPropagation(); onToggle(infoKey); }}
            className="ml-2 w-5 h-5 rounded-full bg-gray-700 hover:bg-cyan-600 text-gray-400 hover:text-white transition-all inline-flex items-center justify-center flex-shrink-0"
            aria-label="More info"
        >
            <HelpCircle size={12} />
        </button>
        {expanded[infoKey] && createPortal(
            <div
                className="fixed inset-0 z-[9999] flex items-center justify-center p-4 bg-black/90"
                onClick={(e) => { e.stopPropagation(); onToggle(infoKey); }}
            >
                <div
                    className="relative w-[calc(100vw-32px)] max-w-md bg-gray-900 border border-gray-600 rounded-2xl p-5 text-sm text-gray-300 shadow-2xl"
                    onClick={(e) => e.stopPropagation()}
                >
                    <button
                        onClick={(e) => { e.stopPropagation(); onToggle(infoKey); }}
                        className="absolute top-3 right-3 w-8 h-8 rounded-full bg-gray-800 hover:bg-gray-700 text-gray-400 hover:text-white transition-all flex items-center justify-center z-10"
                    >
                        <X size={16} />
                    </button>

                    <div className="pr-8">
                        {children}
                    </div>
                </div>
            </div>,
            document.body
        )}
    </>
);

// Resilience Component: Error Boundary for UI Isolation
export class ErrorBoundary extends React.Component {
    constructor(props) {
        super(props);
        this.state = { hasError: false };
    }
    static getDerivedStateFromError(error) { return { hasError: true }; }
    componentDidCatch(error, errorInfo) { console.error(`[UI Blast Radius] ${this.props.name || 'Component'} failed:`, error, errorInfo); }
    render() {
        if (this.state.hasError) {
            return (
                <div className="p-6 rounded-2xl bg-slate-900/50 border border-red-500/30 flex flex-col items-center gap-3 text-center">
                    <AlertTriangle className="text-red-400" size={32} />
                    <div>
                        <div className="font-bold text-white mb-1">{this.props.name || 'Component'} Offline</div>
                        <div className="text-xs text-gray-400">Isolated failure prevented full app crash.</div>
                    </div>
                    <button
                        onClick={() => this.setState({ hasError: false })}
                        className="mt-2 px-4 py-1.5 rounded-full bg-red-500/20 text-red-300 text-xs hover:bg-red-500/30 transition-all border border-red-500/20"
                    >
                        Retry Component
                    </button>
                </div>
            );
        }
        return this.props.children;
    }
}
