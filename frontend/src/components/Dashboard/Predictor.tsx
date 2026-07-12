import React, { useState, useEffect, useRef } from 'react';
import { api, type PredictionResult } from '@/api/client';

export const Predictor = ({ initialMatch, onClearPending }: { initialMatch: { home: string, away: string } | null, onClearPending: () => void }) => {
    const [teams, setTeams] = useState<string[]>([]);
    const [homeTeam, setHomeTeam] = useState('Real Madrid');
    const [awayTeam, setAwayTeam] = useState('Barcelona');
    const [isSimulating, setIsSimulating] = useState(false);
    const [prediction, setPrediction] = useState<PredictionResult | null>(null);
    const [simLog, setSimLog] = useState<{ min: number, text: string, type: string }[]>([]);
    const [simClock, setSimClock] = useState(0);
    const [simScore, setSimScore] = useState({ home: 0, away: 0 });
    const logEndRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        api.getTeams().then(setTeams);
    }, []);

    useEffect(() => {
        if (initialMatch) {
            setHomeTeam(initialMatch.home);
            setAwayTeam(initialMatch.away);
            // Delay slightly to let the UI settle
            const timer = setTimeout(() => {
                runSimulation(initialMatch.home, initialMatch.away);
                onClearPending();
            }, 500);
            return () => clearTimeout(timer);
        }
    }, [initialMatch]);

    useEffect(() => {
        if (logEndRef.current) {
            logEndRef.current.scrollIntoView({ behavior: 'smooth' });
        }
    }, [simLog]);

    const runSimulation = async (overrideHome?: string, overrideAway?: string) => {
        const home = overrideHome || homeTeam;
        const away = overrideAway || awayTeam;
        if (home === away) return;
        
        setIsSimulating(true);
        setPrediction(null);
        setSimLog([{ min: 0, text: '[SYS] Booting stochastic simulation model LALIGA-V4.20...', type: 'success' }]);
        setSimClock(0);
        setSimScore({ home: 0, away: 0 });

        try {
            const result = await api.predictMatch(home, away);
            
            // Simulation loop to match the aesthetic
            let currentMin = 0;
            const interval = setInterval(() => {
                currentMin += Math.floor(Math.random() * 5) + 1;
                if (currentMin >= 90) {
                    currentMin = 90;
                    clearInterval(interval);
                    setIsSimulating(false);
                    setPrediction(result);
                    setSimLog(prev => [...prev, { min: 90, text: '[SYS] Stochastic simulation run ended. compiling statistical models.', type: 'success' }]);
                }
                setSimClock(currentMin);

                // Add random logs based on result context
                if (Math.random() < 0.3) {
                    const logs = [
                        `${home} maintains play flow through midfield lines.`,
                        `${away} is applying tactical defensive blocks.`,
                        `Intensity level remains high. Hard tackling in central sector.`,
                        `Model validation check: standard deviation within limits.`
                    ];
                    setSimLog(prev => [...prev, { min: currentMin, text: logs[Math.floor(Math.random() * logs.length)], type: 'normal' }]);
                }

                // Simulate goals if we have a result
                const [hScore, aScore] = result.predicted_score.split('-').map(Number);
                if (currentMin > 20 && Math.random() < 0.05 && simScore.home < hScore) {
                   setSimScore(prev => ({ ...prev, home: prev.home + 1 }));
                   setSimLog(prev => [...prev, { min: currentMin, text: `GOAL! ${home} converts a clinical finish!`, type: 'goal' }]);
                }
                if (currentMin > 20 && Math.random() < 0.05 && simScore.away < aScore) {
                   setSimScore(prev => ({ ...prev, away: prev.away + 1 }));
                   setSimLog(prev => [...prev, { min: currentMin, text: `GOAL! ${away} silences the stadium!`, type: 'goal' }]);
                }

            }, 200);

        } catch (err) {
            console.error(err);
            setIsSimulating(false);
        }
    };

    return (
        <section className="mb-8">
            <div className="flex items-center justify-between mb-6">
                <div>
                    <h2 className="font-headline-md text-2xl text-primary font-bold">Tactical Match Predictor</h2>
                    <p className="text-on-surface-variant text-xs font-data-mono">STOCHASTIC MODEL SIMULATION • SELECTION CRITERIA</p>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
                {/* Form */}
                <div className="lg:col-span-5 glass-panel p-6 flex flex-col gap-5">
                    <div>
                        <h3 className="font-label-caps text-primary mb-1 text-xs tracking-wider">TEAM CONFIGURATOR</h3>
                    </div>
                    <div>
                        <label className="block text-[10px] font-label-caps text-on-surface-variant mb-1.5">HOME TEAM</label>
                        <select 
                            value={homeTeam} 
                            onChange={(e) => setHomeTeam(e.target.value)}
                            className="w-full bg-[#0e0e0f] border border-white/10 rounded px-3 py-2 text-sm text-on-surface outline-none focus:ring-1 focus:ring-primary"
                        >
                            {teams.map(t => <option key={t} value={t}>{t}</option>)}
                        </select>
                    </div>
                    <div>
                        <label className="block text-[10px] font-label-caps text-on-surface-variant mb-1.5">AWAY TEAM</label>
                        <select 
                            value={awayTeam} 
                            onChange={(e) => setAwayTeam(e.target.value)}
                            className="w-full bg-[#0e0e0f] border border-white/10 rounded px-3 py-2 text-sm text-on-surface outline-none focus:ring-1 focus:ring-primary"
                        >
                            {teams.map(t => <option key={t} value={t}>{t}</option>)}
                        </select>
                    </div>

                    <button 
                        onClick={() => runSimulation()}
                        disabled={isSimulating}
                        className={`w-full mt-4 py-3.5 bg-primary text-black font-label-caps text-xs transition-all tracking-widest font-bold shadow-[0_0_15px_rgba(0,229,255,0.2)] active:scale-95 ${isSimulating ? 'opacity-50 cursor-not-allowed' : 'hover:bg-[#00daf3]'}`}
                    >
                        {isSimulating ? 'SIMULATING...' : 'RUN PREDICTION ENGINE'}
                    </button>
                </div>

                {/* Simulation Visualizer */}
                <div className="lg:col-span-7 flex flex-col gap-6">
                    <div className="glass-panel p-6 flex flex-col gap-4 relative overflow-hidden">
                        {!isSimulating && !prediction && (
                            <div className="h-64 flex flex-col items-center justify-center text-center p-6 space-y-4">
                                <span className="material-symbols-outlined text-5xl text-primary/40 animate-pulse">terminal</span>
                                <div>
                                    <h4 className="font-label-caps text-primary tracking-wide text-xs">AWAITING SIMULATION TRIGGER</h4>
                                    <p className="text-xs text-on-surface-variant max-w-sm mt-1">Configure your teams on the left and run the elite AI simulation engine.</p>
                                </div>
                            </div>
                        )}

                        {(isSimulating || prediction) && (
                            <div className="flex flex-col gap-4">
                                <div className="flex justify-between items-center border-b border-white/5 pb-3">
                                    <div className="flex items-center gap-3">
                                        <span className="font-data-mono text-xl text-primary">{String(simClock).padStart(2, '0')}:00</span>
                                        <span className={`px-2 py-0.5 bg-primary/10 border border-primary/20 text-[9px] font-label-caps text-primary tracking-wider rounded uppercase ${isSimulating ? 'pulse-prediction' : ''}`}>
                                            {isSimulating ? 'SIMULATING' : 'COMPLETED'}
                                        </span>
                                    </div>
                                    <div className="bg-surface-container px-4 py-1.5 border border-white/5 rounded">
                                        <span className="font-display-lg text-lg font-bold">{simScore.home} - {simScore.away}</span>
                                    </div>
                                </div>

                                <div className="h-44 bg-[#050506] border border-white/5 rounded p-3 font-data-mono text-xs flex flex-col gap-2 overflow-y-auto">
                                    {simLog.map((log, i) => (
                                        <div key={i} className={`console-line py-0.5 px-2 ${log.type === 'goal' ? 'goal text-white font-bold' : log.type === 'success' ? 'success text-primary' : 'text-on-surface-variant/80'}`}>
                                            [{String(log.min).padStart(2, '0')}:00] {log.text}
                                        </div>
                                    ))}
                                    <div ref={logEndRef} />
                                </div>

                                {prediction && (
                                    <div className="grid grid-cols-3 gap-4 pt-4 border-t border-white/5">
                                        <div className="flex flex-col items-center gap-2">
                                            <div className="relative w-16 h-16 flex items-center justify-center">
                                                <svg className="w-full h-full transform -rotate-90">
                                                    <circle cx="32" cy="32" r="28" stroke="rgba(255,255,255,0.05)" strokeWidth="4" fill="transparent"/>
                                                    <circle cx="32" cy="32" r="28" stroke="#00e5ff" strokeWidth="4" fill="transparent"
                                                        strokeDasharray="175.9" strokeDashoffset={175.9 - (prediction.probabilities.home_win * 100 / 100) * 175.9}
                                                        className="radial-progress-bar" strokeLinecap="round"/>
                                                </svg>
                                                <span className="absolute text-[10px] font-data-mono font-bold">{Math.round(prediction.probabilities.home_win * 100)}%</span>
                                            </div>
                                            <span className="text-[9px] font-label-caps text-on-surface-variant font-bold">HOME WIN</span>
                                        </div>
                                        <div className="flex flex-col items-center gap-2">
                                            <div className="relative w-16 h-16 flex items-center justify-center">
                                                <svg className="w-full h-full transform -rotate-90">
                                                    <circle cx="32" cy="32" r="28" stroke="rgba(255,255,255,0.05)" strokeWidth="4" fill="transparent"/>
                                                    <circle cx="32" cy="32" r="28" stroke="#909095" strokeWidth="4" fill="transparent"
                                                        strokeDasharray="175.9" strokeDashoffset={175.9 - (prediction.probabilities.draw * 100 / 100) * 175.9}
                                                        className="radial-progress-bar" strokeLinecap="round"/>
                                                </svg>
                                                <span className="absolute text-[10px] font-data-mono font-bold">{Math.round(prediction.probabilities.draw * 100)}%</span>
                                            </div>
                                            <span className="text-[9px] font-label-caps text-on-surface-variant font-bold">DRAW</span>
                                        </div>
                                        <div className="flex flex-col items-center gap-2">
                                            <div className="relative w-16 h-16 flex items-center justify-center">
                                                <svg className="w-full h-full transform -rotate-90">
                                                    <circle cx="32" cy="32" r="28" stroke="rgba(255,255,255,0.05)" strokeWidth="4" fill="transparent"/>
                                                    <circle cx="32" cy="32" r="28" stroke="#cdbdff" strokeWidth="4" fill="transparent"
                                                        strokeDasharray="175.9" strokeDashoffset={175.9 - (prediction.probabilities.away_win * 100 / 100) * 175.9}
                                                        className="radial-progress-bar" strokeLinecap="round"/>
                                                </svg>
                                                <span className="absolute text-[10px] font-data-mono font-bold">{Math.round(prediction.probabilities.away_win * 100)}%</span>
                                            </div>
                                            <span className="text-[9px] font-label-caps text-on-surface-variant font-bold">AWAY WIN</span>
                                        </div>
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </section>
    );
};
