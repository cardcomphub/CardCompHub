'use client'

import React, { useState } from 'react'
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts'

interface PriceTrendsChartProps {
  data: Array<{ sale_price: number; sale_date: string; grade?: string }>;
}

export default function PriceTrendsChart({ data }: PriceTrendsChartProps) {
  const [timeframe, setTimeframe] = useState<'7D' | '30D' | '1Y'>('30D')

  // 1. Timeframe Boundary Filtering Loop
  const now = new Date()
  const filteredTrends = (data || []).filter((comp) => {
    if (!comp.sale_date) return false
    const compDate = new Date(comp.sale_date)
    const diffTime = Math.abs(now.getTime() - compDate.getTime())
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24))

    if (timeframe === '7D') return diffDays <= 7
    if (timeframe === '30D') return diffDays <= 30
    return diffDays <= 365
  })

  // 2. DAILY AGGREGATION ENGINE: Group ALL raw + graded sales together by calendar date
  const dailyStats: Record<string, { totalVolume: number; salesCount: number; timestamp: Date }> = {}

  filteredTrends.forEach((comp) => {
    const dateObj = new Date(comp.sale_date)
    const dateLabel = dateObj.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
    const currentPrice = Number(comp.sale_price)
    
    if (!isNaN(currentPrice)) {
      if (!dailyStats[dateLabel]) {
        dailyStats[dateLabel] = { totalVolume: 0, salesCount: 0, timestamp: dateObj }
      }
      dailyStats[dateLabel].totalVolume += currentPrice
      dailyStats[dateLabel].salesCount += 1
    }
  })

  // 3. Coordinate Generation & Chronological Sorting
  const chartData = Object.entries(dailyStats)
    .map(([dateLabel, metrics]) => ({
      dateLabel,
      price: metrics.totalVolume / metrics.salesCount, // Math Mean: (Sum of all Raw + Graded / Total Transactions)
      rawDate: metrics.timestamp
    }))
    .sort((a, b) => a.rawDate.getTime() - b.rawDate.getTime())

  // 4. Axis Safety Boundaries
  const prices = chartData.map(d => d.price)
  const minPrice = prices.length > 0 ? Math.min(...prices) : 0
  const maxPrice = prices.length > 0 ? Math.max(...prices) : 0
  const yDomain = minPrice === maxPrice ? [0, Math.ceil(maxPrice) + 5] : ['auto', 'auto']

  return (
    <div className="bg-slate-900 border border-slate-800 p-6 rounded-xl shadow-md w-full">
      {/* Chart Control Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-6 gap-4">
        <div>
          <h3 className="text-lg font-bold text-white tracking-tight">Market Value Trends</h3>
          <p className="text-xs text-slate-400">Historical lookback tracking daily baseline value averages across all raw and graded transactions</p>
        </div>

        {/* Time Interval Toggle Array */}
        <div className="inline-flex bg-slate-950 p-1 rounded-lg border border-slate-800">
          {(['7D', '30D', '1Y'] as const).map((r) => (
            <button
              key={r}
              onClick={() => setTimeframe(r)}
              className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-all ${
                timeframe === r
                  ? 'bg-emerald-600 text-white shadow'
                  : 'text-slate-400 hover:text-white hover:bg-slate-900'
              }`}
            >
              {r}
            </button>
          ))}
        </div>
      </div>

      {/* Visual Workspace Rendering Frame */}
      <div className="h-64 w-full flex items-center justify-center">
        {chartData.length === 0 ? (
          <div className="text-slate-500 text-xs font-mono italic">No historical sales indexed for this lookup window.</div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="chartGlow" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10b981" stopOpacity={0.2}/>
                  <stop offset="95%" stopColor="#10b981" stopOpacity={0.0}/>
                </linearGradient>
              </defs>
              
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
              <XAxis 
                dataKey="dateLabel" 
                stroke="#64748b" 
                fontSize={11} 
                tickLine={false} 
                axisLine={false}
              />
              <YAxis 
                stroke="#64748b" 
                fontSize={11} 
                tickLine={false} 
                axisLine={false}
                tickFormatter={(value) => `$${value}`}
                domain={yDomain}
              />
              <Tooltip
                contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px' }}
                labelStyle={{ color: '#94a3b8', fontSize: '12px' }}
                itemStyle={{ color: '#10b981', fontSize: '13px', fontWeight: 'bold' }}
                formatter={(value: any) => [`$${Number(value).toFixed(2)}`, 'Daily Average']}
              />
              <Area
                type="monotone"
                dataKey="price"
                stroke="#10b981"
                strokeWidth={2.5}
                fillOpacity={1}
                fill="url(#chartGlow)"
                dot={{ r: 3, strokeWidth: 1, fill: '#0f172a' }}
                activeDot={{ r: 6 }}
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  )
}