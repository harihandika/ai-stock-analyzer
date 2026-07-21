import React from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';
import { Brain, TrendingUp, TrendingDown, Target, ShieldAlert } from 'lucide-react';
import clsx from 'clsx';

interface AIReportProps {
  summary: string;
  sentiment: 'BULLISH' | 'BEARISH' | 'NEUTRAL';
  targetPrice: number;
  confidenceScore: number;
  riskLevel: 'LOW' | 'MEDIUM' | 'HIGH';
}

export function AIReportCard({ summary, sentiment, targetPrice, confidenceScore, riskLevel }: AIReportProps) {
  const isBullish = sentiment === 'BULLISH';
  const isBearish = sentiment === 'BEARISH';
  
  return (
    <Card variant="glass" className="h-full flex flex-col relative overflow-hidden">
      {/* Decorative Glow */}
      <div className={clsx(
        "absolute top-0 right-0 w-32 h-32 rounded-full blur-[80px] -z-10",
        isBullish ? "bg-emerald-500/20" : isBearish ? "bg-rose-500/20" : "bg-slate-500/20"
      )} />

      <CardHeader className="border-b border-[rgba(255,255,255,0.05)] pb-4">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center">
            <Brain className="w-5 h-5 text-indigo-400" />
          </div>
          <div>
            <CardTitle>Analisis AI Premium</CardTitle>
            <p className="text-sm text-slate-400">Diperbarui beberapa menit yang lalu</p>
          </div>
        </div>
      </CardHeader>
      
      <CardContent className="pt-6 flex-1 flex flex-col">
        {/* Indicators */}
        <div className="grid grid-cols-2 gap-4 mb-6">
          <div className="bg-[#0a0b10]/50 p-4 rounded-lg border border-[rgba(255,255,255,0.05)]">
            <p className="text-xs text-slate-400 mb-1 flex items-center"><Target className="w-3 h-3 mr-1" /> Target Harga (12B)</p>
            <p className="text-xl font-bold font-mono">Rp {targetPrice.toLocaleString('id-ID')}</p>
          </div>
          
          <div className="bg-[#0a0b10]/50 p-4 rounded-lg border border-[rgba(255,255,255,0.05)]">
            <p className="text-xs text-slate-400 mb-1 flex items-center"><ShieldAlert className="w-3 h-3 mr-1" /> Tingkat Risiko</p>
            <div className="flex items-center mt-1">
              <span className={clsx(
                "px-2 py-0.5 rounded text-xs font-semibold uppercase tracking-wider",
                riskLevel === 'HIGH' ? 'bg-rose-500/20 text-rose-400' :
                riskLevel === 'MEDIUM' ? 'bg-yellow-500/20 text-yellow-400' :
                'bg-emerald-500/20 text-emerald-400'
              )}>
                {riskLevel}
              </span>
            </div>
          </div>
        </div>
        
        {/* Sentiment Banner */}
        <div className={clsx(
          "px-4 py-3 rounded-lg flex items-center justify-between mb-6",
          isBullish ? "bg-emerald-500/10 border border-emerald-500/20 text-emerald-400" :
          isBearish ? "bg-rose-500/10 border border-rose-500/20 text-rose-400" :
          "bg-slate-500/10 border border-slate-500/20 text-slate-400"
        )}>
          <span className="font-semibold tracking-wide flex items-center">
            {isBullish ? <TrendingUp className="w-5 h-5 mr-2" /> : isBearish ? <TrendingDown className="w-5 h-5 mr-2" /> : null}
            {sentiment}
          </span>
          <span className="text-sm">
            Confidence: <strong className="font-mono">{confidenceScore}%</strong>
          </span>
        </div>
        
        {/* Summary Text */}
        <div className="flex-1">
          <h4 className="text-sm font-semibold text-white mb-2">Ringkasan Eksekutif</h4>
          <p className="text-sm text-slate-300 leading-relaxed text-justify">
            {summary}
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
