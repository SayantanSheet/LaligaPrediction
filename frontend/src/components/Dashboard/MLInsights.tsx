import React, { useState, useEffect } from 'react';
import { api } from '@/api/client';

export const MLInsights = () => {
    const [diagnostics, setDiagnostics] = useState<any>(null);

    useEffect(() => {
        api.getMlDiagnostics().then(setDiagnostics);
    }, []);

    if (!diagnostics) return null;

    return (
        <section className="mb-12">
            <div className="flex items-center justify-between mb-8">
                <div>
                    <h2 className="font-headline-md text-2xl text-primary font-bold tracking-tight">AI Diagnostics & Neural Weights</h2>
                    <p className="text-on-surface-variant text-xs font-data-mono uppercase tracking-[0.2em] opacity-80 mt-1">INTERNAL MODEL VALIDATION • FEATURE IMPORTANCE MATRIX</p>
                </div>
                <div className="hidden sm:flex gap-3">
                    <div className="bg-surface-container border border-white/5 px-4 py-2 rounded flex flex-col items-center">
                        <span className="text-[10px] font-label-caps text-on-surface-variant/60">VALIDATION ACCURACY</span>
                        <span className="font-data-mono text-primary text-xl font-bold">{diagnostics.accuracy}%</span>
                    </div>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
                {/* Feature Weights */}
                <div className="lg:col-span-8 flex flex-col gap-6">
                    <div className="glass-panel p-8 relative overflow-hidden group">
                        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-8">
                            <h3 className="font-label-caps text-primary text-xs tracking-[0.3em] font-bold">TOP INFLUENCING FEATURES</h3>
                            <span className="px-3 py-1 bg-white/5 border border-white/10 rounded-full font-data-mono text-[9px] text-on-surface-variant capitalize">Dataset: 2023-2024 seasons</span>
                        </div>
                        
                        <div className="space-y-8">
                            {diagnostics.feature_weights.map((feature: any) => (
                                <div key={feature.name} className="relative group">
                                    <div className="flex justify-between items-end mb-2">
                                        <div className="flex items-center gap-3">
                                            <div className="w-1.5 h-1.5 bg-primary/40 rounded-sm"></div>
                                            <p className="font-body-md text-sm font-semibold tracking-wide text-on-surface/90">{feature.name}</p>
                                        </div>
                                        <p className="font-data-mono text-xs text-primary font-bold bg-primary/5 px-2 py-0.5 rounded">{feature.weight}%</p>
                                    </div>
                                    <div className="h-2 w-full bg-surface-container rounded-full overflow-hidden flex shadow-inner">
                                        <div 
                                            className="h-full bg-gradient-to-r from-primary/60 to-primary shadow-[0_0_10px_rgba(0,229,255,0.2)] rounded-full transition-all duration-1000 ease-out group-hover:brightness-125" 
                                            style={{ width: `${feature.weight * 2}%` }}
                                        ></div>
                                    </div>
                                </div>
                            ))}
                        </div>

                        <div className="mt-12 flex flex-wrap gap-4 pt-8 border-t border-white/5">
                            <div className="flex-1 min-w-[140px] bg-white/3 border border-white/5 p-4 rounded group-hover:bg-white/5 transition-all">
                                <p className="text-[9px] font-label-caps text-on-surface-variant/60 mb-1">TOTAL TRAINING FEATURES</p>
                                <p className="font-data-mono text-lg font-bold text-primary">{diagnostics.total_features}</p>
                            </div>
                            <div className="flex-1 min-w-[140px] bg-white/3 border border-white/5 p-4 rounded group-hover:bg-white/5 transition-all">
                                <p className="text-[9px] font-label-caps text-on-surface-variant/60 mb-1">GRADIENT NORM (L2)</p>
                                <p className="font-data-mono text-lg font-bold text-purple-400">{diagnostics.gradient_norm}</p>
                            </div>
                            <div className="flex-1 min-w-[140px] bg-white/3 border border-white/5 p-4 rounded group-hover:bg-white/5 transition-all">
                                <p className="text-[9px] font-label-caps text-on-surface-variant/60 mb-1">COST FUNCTION VAL</p>
                                <p className="font-data-mono text-lg font-bold text-secondary">{diagnostics.validation_cost}</p>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Model Architecture Bento */}
                <div className="lg:col-span-4 flex flex-col gap-6">
                    <div className="glass-panel p-6 flex-1 border-l-primary/30 border-l-2">
                        <div className="flex justify-between items-start mb-6">
                            <h3 className="font-label-caps text-secondary text-xs tracking-wider font-bold">ENSEMBLE LAYERING</h3>
                            <span className="material-symbols-outlined text-secondary opacity-40">layers</span>
                        </div>
                        <div className="space-y-4">
                            <div className="flex items-center gap-4">
                                <div className="w-12 h-1 bg-primary/20 rounded-full"></div>
                                <span className="text-[10px] font-data-mono text-on-surface-variant">L1: POISSON (Poisson Dist.)</span>
                            </div>
                            <div className="flex items-center gap-4">
                                <div className="w-20 h-1 bg-primary/40 rounded-full"></div>
                                <span className="text-[10px] font-data-mono text-on-surface-variant">L2: TREE MODELS (XGB/RF)</span>
                            </div>
                            <div className="flex items-center gap-4">
                                <div className="w-24 h-1 bg-primary/80 rounded-full"></div>
                                <span className="text-[10px] font-data-mono text-primary font-bold">META: SOFTMAX LOGREG</span>
                            </div>
                        </div>
                        <p className="mt-8 text-[11px] leading-relaxed text-on-surface-variant/60 italic">
                            Architecture utilizes a cascading meta-learner to capture non-linear interactions between statistical attacking parameters and historical ELODIFF dynamics.
                        </p>
                    </div>

                    <div className="glass-panel p-6 bg-primary/5 border border-primary/20 flex flex-col justify-center items-center gap-4 text-center">
                        <div className="w-16 h-16 rounded-full border border-primary/20 flex items-center justify-center bg-primary/5">
                            <span className="material-symbols-outlined text-primary text-3xl pulse-prediction">verified_user</span>
                        </div>
                        <div>
                            <h4 className="font-label-caps text-primary text-xs font-bold tracking-widest mb-1">MODEL CERTIFIED</h4>
                            <p className="text-[10px] text-on-surface-variant px-4">Standardized for European top flight league variance capture.</p>
                        </div>
                    </div>
                </div>
            </div>
        </section>
    );
};
