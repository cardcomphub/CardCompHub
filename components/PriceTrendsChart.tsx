'use client'

import React, { useState, useEffect } from 'react'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts'

interface TrendPoint {
  dateLabel: string
  price: number
}

export default function PriceTrendsChart({ cardId }: { cardId: string }) {
  const [timeframe, setTimeframe] = useState<'week' | 'month' | 'year'>('month')
  const [chartData, setChartData] = useState<TrendPoint[]>([])
  const [loading, setLoading] = useState<boolean>(true)

  useEffect(() => {
    async function fetchTrends() {
      setLoading(true)
      try {
        const res = await fetch(`/cards/${cardId}/trends?range=${timeframe}`)
        if (res.ok) {
          const payload = await res.json()
          setChartData(payload.trends || [])
        }
      } catch (err) {
        // 🛠️ FIXED: Swapped out print() for console.error() to fix the TypeScript signature mismatch
        console.error("🚨 Frontend failed to fetch trends context structure:", err)
      } finally {
        setLoading(false)
      }
    }
    if (cardId) fetchTrends()
  }, [cardId, timeframe])

  return (
    <div className="bg-slate-900 border border-slate-800 p-6 rounded-xl shadow-md w-full">
      {/* Chart Control Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-6 gap-4">
        <div>
          <h3 className="text-lg font-bold text-white tracking-tight">Market Value Trends</h3>
          <p className="text-xs text-slate-400">Historical pricing index tracking across market sources</p>
        </div>

        {/* Dynamic Interval Toggle Array */}
        <div className="inline-flex bg-slate-950 p-1 rounded-lg border border-slate-800">
          {(['week', 'month', 'year'] as const).map((r) => (
            <button
              key={r}
              onClick={() => setTimeframe(r)}
              className={`px-3 py-1.5 text-xs font-semibold rounded-md uppercase transition-all ${
                timeframe === r
                  ? 'bg-blue-600 text-white shadow'
                  : 'text-slate-400 hover:text-white hover:bg-slate-900'
              }`}
            >
              {r === 'week' ? '7D' : r === 'month' ? '30D' : '1Y'}
            </button>
          ))}
        </div>
      </div>

      {/* Visual Workspace Rendering Frame */}
      <div className="h-64 w-full flex items-center justify-center">
        {loading ? (
          <div className="text-slate-500 text-xs animate-pulse">Calculating pricing vectors...</div>
        ) : chartData.length === 0 ? (
          <div className="text-slate-500 text-xs">Insufficient transaction data to graph trends.</div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
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
              />
              <Tooltip
                contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px' }}
                labelStyle={{ color: '#94a3b8', fontSize: '12px' }}
                itemStyle={{ color: '#3b82f6', fontSize: '13px', fontWeight: 'bold' }}
                formatter={(value: any) => [`$${Number(value).toFixed(2)}`, 'Value']}
              />
              <Line
                type="monotone"
                dataKey="price"
                stroke="#2563eb"
                strokeWidth={2.5}
                dot={{ r: 3, strokeWidth: 1, fill: '#0f172a' }}
                activeDot={{ r: 6 }}
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  )
}