import React from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';
import { Brain, TrendingUp, TrendingDown, Target, ShieldAlert, Sparkles } from 'lucide-react';
import clsx from 'clsx';

interface AIReportProps {
  ticker?: string;
  summary: string;
  sentiment: 'BULLISH' | 'BEARISH' | 'NEUTRAL';
  targetPrice: number;
  confidenceScore: number;
  riskLevel: 'LOW' | 'MEDIUM' | 'HIGH';
}

export function AIReportCard({ ticker = '', summary, sentiment, targetPrice, confidenceScore, riskLevel }: AIReportProps) {
  const isBullish = sentiment === 'BULLISH';
  const isBearish = sentiment === 'BEARISH';
  const isNeutral = !isBullish && !isBearish;
  
  const isJK = ticker.endsWith('.JK');
  const formattedPrice = isJK 
    ? `Rp ${targetPrice.toLocaleString('id-ID')}`
    : `$${targetPrice.toLocaleString('en-US', { minimumFractionDigits: 2 })}`;
  
  return (
    <Card variant="glass" className="h-full flex flex-col relative overflow-hidden border-slate-700/50 shadow-2xl bg-[#0a0b10]/80 backdrop-blur-xl">
      {/* Decorative Glow */}
      <div className={clsx(
        "absolute top-0 right-0 w-48 h-48 rounded-full blur-[100px] -z-10",
        isBullish ? "bg-emerald-500/20" : isBearish ? "bg-rose-500/20" : "bg-slate-500/20"
      )} />

      <CardHeader className="border-b border-[rgba(255,255,255,0.05)] pb-5">
        <div className="flex items-center space-x-4">
          <div className="w-12 h-12 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center shadow-inner relative overflow-hidden">
            <div className="absolute inset-0 bg-gradient-to-br from-indigo-400/20 to-transparent" />
            <Brain className="w-6 h-6 text-indigo-400 relative z-10" />
          </div>
          <div>
            <CardTitle className="flex items-center text-xl text-white">
              AI Insight <Sparkles className="w-4 h-4 ml-2 text-indigo-400" />
            </CardTitle>
            <p className="text-sm text-slate-400 mt-1">Sintesis Fundamental & Teknikal</p>
          </div>
        </div>
      </CardHeader>
      
      <CardContent className="pt-6 flex-1 flex flex-col">
        {/* Indicators */}
        <div className="grid grid-cols-2 gap-4 mb-6">
          <div className="bg-[#12141f]/80 p-4 rounded-xl border border-[rgba(255,255,255,0.03)] shadow-inner">
            <p className="text-xs text-slate-400 mb-2 flex items-center font-medium uppercase tracking-wider"><Target className="w-3.5 h-3.5 mr-1.5" /> Proyeksi Harga</p>
            <p className="text-2xl font-bold font-mono text-white tracking-tight">{formattedPrice}</p>
          </div>
          
          <div className="bg-[#12141f]/80 p-4 rounded-xl border border-[rgba(255,255,255,0.03)] shadow-inner">
            <p className="text-xs text-slate-400 mb-2 flex items-center font-medium uppercase tracking-wider"><ShieldAlert className="w-3.5 h-3.5 mr-1.5" /> Tingkat Risiko</p>
            <div className="flex items-center mt-1">
              <span className={clsx(
                "px-2.5 py-1 rounded-md text-xs font-bold uppercase tracking-widest shadow-sm",
                riskLevel === 'HIGH' ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20' :
                riskLevel === 'MEDIUM' ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20' :
                'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
              )}>
                {riskLevel}
              </span>
            </div>
          </div>
        </div>
        
        {/* Sentiment Banner */}
        <div className={clsx(
          "px-5 py-4 rounded-xl flex items-center justify-between mb-8 shadow-lg",
          isBullish ? "bg-emerald-900/20 border border-emerald-500/30 text-emerald-400" :
          isBearish ? "bg-rose-900/20 border border-rose-500/30 text-rose-400" :
          "bg-slate-800/40 border border-slate-600/30 text-slate-300"
        )}>
          <div className="flex items-center">
            {isBullish ? (
              <div className="w-8 h-8 rounded-full bg-emerald-500/20 flex items-center justify-center mr-3">
                <TrendingUp className="w-5 h-5" />
              </div>
            ) : isBearish ? (
              <div className="w-8 h-8 rounded-full bg-rose-500/20 flex items-center justify-center mr-3">
                <TrendingDown className="w-5 h-5" />
              </div>
            ) : (
              <div className="w-8 h-8 rounded-full bg-slate-500/20 flex items-center justify-center mr-3">
                <div className="w-3 h-0.5 bg-slate-400 rounded-full" />
              </div>
            )}
            <span className="text-lg font-bold tracking-wide">
              {sentiment}
            </span>
          </div>
          <div className="text-right">
            <span className="block text-[10px] uppercase tracking-wider text-slate-500 font-bold mb-0.5">Confidence</span>
            <strong className="text-xl font-mono">{confidenceScore}%</strong>
          </div>
        </div>
        
        {/* Summary Text */}
        <div className="flex-1 bg-slate-900/30 rounded-xl p-5 border border-slate-800/50">
          <h4 className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-3 flex items-center">
            Ringkasan Eksekutif
            <div className="ml-3 flex-1 h-px bg-slate-800" />
          </h4>
          <p className="text-[15px] text-slate-300 leading-relaxed text-justify">
            {summary}
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
