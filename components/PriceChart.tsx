'use client'

import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';

interface PriceChartProps {
  data: Array<{ sale_price: number; sale_date: string; grade?: string }>;
}

export default function PriceChart({ data }: PriceChartProps) {
  // 1. Format and sort data chronologically (oldest sales to newest sales)
  const formattedData = [...data]
    .map((comp, idx) => ({
      rawDate: new Date(comp.sale_date),
      price: Number(comp.sale_price),
      // Clean date string for display
      dateLabel: new Date(comp.sale_date).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }),
      grade: comp.grade || 'Raw'
    }))
    // Sort by actual timestamp so the line chart moves accurately through time
    .sort((a, b) => a.rawDate.getTime() - b.rawDate.getTime())
    // Inject a sequential index key to map the horizontal grid seamlessly
    .map((item, index) => ({ ...item, index }));

  if (formattedData.length === 0) {
    return (
      <div className="text-xs text-slate-500 italic h-36 flex items-center justify-center">
        No historical sales data yet
      </div>
    );
  }

  return (
    <div className="w-full h-36 mt-4 bg-slate-950/50 rounded-xl p-3 border border-slate-800/60 relative overflow-hidden group">
      <ResponsiveContainer width="100%" height="100%">
        {/* Swapped to AreaChart for a premium financial asset layout */}
        <AreaChart data={formattedData} margin={{ top: 10, right: 5, left: -25, bottom: 0 }}>
          
          {/* Neon Glow Gradient Definition Block */}
          <defs>
            <linearGradient id="chartGlow" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#10b981" stopOpacity={0.25}/>
              <stop offset="95%" stopColor="#10b981" stopOpacity={0.0}/>
            </linearGradient>
          </defs>

          {/* Soft background grid lines for value scale context */}
          <CartesianGrid strokeDasharray="4 4" stroke="#334155" opacity={0.15} vertical={false} />

          {/* Index Mapping: We bind the axis to the array position, not the repetitive text string */}
          <XAxis 
            dataKey="index" 
            stroke="#475569" 
            fontSize={10} 
            tickLine={false} 
            axisLine={false}
            dy={8}
            tickFormatter={(idx) => {
              // Master De-duplication Rule: Only print the text label if it's the first card or a brand new day
              if (idx === 0) return formattedData[0].dateLabel;
              if (idx === formattedData.length - 1) return formattedData[formattedData.length - 1].dateLabel;
              
              const current = formattedData[idx];
              const previous = formattedData[idx - 1];
              if (current && previous && current.dateLabel !== previous.dateLabel) {
                return current.dateLabel;
              }
              return ''; // Return blank spacer to avoid text overlapping chaos
            }}
          />
          
          <YAxis 
            stroke="#475569" 
            fontSize={10} 
            tickLine={false} 
            axisLine={false} 
            dx={-2}
            tickFormatter={(val) => `$${val}`}
          />
          
          {/* Custom Styled Glassmorphism HUD Tooltip */}
          <Tooltip 
            content={({ active, payload }) => {
              if (active && payload && payload.length) {
                const dataPoint = payload[0].payload;
                return (
                  <div className="bg-slate-900/90 backdrop-blur-md border border-slate-700/80 rounded-lg p-2 shadow-2xl text-left min-w-[100px]">
                    <p className="text-[10px] text-slate-400 font-mono font-medium">{dataPoint.dateLabel}</p>
                    <p className="text-sm font-black text-white mt-0.5">${dataPoint.price.toFixed(2)}</p>
                    <span className="text-[9px] bg-slate-800 text-emerald-400 px-1.5 py-0.2 rounded border border-slate-700 font-bold inline-block mt-1">
                      {dataPoint.grade}
                    </span>
                  </div>
                );
              }
              return null;
            }}
          />
          
          {/* The Glowing Area Fill Asset */}
          <Area 
            type="monotone" 
            dataKey="price" 
            stroke="#10b981" 
            strokeWidth={2} 
            fillOpacity={1} 
            fill="url(#chartGlow)"
            dot={{ fill: '#10b981', stroke: '#020617', strokeWidth: 1.5, r: 3 }}
            activeDot={{ r: 5, stroke: '#34d399', strokeWidth: 2, fill: '#020617' }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}