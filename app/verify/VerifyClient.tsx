'use client'

import { useState } from 'react'

interface CertData {
  player_name: string
  card_year: number | null
  card_brand: string
  card_grade: string
  cert_image_front: string | null
  cert_image_back: string | null
  is_valid_slab: boolean
}

interface ApiResponse {
  source: 'database_cache' | 'live_psa_api'
  data: CertData
  debugRaw?: any
}

export default function VerifyClient() {
  const [certNumber, setCertNumber] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<ApiResponse | null>(null)

  const handleVerify = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!certNumber.trim()) return

    setLoading(true)
    setError(null)
    setResult(null)

    try {
      const response = await fetch('/api/psa/verify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ certNumber: certNumber.trim() }),
      })

      const payload = await response.json()

      if (!response.ok) {
        throw new Error(payload.error || 'Failed to authenticate certificate number.')
      }

      setResult(payload)
    } catch (err: any) {
      setError(err.message || 'An unexpected error occurred.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col items-center py-12 px-4">
      <div className="w-full max-w-3xl">
        
        <div className="text-center mb-10">
          <h1 className="text-3xl font-black tracking-tight text-white sm:text-4xl mb-3">
            Slab Authenticator
          </h1>
          <p className="text-slate-400 max-w-md mx-auto text-sm">
            Verify the authenticity of any PSA-graded card instantly via the official registry database.
          </p>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl mb-8">
          <form onSubmit={handleVerify} className="flex flex-col sm:flex-row gap-3">
            <input
              type="text"
              placeholder="Enter 8-Digit PSA Cert Number (e.g., 69701173)"
              value={certNumber}
              onChange={(e) => setCertNumber(e.target.value)}
              disabled={loading}
              className="flex-1 bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-white placeholder-slate-600 focus:outline-none focus:border-emerald-500 transition font-mono"
            />
            <button
              type="submit"
              disabled={loading || !certNumber.trim()}
              className="bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-800 disabled:text-slate-600 text-slate-950 font-bold px-6 py-3 rounded-xl transition cursor-pointer flex items-center justify-center min-w-[140px]"
            >
              {loading ? (
                <span className="w-5 h-5 border-2 border-slate-950 border-t-transparent rounded-full animate-spin" />
              ) : (
                'Verify Slab'
              )}
            </button>
          </form>

          {error && (
            <div className="mt-4 bg-rose-950/30 border border-rose-900/50 text-rose-400 px-4 py-3 rounded-xl text-sm font-mono">
              ⚠️ {error}
            </div>
          )}
        </div>

        {result && (
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-2xl">
            <div className="flex flex-wrap justify-between items-center border-b border-slate-800 pb-4 mb-6 gap-2">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
                <h2 className="font-bold text-lg text-white">PSA Verified Authentic</h2>
              </div>
              <span className="text-[10px] uppercase font-mono tracking-wider px-2 py-1 bg-slate-950 border border-slate-800 rounded text-slate-400">
                Source: {result.source === 'database_cache' ? 'Supabase Cache' : 'Live PSA API'}
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-4">
                <div>
                  <label className="text-xs font-bold text-slate-500 uppercase font-mono">Player / Item</label>
                  <p className="text-xl font-extrabold text-white mt-0.5">{result.data.player_name}</p>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-xs font-bold text-slate-500 uppercase font-mono">Year</label>
                    <p className="text-base font-semibold text-slate-200 mt-0.5">{result.data.card_year || 'N/A'}</p>
                  </div>
                  <div>
                    <label className="text-xs font-bold text-slate-500 uppercase font-mono">Official Grade</label>
                    <p className="text-base font-black text-emerald-400 mt-0.5 font-mono">{result.data.card_grade}</p>
                  </div>
                </div>
                <div>
                  <label className="text-xs font-bold text-slate-500 uppercase font-mono">Brand / Set Identity</label>
                  <p className="text-sm font-medium text-slate-300 mt-0.5">{result.data.card_brand}</p>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-[10px] font-bold text-slate-500 uppercase block mb-1 text-center font-mono">Slab Front</label>
                  {result.data.cert_image_front ? (
                    <img src={result.data.cert_image_front} alt="PSA Slab Front" className="rounded-xl border border-slate-800 max-h-60 mx-auto object-contain bg-slate-950 p-1 shadow-lg" />
                  ) : (
                    <div className="h-40 rounded-xl border border-slate-800 bg-slate-950 flex items-center justify-center text-xs text-slate-600 italic">No Scan Provided</div>
                  )}
                </div>
                <div>
                  <label className="text-[10px] font-bold text-slate-500 uppercase block mb-1 text-center font-mono">Slab Back</label>
                  {result.data.cert_image_back ? (
                    <img src={result.data.cert_image_back} alt="PSA Slab Back" className="rounded-xl border border-slate-800 max-h-60 mx-auto object-contain bg-slate-950 p-1 shadow-lg" />
                  ) : (
                    <div className="h-40 rounded-xl border border-slate-800 bg-slate-950 flex items-center justify-center text-xs text-slate-600 italic">No Scan Provided</div>
                  )}
                </div>
              </div>

              {result.debugRaw && (
                <div className="mt-8 pt-6 border-t border-slate-800 w-full md:col-span-2">
                  <label className="text-xs font-bold text-amber-500 uppercase font-mono block mb-2">🔴 Live API Debugger: Raw Payload From PSA</label>
                  <pre className="bg-slate-950 p-4 rounded-xl text-xs text-emerald-400 overflow-x-auto max-h-96 font-mono border border-slate-800">{JSON.stringify(result.debugRaw, null, 2)}</pre>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}