import React, { useState, useEffect } from 'react';
import { api } from '@/api/client';
import { MatchCenter } from './MatchCenter';
import { Predictor } from './Predictor';
import { PlayerMatrix } from './PlayerMatrix';
import { MLInsights } from './MLInsights';

export const Dashboard = () => {
    const [activeTab, setActiveTab] = useState('match-center');
    const [pendingMatch, setPendingMatch] = useState<{ home: string, away: string } | null>(null);

    const tabs = [
        { id: 'match-center', name: 'Match Center', icon: 'query_stats' },
        { id: 'predictor', name: 'AI Predictor', icon: 'precision_manufacturing' },
        { id: 'player-matrix', name: 'Player Matrix', icon: 'psychology_alt' },
        { id: 'ml-insights', name: 'ML Insights', icon: 'settings_input_antenna' },
    ];

    return (
        <div className="bg-background text-on-surface font-body-md selection:bg-primary/30 selection:text-white min-h-screen">
            {/* TopAppBar */}
            <header className="fixed top-0 w-full z-50 bg-background/70 backdrop-blur-xl border-b border-white/10 flex justify-between items-center px-container-padding-mobile md:px-container-padding-desktop h-16">
                <div className="flex items-center gap-3">
                    <span className="material-symbols-outlined text-primary text-2xl">analytics</span>
                    <h1 className="font-display-lg text-2xl font-bold tracking-tighter text-primary drop-shadow-[0_0_8px_rgba(0,229,255,0.3)]">LALIGA AI ELITE</h1>
                </div>
                <div className="flex items-center gap-4">
                    <div className="hidden md:flex gap-2">
                        <span className="px-2.5 py-1 bg-surface-container-high rounded text-[10px] font-label-caps border border-white/5 tracking-wider">LIVE DATA FEED</span>
                        <span className="px-2.5 py-1 bg-primary/10 text-primary rounded text-[10px] font-label-caps border border-primary/20 tracking-wider flex items-center gap-1.5">
                            <span className="w-1.5 h-1.5 rounded-full bg-primary animate-ping"></span>SYNCED
                        </span>
                    </div>
                    <div className="cursor-pointer active:scale-95 w-8 h-8 rounded-full bg-surface-container-high border border-white/10 flex items-center justify-center text-primary-fixed">
                        <span className="material-symbols-outlined text-md">account_circle</span>
                    </div>
                </div>
            </header>

            {/* Side Navigation (Desktop Only) */}
            <aside className="fixed left-0 top-0 h-full w-64 z-40 bg-surface-container-lowest/90 backdrop-blur-2xl border-r border-white/5 flex flex-col pt-20 pb-8 hidden lg:flex">
                <div className="px-6 mb-8 flex items-center gap-4">
                    <div className="w-10 h-10 rounded-full bg-secondary-container/20 border border-secondary/30 flex items-center justify-center">
                        <span className="material-symbols-outlined text-secondary">person</span>
                    </div>
                    <div>
                        <p className="font-body-md text-primary-fixed font-bold leading-tight">Elite Analyst</p>
                        <p className="text-[10px] font-label-caps text-on-surface-variant/60">PRO TIER ACCESS</p>
                    </div>
                </div>
                <nav className="flex-1 space-y-1">
                    {tabs.map(tab => (
                        <a 
                            key={tab.id}
                            onClick={() => setActiveTab(tab.id)}
                            className={`group flex items-center space-x-4 p-4 transition-all cursor-pointer ${
                                activeTab === tab.id 
                                ? 'text-primary bg-primary/10 border-l-2 border-primary' 
                                : 'text-on-surface-variant/60 hover:bg-surface-variant/20 hover:text-primary'
                            }`}
                        >
                            <span className="material-symbols-outlined text-xl">{tab.icon}</span>
                            <span className="font-body-md">{tab.name}</span>
                        </a>
                    ))}
                </nav>
                <div className="px-6 mt-auto">
                    <div className="p-4 bg-surface-container rounded border border-white/5">
                        <p className="text-[9px] font-label-caps text-primary uppercase mb-1.5 tracking-widest flex items-center gap-1.5">
                            <span className="w-1.5 h-1.5 rounded-full bg-primary pulse-prediction"></span>Live Sync Active
                        </p>
                        <div className="h-1 w-full bg-surface-variant rounded overflow-hidden">
                            <div className="h-full bg-primary w-3/4 pulse-prediction"></div>
                        </div>
                    </div>
                </div>
            </aside>

            {/* Main Content Canvas */}
            <main className="lg:ml-64 pt-24 pb-28 px-container-padding-mobile md:px-container-padding-desktop">
                {activeTab === 'match-center' && <MatchCenter onSimulate={(home, away) => {
                    setPendingMatch({ home, away });
                    setActiveTab('predictor');
                }} />}
                {activeTab === 'predictor' && <Predictor initialMatch={pendingMatch} onClearPending={() => setPendingMatch(null)} />}
                {activeTab === 'player-matrix' && <PlayerMatrix />}
                {activeTab === 'ml-insights' && <MLInsights />}
            </main>

            {/* BottomNavBar (Mobile Only) */}
            <nav className="lg:hidden fixed bottom-0 w-full z-50 bg-background/90 backdrop-blur-md border-t border-white/10 flex justify-around items-center h-20 px-4 pb-safe shadow-[0_-8px_30px_rgba(0,0,0,0.4)]">
                {tabs.map(tab => (
                    <a 
                        key={tab.id}
                        onClick={() => setActiveTab(tab.id)}
                        className={`flex flex-col items-center justify-center transition-all cursor-pointer ${
                            activeTab === tab.id 
                            ? 'text-primary drop-shadow-[0_0_5px_rgba(0,229,255,0.4)]' 
                            : 'text-on-surface-variant opacity-60'
                        }`}
                    >
                        <span className="material-symbols-outlined text-2xl">{tab.icon}</span>
                        <span className="font-label-caps text-[9px] mt-1 tracking-wider">{tab.name.split(' ').pop()}</span>
                    </a>
                ))}
            </nav>
        </div>
    );
};
