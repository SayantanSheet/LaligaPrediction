import React, { useState, useEffect } from 'react';
import { api } from '@/api/client';

export const MatchCenter = ({ onSimulate }: { onSimulate: (home: string, away: string) => void }) => {
    const [standings, setStandings] = useState<any[]>([]);
    const [isRankingsModalOpen, setIsRankingsModalOpen] = useState(false);

    useEffect(() => {
        const fetchStandings = async () => {
            try {
                const data = await api.getStandings();
                setStandings(data);
            } catch (err) {
                console.error(err);
            }
        };
        fetchStandings();
    }, []);

    const topTeams = standings.slice(0, 4);

    return (
        <div id="match-center" className="tab-content active">
            <section className="mb-8">
                <div className="flex items-center justify-between mb-6">
                    <div>
                        <h2 className="font-headline-md text-2xl text-primary font-bold">LaLiga Match Center</h2>
                        <p className="text-on-surface-variant text-xs font-data-mono">DASHBOARD • CURRENT MATCHDAY PROJECTIONS</p>
                    </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-6">
                    {/* El Clasico Card (Example) */}
                    <div className="glass-panel p-6 flex flex-col gap-6 neon-glow-primary">
                        <div className="flex justify-between items-center">
                            <span className="text-[10px] font-label-caps bg-primary/20 text-primary px-2.5 py-1 rounded tracking-wider border border-primary/20">EL CLÁSICO</span>
                            <div className="flex items-center gap-1.5">
                                <div className="w-2 h-2 rounded-full bg-primary pulse-prediction"></div>
                                <span className="text-[10px] font-label-caps text-primary">LIVE MODEL SYNC</span>
                            </div>
                        </div>
                        <div className="flex justify-between items-center gap-4">
                            <div className="flex flex-col items-center flex-1">
                                <div className="w-14 h-14 rounded-full bg-surface-container-high border border-white/10 mb-2 flex items-center justify-center text-primary font-bold">RMA</div>
                                <p className="font-label-caps text-center font-bold">RMA</p>
                            </div>
                            <div className="text-center">
                                <p className="font-display-lg text-3xl text-primary font-bold tracking-tight">58.4%</p>
                                <p className="text-[9px] font-label-caps text-on-surface-variant">WIN CONFIDENCE</p>
                            </div>
                            <div className="flex flex-col items-center flex-1">
                                <div className="w-14 h-14 rounded-full bg-surface-container-high border border-white/10 mb-2 flex items-center justify-center text-secondary font-bold">BAR</div>
                                <p className="font-label-caps text-center font-bold">BAR</p>
                            </div>
                        </div>
                        <div className="space-y-2">
                            <div className="flex justify-between text-[10px] font-label-caps text-on-surface-variant/80">
                                <span>WIN: 58.4%</span>
                                <span>DRAW: 23.1%</span>
                                <span>LOSS: 18.5%</span>
                            </div>
                            <div className="h-2 w-full bg-surface-container rounded overflow-hidden flex">
                                <div className="h-full bg-primary" style={{ width: '58.4%' }}></div>
                                <div className="h-full bg-surface-variant" style={{ width: '23.1%' }}></div>
                                <div className="h-full bg-secondary-container" style={{ width: '18.5%' }}></div>
                            </div>
                        </div>
                        <button 
                            onClick={() => onSimulate('Real Madrid', 'Barcelona')}
                            className="w-full py-2 bg-primary/10 text-primary border border-primary/20 text-xs font-label-caps hover:bg-primary hover:text-black tracking-widest transition-all"
                        >
                            SIMULATE FIXTURE
                        </button>
                    </div>

                    {/* Madrid Derby Fixture Card */}
                    <div className="glass-panel p-6 flex flex-col justify-between gap-6">
                        <div className="flex justify-between items-center">
                            <span className="text-[10px] font-label-caps bg-surface-container-high text-on-surface-variant/80 px-2.5 py-1 rounded border border-white/5">DERBI MADRILEÑO</span>
                            <span className="text-[10px] font-label-caps text-on-surface-variant opacity-60">PROBABLE MATRIX</span>
                        </div>
                        <div className="flex justify-between items-center gap-4">
                            <div className="flex flex-col items-center flex-1">
                                <div className="w-14 h-14 rounded-full bg-surface-container-high border border-white/10 mb-2 flex items-center justify-center text-secondary">
                                    <span className="material-symbols-outlined text-3xl">sports_soccer</span>
                                </div>
                                <p className="font-label-caps text-center font-bold">ATM</p>
                            </div>
                            <div className="text-center">
                                <p className="font-display-lg text-3xl text-secondary font-bold tracking-tight">41.8%</p>
                                <p className="text-[9px] font-label-caps text-on-surface-variant">WIN CHANCE</p>
                            </div>
                            <div className="flex flex-col items-center flex-1">
                                <div className="w-14 h-14 rounded-full bg-surface-container-high border border-white/10 mb-2 flex items-center justify-center text-primary font-bold">RMA</div>
                                <p className="font-label-caps text-center font-bold">RMA</p>
                            </div>
                        </div>
                        <div className="p-3 bg-surface-container rounded border border-white/5">
                            <p className="text-[9px] font-label-caps text-secondary mb-1.5 tracking-wider">ML INSIGHT</p>
                            <p className="text-xs italic leading-snug text-on-surface-variant text-balance">ATM defensive pressure rating is at seasonal peak (+14%). Model expects low block stalemate setup.</p>
                        </div>
                        <button 
                            onClick={() => onSimulate('Atlético Madrid', 'Real Madrid')}
                            className="w-full py-2 bg-white/5 border border-white/10 text-xs font-label-caps hover:bg-secondary hover:text-black tracking-widest transition-all"
                        >
                            SIMULATE FIXTURE
                        </button>
                    </div>

                    {/* Team Power Rankings */}
                    <div className="glass-panel p-6 flex flex-col justify-between">
                        <div>
                            <h3 className="font-label-caps text-primary mb-4 flex items-center gap-2 text-xs tracking-wider">
                                <span className="material-symbols-outlined text-md">trending_up</span>
                                TEAM POWER RANKINGS
                            </h3>
                            <div className="space-y-1">
                                {topTeams.map((team, index) => (
                                    <div key={team.name} className="flex items-center justify-between p-2 hover:bg-white/5 transition-colors rounded cursor-pointer">
                                        <div className="flex items-center gap-3">
                                            <span className="font-data-mono text-primary font-bold">0{index + 1}</span>
                                            <span className="font-body-md font-bold">{team.name}</span>
                                        </div>
                                        <div className="text-right">
                                            <p className="font-data-mono text-sm">{team.pts} pts</p>
                                            <span className="text-[10px] text-primary">+{team.xgDiff} xG ▲</span>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                        <button 
                            onClick={() => setIsRankingsModalOpen(true)}
                            className="w-full mt-6 py-2 border border-white/10 text-xs font-label-caps hover:bg-primary hover:text-black tracking-widest transition-all"
                        >
                            VIEW FULL RANKINGS
                        </button>
                    </div>
                </div>

                {/* xG Comparison Widget */}
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    <div className="glass-panel p-6 lg:col-span-2">
                        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6">
                            <h3 className="font-label-caps text-primary text-xs tracking-wider">EXPECTED GOALS (xG) TRENDS</h3>
                            <div className="flex gap-4">
                                <div className="flex items-center gap-2">
                                    <div className="w-2.5 h-2.5 bg-primary rounded-sm"></div>
                                    <span className="text-[10px] font-label-caps text-on-surface-variant">xG CREATED</span>
                                </div>
                                <div className="flex items-center gap-2">
                                    <div className="w-2.5 h-2.5 bg-purple-400 rounded-sm"></div>
                                    <span className="text-[10px] font-label-caps text-on-surface-variant">xG CONCEDED</span>
                                </div>
                            </div>
                        </div>
                        <div className="h-44 w-full flex items-end justify-between gap-2 px-2 border-b border-white/10 pb-2">
                            {[0.8, 0.6, 0.95, 0.65, 0.75].map((h, i) => (
                                <div key={i} className="flex-1 flex flex-col items-center gap-2 h-full justify-end group cursor-pointer relative">
                                    <div className="w-full flex justify-center items-end gap-1 h-32">
                                        <div className="w-4 bg-primary rounded-t-sm" style={{ height: `${h * 100}%` }}></div>
                                        <div className="w-4 bg-purple-400 rounded-t-sm" style={{ height: `${(1-h) * 50 + 20}%` }}></div>
                                    </div>
                                    <span className="text-[9px] font-label-caps text-on-surface-variant">GW {12+i}</span>
                                </div>
                            ))}
                        </div>
                    </div>

                    <div className="glass-panel p-6 flex flex-col justify-between">
                        <div>
                            <h3 className="font-label-caps text-primary mb-3 text-xs tracking-wider">SIMULATION LOG FEED</h3>
                            <div className="h-28 bg-[#070708] border border-white/5 rounded p-3 font-data-mono text-[10px] space-y-1.5 overflow-y-auto">
                                <p className="text-primary/80 border-l border-primary/40 pl-1">Gradient backpropagation complete.</p>
                                <p className="text-on-surface-variant/70">Received Live Opta stats feed.</p>
                                <p className="text-on-surface-variant/70">Adjusting player weights for GW17.</p>
                            </div>
                        </div>
                        <div className="mt-4 flex gap-2">
                            <span className="w-2.5 h-2.5 bg-primary rounded-full animate-ping"></span>
                            <p className="text-[10px] font-label-caps text-primary tracking-wider uppercase">Receiving Telemetry Updates</p>
                        </div>
                    </div>
                </div>
            </section>

            {/* Rankings Modal */}
            {isRankingsModalOpen && (
                <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex items-center justify-center p-4">
                    <div className="glass-panel p-6 w-full max-w-2xl bg-background/95 max-h-[85vh] flex flex-col gap-4 overflow-hidden border border-white/10 shadow-[0_0_50px_rgba(0,229,255,0.1)]">
                        <div className="flex justify-between items-center border-b border-white/10 pb-3">
                            <div>
                                <h3 className="font-label-caps text-primary text-sm tracking-wider">LALIGA FULL MODEL STANDINGS</h3>
                            </div>
                            <button onClick={() => setIsRankingsModalOpen(false)} className="w-8 h-8 rounded-full border border-white/10 flex items-center justify-center text-on-surface-variant hover:text-primary transition-colors">
                                <span className="material-symbols-outlined text-sm">close</span>
                            </button>
                        </div>
                        <div className="flex-1 overflow-y-auto">
                            <table className="w-full text-left text-xs border-collapse">
                                <thead>
                                    <tr className="border-b border-white/5 font-label-caps text-[9px] text-on-surface-variant/80">
                                        <th className="py-2.5">POS</th>
                                        <th className="py-2.5">TEAM</th>
                                        <th className="py-2.5 text-center">PTS</th>
                                        <th className="py-2.5 text-center">xPTS</th>
                                        <th className="py-2.5 text-center">xG DIFF</th>
                                        <th className="py-2.5 text-center">TOP 4 %</th>
                                    </tr>
                                </thead>
                                <tbody className="font-data-mono">
                                    {standings.map((team, index) => (
                                        <tr key={team.name} className="border-b border-white/5 hover:bg-white/5">
                                            <td className="py-3 text-primary font-bold">#{index + 1}</td>
                                            <td className="py-3 font-semibold">{team.name}</td>
                                            <td className="py-3 text-center">{team.pts}</td>
                                            <td className="py-3 text-center text-primary-fixed">{team.xPoints}</td>
                                            <td className="py-3 text-center text-primary">{team.xgDiff}</td>
                                            <td className="py-3 text-center">{team.top4}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};
