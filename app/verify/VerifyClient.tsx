'use client'

import { useState, useEffect } from 'react'

interface CertData {
  cert_number: string
  player_name: string
  card_year: number | null
  card_brand: string
  card_grade: string
  card_number: string | null
  category: string | null
  label_type: string | null
  reverse_barcode_exists: boolean
  pop_count: number
  pop_higher: number
  cert_image_front: string | null
  cert_image_back: string | null
  slab_image_front: string | null
  slab_image_back: string | null
}

interface ApiResponse {
  success: boolean
  source?: 'database_cache' | 'live_psa_api'
  data: CertData
}

interface VerifyClientProps {
  initialServerData?: CertData | null
  requestedCertQuery?: string
}

export default function VerifyClient({ initialServerData, requestedCertQuery = '' }: VerifyClientProps) {
  const [certNumber, setCertNumber] = useState(requestedCertQuery)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  
  const [result, setResult] = useState<ApiResponse | null>(() => {
    if (initialServerData) {
      return { success: true, source: 'database_cache', data: initialServerData }
    }
    return null
  })

  useEffect(() => {
    if (requestedCertQuery) setCertNumber(requestedCertQuery)
    if (initialServerData) setResult({ success: true, source: 'database_cache', data: initialServerData })
  }, [requestedCertQuery, initialServerData])

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

 // Helper to generate a Modern EPN Affiliate eBay Link
  const generateEbayAffiliateLink = (data: CertData) => {
    // 1. Build the specific search query (e.g., "2023 Panini Prizm Anthony Edwards PSA 10")
    const yearStr = data.card_year ? `${data.card_year} ` : ''
    const searchQuery = `${yearStr}${data.card_brand} ${data.player_name} PSA ${data.card_grade}`
    const encodedQuery = encodeURIComponent(searchQuery)

    // 2. Construct standard eBay search URL for sold listings
    const baseEbaySearch = `https://www.ebay.com/sch/i.html?_nkw=${encodedQuery}&LH_Complete=1&LH_Sold=1`

    // 3. Modern EPN Tracking Parameters
    // Replace YOUR_EPN_CAMPAIGN_ID with your actual 10-digit Campaign ID
    const campaignId = 'YOUR_EPN_CAMPAIGN_ID' 
    const customId = 'slab_authenticator'

    // 4. Append tracking tags directly to the destination URL
    return `${baseEbaySearch}&mkcid=1&mkrid=711-53200-19255-0&siteid=0&campid=${campaignId}&customid=${customId}&toolid=10001&mkevt=1`
  }
  const frontImg = result?.data?.slab_image_front || result?.data?.cert_image_front
  const backImg = result?.data?.slab_image_back || result?.data?.cert_image_back

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col items-center py-12 px-4">
      <div className="w-full max-w-4xl">
        
        {/* Title Frame Banner */}
        <div className="text-center mb-10">
          <h1 className="text-3xl font-black tracking-tight text-white sm:text-4xl mb-3">
            Slab Authenticator
          </h1>
          <p className="text-slate-400 max-w-md mx-auto text-sm">
            Verify the authenticity of any PSA-graded card instantly via the official registry database.
          </p>
        </div>

        {/* Form Container */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl mb-8">
          <form onSubmit={handleVerify} className="flex flex-col sm:flex-row gap-3">
            <input
              type="text"
              placeholder="Enter 8-Digit PSA Cert Number (e.g., 100394399)"
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

        {/* 📊 CORE RESULTS PANEL */}
        {result && (
          <div className="space-y-6">
            
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 flex flex-wrap justify-between items-center shadow-2xl gap-2">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
                <h2 className="font-bold text-base text-white">Official PSA Registry Record Confirmed</h2>
              </div>
              <span className="text-[10px] uppercase font-mono tracking-wider px-2 py-1 bg-slate-950 border border-slate-800 rounded text-slate-400">
                Index Track: {result.source === 'live_psa_api' ? 'Live API Sync' : 'System Cache Grid'}
              </span>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-slate-900/40 border border-slate-900 p-4 rounded-xl text-center shadow">
                <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider font-mono">Item Grade</span>
                <p className="text-base font-black text-emerald-400 mt-1 font-mono truncate">{result.data.card_grade}</p>
              </div>
              
              <div className="bg-slate-900/40 border border-slate-900 p-4 rounded-xl text-center shadow">
                <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider font-mono">PSA Population</span>
                <p className="text-base font-black text-white mt-1 font-mono">
                  {result.data.pop_count !== null ? result.data.pop_count.toLocaleString() : 'N/A'}
                </p>
              </div>

              <div className="bg-slate-900/40 border border-slate-900 p-4 rounded-xl text-center shadow">
                <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider font-mono">PSA Pop Higher</span>
                <p className="text-base font-black text-slate-300 mt-1 font-mono">
                  {result.data.pop_higher !== null ? result.data.pop_higher.toLocaleString() : '0'}
                </p>
              </div>

              {/* 🛒 NEW: Affiliate Action Button Block */}
              <div className="bg-blue-600/10 border border-blue-500/30 p-3 rounded-xl flex items-center justify-center shadow hover:bg-blue-600/20 transition-colors">
                <a 
                  href={generateEbayAffiliateLink(result.data)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex flex-col items-center justify-center w-full h-full cursor-pointer"
                >
                  <span className="text-[10px] font-bold text-blue-400 uppercase tracking-wider font-mono mb-1">Market Value</span>
                  <p className="text-sm font-black text-white flex items-center gap-1.5">
                    Search eBay
                    <svg className="w-3 h-3 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                    </svg>
                  </p>
                </a>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-12 gap-6 items-start">
              <div className="md:col-span-7 bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-2xl space-y-4">
                <h3 className="text-sm font-bold text-white uppercase tracking-wider border-b border-slate-800 pb-2">Item Information</h3>
                
                <div className="divide-y divide-slate-800/60 font-mono text-xs">
                  <div className="py-2.5 flex justify-between items-center gap-4">
                    <span className="text-slate-500 uppercase font-bold">Cert Number</span>
                    <span className="text-white font-bold select-all text-sm">{result.data.cert_number || certNumber}</span>
                  </div>
                  <div className="py-2.5 flex justify-between items-center gap-4">
                    <span className="text-slate-500 uppercase font-bold">Label Type</span>
                    <span className="text-slate-300 text-right font-medium max-w-[240px] truncate-2-lines">{result.data.label_type || 'Standard Label Variant'}</span>
                  </div>
                  <div className="py-2.5 flex justify-between items-center gap-4">
                    <span className="text-slate-500 uppercase font-bold">Reverse Barcode</span>
                    <span className={`font-bold uppercase ${result.data.reverse_barcode_exists ? 'text-emerald-400' : 'text-slate-500'}`}>
                      {result.data.reverse_barcode_exists ? 'YES' : 'NO'}
                    </span>
                  </div>
                  <div className="py-2.5 flex justify-between items-center gap-4">
                    <span className="text-slate-500 uppercase font-bold">Year</span>
                    <span className="text-slate-200 font-bold">{result.data.card_year || 'N/A'}</span>
                  </div>
                  <div className="py-2.5 flex justify-between items-center gap-4">
                    <span className="text-slate-500 uppercase font-bold">Brand / Title</span>
                    <span className="text-slate-200 text-right font-bold max-w-[220px] truncate">{result.data.card_brand}</span>
                  </div>
                  <div className="py-2.5 flex justify-between items-center gap-4">
                    <span className="text-slate-500 uppercase font-bold">Subject</span>
                    <span className="text-white font-black max-w-[220px] truncate text-right">{result.data.player_name}</span>
                  </div>
                  <div className="py-2.5 flex justify-between items-center gap-4">
                    <span className="text-slate-500 uppercase font-bold">Card Number</span>
                    <span className="text-slate-200 font-bold">#{result.data.card_number || 'N/A'}</span>
                  </div>
                  <div className="py-2.5 flex justify-between items-center gap-4">
                    <span className="text-slate-500 uppercase font-bold">Category</span>
                    <span className="text-slate-400 uppercase tracking-wide text-[11px] font-bold">{result.data.category || 'Trading Cards'}</span>
                  </div>
                </div>
              </div>

              <div className="md:col-span-5 grid grid-cols-2 gap-4">
                <div className="flex flex-col gap-2">
                  <span className="text-[10px] font-bold text-slate-500 uppercase text-center font-mono tracking-wider">Slab Front Photo</span>
                  {frontImg ? (
                    <img 
                      src={frontImg} 
                      alt="PSA Certificate Slab Front Photography View" 
                      className="rounded-xl border border-slate-800 w-full object-contain bg-slate-950 p-1 shadow-2xl hover:scale-[1.02] transition-transform duration-200" 
                    />
                  ) : (
                    <div className="h-48 rounded-xl border border-slate-900 bg-slate-950/40 flex items-center justify-center text-[10px] text-slate-700 font-mono italic">Front Scan Not Provided</div>
                  )}
                </div>
                <div className="flex flex-col gap-2">
                  <span className="text-[10px] font-bold text-slate-500 uppercase text-center font-mono tracking-wider">Slab Back Photo</span>
                  {backImg ? (
                    <img 
                      src={backImg} 
                      alt="PSA Certificate Slab Reverse Photography View" 
                      className="rounded-xl border border-slate-800 w-full object-contain bg-slate-950 p-1 shadow-2xl hover:scale-[1.02] transition-transform duration-200" 
                    />
                  ) : (
                    <div className="h-48 rounded-xl border border-slate-900 bg-slate-950/40 flex items-center justify-center text-[10px] text-slate-700 font-mono italic">Back Scan Not Provided</div>
                  )}
                </div>
              </div>

            </div>

          </div>
        )}
      </div>
    </div>
  )
}