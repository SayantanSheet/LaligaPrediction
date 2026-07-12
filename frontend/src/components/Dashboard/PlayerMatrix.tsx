import React, { useState, useEffect } from 'react';
import { api } from '@/api/client';

export const PlayerMatrix = () => {
    const [players, setPlayers] = useState<any[]>([]);
    const [selectedPlayer, setSelectedPlayer] = useState<any>(null);

    useEffect(() => {
        api.getPlayers().then(data => {
            setPlayers(data);
            if (data.length > 0) setSelectedPlayer(data[0]);
        });
    }, []);

    if (!selectedPlayer) return null;

    return (
        <section className="mb-8">
            <div className="flex items-center justify-between mb-6">
                <div>
                    <h2 className="font-headline-md text-2xl text-primary font-bold">Player Performance Matrix</h2>
                    <p className="text-on-surface-variant text-xs font-data-mono">ELITE METRIC ANALYTICS • INDIVIDUAL RADAR MAPS</p>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
                {/* Player List */}
                <div className="lg:col-span-4 glass-panel overflow-hidden flex flex-col max-h-[550px]">
                    <div className="p-4 border-b border-white/5 bg-white/5">
                        <h3 className="font-label-caps text-on-surface-variant text-[10px] tracking-widest">KEY SQUAD PROFILES</h3>
                    </div>
                    <div className="flex-1 overflow-y-auto">
                        {players.map(player => (
                            <div 
                                key={player.name} 
                                onClick={() => setSelectedPlayer(player)}
                                className={`p-4 border-b border-white/5 flex items-center gap-4 cursor-pointer transition-all ${selectedPlayer.name === player.name ? 'bg-primary/10 border-l-2 border-primary' : 'hover:bg-white/5'}`}
                            >
                                <div className="w-10 h-10 rounded-full bg-surface-container-high border border-white/10 flex items-center justify-center text-xs overflow-hidden">
                                     <img src={player.img} alt={player.name} className="w-full h-full object-cover" />
                                </div>
                                <div className="flex-1 min-w-0">
                                    <p className="font-body-md font-bold text-sm truncate">{player.name}</p>
                                    <div className="flex items-center gap-2">
                                        <div className="w-1.5 h-1.5 rounded-full bg-primary"></div>
                                        <p className="text-[9px] font-label-caps text-on-surface-variant/80 uppercase tracking-tighter">{player.team}</p>
                                    </div>
                                </div>
                                <div className="text-right">
                                    <p className="font-data-mono text-[10px] text-primary">{player.goals} GS</p>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Profile Card */}
                <div className="lg:col-span-8 glass-panel p-6 lg:p-8 flex flex-col md:flex-row gap-8 relative overflow-hidden">
                    <div className="absolute top-0 right-0 p-8 opacity-[0.03] pointer-events-none">
                        <span className="material-symbols-outlined text-[180px]">monitoring</span>
                    </div>

                    <div className="flex-1 flex flex-col gap-6">
                        <div>
                            <div className="flex items-center gap-2 mb-2">
                                <span className={`px-2 py-0.5 border text-[9px] font-label-caps tracking-widest rounded ${selectedPlayer.key_injured ? 'bg-error/10 border-error/20 text-error' : 'bg-primary/10 border-primary/20 text-primary'}`}>
                                    {selectedPlayer.key_injured ? 'STATUS: INJURED' : 'STATUS: OPTIMIZED'}
                                </span>
                                <span className="px-2 py-0.5 bg-secondary-container/10 border border-secondary/20 text-[9px] font-label-caps text-secondary tracking-widest rounded uppercase">{selectedPlayer.role}</span>
                            </div>
                            <h3 className="font-display-lg text-4xl lg:text-5xl font-bold tracking-tighter text-on-surface mb-1">{selectedPlayer.name}</h3>
                            <p className="text-primary font-label-caps text-sm tracking-widest flex items-center gap-2">
                                {selectedPlayer.tier} <span className="w-1 h-1 bg-primary/40 rounded-full"></span> {selectedPlayer.team}
                            </p>
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                            {Object.entries(selectedPlayer.stats).map(([stat, val]: [string, any]) => (
                                <div key={stat} className="bg-surface-container/40 p-3 border border-white/5 rounded">
                                    <div className="flex justify-between items-center mb-1">
                                        <p className="text-[9px] font-label-caps text-on-surface-variant/80 uppercase tracking-wider">{stat.replace('_', ' ')}</p>
                                        <p className="font-data-mono text-xs text-primary font-bold">{val}</p>
                                    </div>
                                    <div className="h-1 w-full bg-background rounded-full overflow-hidden">
                                        <div className="h-full bg-primary" style={{ width: `${val}%` }}></div>
                                    </div>
                                </div>
                            ))}
                        </div>

                        <div className="p-4 bg-[#0a0a0b] border border-white/5 rounded-lg">
                            <p className="text-[9px] font-label-caps text-primary tracking-widest mb-1.5 flex items-center gap-2">
                                <span className="material-symbols-outlined text-xs">auto_awesome</span> ANALYST INSIGHT
                            </p>
                            <p className="text-xs italic leading-relaxed text-on-surface-variant">{selectedPlayer.insight}</p>
                        </div>
                    </div>

                    <div className="w-full md:w-64 flex flex-col items-center justify-center gap-4">
                        <div className="relative w-56 h-56 flex items-center justify-center border border-white/5 rounded-full bg-gradient-to-b from-white/5 to-transparent">
                             {/* Radar Chart Mock Representation */}
                             <div className="absolute inset-4 border border-white/5 rounded-full"></div>
                             <div className="absolute inset-12 border border-white/5 rounded-full"></div>
                             <div className="absolute inset-20 border border-white/5 rounded-full"></div>
                             
                             <svg className="absolute w-full h-full p-4 overflow-visible">
                                <polygon 
                                    points="112,20 180,60 170,160 112,190 54,160 44,60" 
                                    className="fill-primary/20 stroke-primary stroke-2"
                                />
                                <circle cx="112" cy="112" r="3" className="fill-primary" />
                             </svg>

                             <span className="absolute top-2 text-[8px] font-label-caps text-primary/80">PAC</span>
                             <span className="absolute bottom-2 text-[8px] font-label-caps text-primary/80">PHY</span>
                             <span className="absolute right-2 top-1/2 -translate-y-1/2 text-[8px] font-label-caps text-primary/80">SHO</span>
                             <span className="absolute left-2 top-1/2 -translate-y-1/2 text-[8px] font-label-caps text-primary/80">DRI</span>
                        </div>
                        <p className="font-label-caps text-[10px] text-on-surface-variant tracking-[0.2em]">PERFORMANCE OVERLAY</p>
                    </div>
                </div>
            </div>
        </section>
    );
};
