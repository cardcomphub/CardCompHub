import { createClient } from '@supabase/supabase-js'
import Link from 'next/link'

export const dynamic = 'force-dynamic';

const getSupabaseClient = () => {
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || 'https://placeholder.supabase.co'
  const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || 'placeholder'
  
  return createClient(supabaseUrl, supabaseAnonKey, {
    auth: { persistSession: false },
    global: {
      fetch: (url, options) => fetch(url, { ...options, cache: 'no-store' }),
    },
  })
}

export const metadata = {
  title: 'Hottest Market Breakouts | CardCompHub',
  description: 'Exclusive real-time market tracker for the highest trending assets and league performers.',
}

function generateSparklinePointsFromComps(comps: any[]): string {
  if (!comps || comps.length < 2) return "";
  
  const prices = comps
    .map((c: any) => Number(c.sale_price))
    .filter((p: number) => !isNaN(p) && p >= 0.25)
    .slice(-6); 
    
  if (prices.length < 2) return "";
  
  const min = Math.min(...prices);
  const max = Math.max(...prices);
  const range = max - min || 1;
  
  return prices.map((price, index) => {
    const x = (index / (prices.length - 1)) * 140;
    const y = 40 - ((price - min) / range) * 30 - 5; 
    return `${x},${y}`;
  }).join(' ');
}

export default async function HottestPlayersPage() {
  try {
    const supabase = getSupabaseClient()

    // 🚀 Parallel Fetch: Query the left and right sideboards independently at the same time
    const [leaderboardRes, downtownRes] = await Promise.all([
      supabase
        .from('hottest_players_leaderboard')
        .select('*')
        .order('hype_score', { ascending: false })
        .limit(25),
      
      supabase
        .from('hottest_players_leaderboard')
        .select('*')
        .gt('downtown_sales_count', 0)
        .order('downtown_sales_count', { ascending: false })
        .limit(10)
    ]);

    // 🛠️ Enhanced Error Handling: Check primary leaderboard response
    if (leaderboardRes.error || !leaderboardRes.data) {
      console.error("Supabase Leaderboard Error Details:", leaderboardRes.error);
      return (
        <div className="text-red-500 p-20 text-center font-mono bg-slate-950 min-h-screen">
          Failed to process live records. <br/>
          <span className="text-sm text-slate-400 mt-4 block">
            {leaderboardRes.error?.message || "Check your terminal for details."}
          </span>
        </div>
      );
    }

    const baseLeaderboard = leaderboardRes.data;

    // Process Downtown Visuals Spotlights
    const downtownSpotlight = (downtownRes.data || [])
      .filter((card: any) => card.downtown_comps)
      .map((card: any) => ({
        ...card,
        downtownSparklinePoints: generateSparklinePointsFromComps(card.downtown_comps)
      }));

    return (
      <main className="min-h-screen bg-slate-950 text-slate-100 p-4 md:p-10">
        <div className="max-w-7xl mx-auto">
          
          {/* Header */}
          <div className="border-b border-slate-900 pb-6 mb-8">
            <div className="flex items-center gap-2 mb-2">
              <span className="bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2 py-0.5 rounded text-[10px] font-mono tracking-widest uppercase font-bold">
                Real-Time Hype Metrics Engaged
              </span>
            </div>
            <h1 className="text-3xl font-black text-white tracking-tight sm:text-4xl">
              Hottest Players Dashboard
            </h1>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
            
            {/* LEFT SIDEBOARD: Performance Leaders */}
            <div className="lg:col-span-7 space-y-4">
              <div className="mb-4">
                <h2 className="text-lg font-bold text-slate-200 flex items-center gap-2">
                  🔥 Trending Market Breakouts
                </h2>
                <p className="text-xs text-slate-500 mt-0.5">Real-time overview ranking the absolute highest macro market movers and elite class performers.</p>
              </div>

              {baseLeaderboard.length > 0 ? (
                baseLeaderboard.map((player: any, index: number) => {
                  const isPositive = player.percentage_change >= 0;
                  return (
                    <Link 
                      key={player.id}
                      href={`/cards/${player.slug}`}
                      className="group flex items-center justify-between p-4 bg-slate-900/30 border border-slate-900/60 rounded-xl hover:bg-slate-900/70 hover:border-slate-800 transition-all gap-4"
                    >
                      <div className="flex items-center gap-3 min-w-0">
                        <span className="w-6 h-6 flex items-center justify-center rounded bg-slate-950 border border-slate-900 text-xs text-slate-500 font-mono font-bold">
                          {index + 1}
                        </span>
                        <div className="w-10 h-14 bg-slate-950 rounded overflow-hidden border border-slate-900 flex-shrink-0 flex items-center justify-center">
                          {player.image_url ? (
                            <img src={player.image_url} alt={player.player_name} className="h-full w-full object-cover group-hover:scale-105 transition-transform" />
                          ) : (
                            <span className="text-[8px] text-slate-700 font-mono">RAW</span>
                          )}
                        </div>
                        <div className="min-w-0">
                          <h3 className="font-bold text-slate-200 text-sm group-hover:text-emerald-400 transition-colors truncate flex items-center gap-1.5">
                            {player.player_name}
                            {player.is_rookie && <span className="text-[8px] font-bold bg-emerald-500/10 text-emerald-400 px-1 rounded border border-emerald-500/20">RC</span>}
                          </h3>
                          
                          <div className="flex gap-1 mt-1 flex-wrap">
                            <span className="text-[8px] font-mono bg-slate-950 text-slate-500 px-1.5 py-0.5 rounded border border-slate-900 uppercase">
                              {player.sport}
                            </span>
                            {player.is_stat_leader && (
                              <span className="text-[8px] bg-rose-500/10 text-rose-400 px-1.5 py-0.5 rounded font-bold border border-rose-500/20">
                                📊 Leader
                              </span>
                            )}
                            {player.is_mvp_candidate && (
                              <span className="text-[8px] bg-purple-500/10 text-purple-400 px-1.5 py-0.5 rounded font-bold border border-purple-500/20">
                                ⭐ MVP
                              </span>
                            )}
                            {player.is_in_playoffs && (
                              <span className="text-[8px] bg-blue-500/10 text-blue-400 px-1.5 py-0.5 rounded font-bold border border-blue-500/20">
                                👟 Playoffs
                              </span>
                            )}
                            {player.is_in_finals && (
                              <span className="text-[8px] bg-amber-500/10 text-amber-400 px-1.5 py-0.5 rounded font-bold border border-amber-500/20">
                                🏆 Finals
                              </span>
                            )}
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center gap-6 text-right">
                        <div>
                          <p className="text-sm font-black font-mono text-slate-200">
                            {player.current_floor > 0 ? `$${Number(player.current_floor).toFixed(2)}` : 'UNPRICED'}
                          </p>
                          <span className="text-[9px] text-slate-500 font-mono uppercase block">Avg Value</span>
                        </div>
                        <div className="min-w-[75px]">
                          <span className={`text-[11px] font-mono font-bold px-1.5 py-0.5 rounded ${player.percentage_change === 0 ? 'bg-slate-950 text-slate-500' : (isPositive ? 'bg-emerald-500/10 text-emerald-400' : 'bg-rose-500/10 text-rose-400')}`}>
                            {player.percentage_change === 0 ? '•' : (isPositive ? '▲' : '▼')} {Math.abs(player.percentage_change).toFixed(1)}%
                          </span>
                        </div>
                      </div>
                    </Link>
                  )
                })
              ) : (
                <p className="text-xs font-mono text-slate-600 bg-slate-900/10 p-6 rounded-xl border border-dashed border-slate-900 text-center">
                  No active high-velocity market movers registered in this database indexing sync.
                </p>
              )}
            </div>

            {/* RIGHT SIDEBOARD: Standalone Downtown Trend Charts */}
            <div className="lg:col-span-5 bg-slate-900/20 border border-slate-900 p-5 rounded-2xl space-y-5">
              <div>
                <h2 className="text-lg font-bold text-amber-400 flex items-center gap-2">
                  ✨ Downtown Market Visuals
                </h2>
                <p className="text-xs text-slate-500 mt-0.5">Isolated, distinct case-hit tracking displaying top 10 unique assets sorted by sales volume.</p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-1 gap-4">
                {downtownSpotlight.length > 0 ? (
                  downtownSpotlight.map((card: any) => (
                    <div key={card.id} className="p-4 bg-slate-950/60 border border-slate-900/80 rounded-xl flex flex-col gap-3">
                      
                      <div className="flex items-center justify-between gap-2 min-w-0">
                        <div className="min-w-0">
                          <h4 className="font-bold text-slate-200 text-xs truncate">{card.player_name}</h4>
                          <p className="text-[9px] text-slate-500 font-mono truncate mt-0.5">
                            {card.year} {card.brand}
                          </p>
                        </div>
                        <div className="text-right flex-shrink-0">
                          <p className="text-xs font-black text-amber-400 font-mono">${Number(card.downtown_avg_price).toFixed(2)}</p>
                          <span className="text-[8px] text-slate-500 font-mono uppercase block mt-0.5">
                            Avg Price • {card.downtown_sales_count} {card.downtown_sales_count === 1 ? 'Sale' : 'Sales'}
                          </span>
                        </div>
                      </div>

                      <div className="h-10 w-full bg-slate-900/40 rounded border border-slate-900/40 px-1 flex items-center justify-center overflow-hidden">
                        <svg className="w-full h-full overflow-visible" viewBox="0 0 140 40" preserveAspectRatio="none">
                          <defs>
                            <linearGradient id={`grad-${card.id}`} x1="0%" y1="0%" x2="0%" y2="100%">
                              <stop offset="0%" stopColor="#fbbf24" stopOpacity="0.15" />
                              <stop offset="100%" stopColor="#fbbf24" stopOpacity="0.0" />
                            </linearGradient>
                          </defs>
                          <polygon 
                            points={`0,40 ${card.downtownSparklinePoints} 140,40`} 
                            fill={`url(#grad-${card.id})`}
                          />
                          <polyline
                            fill="none"
                            stroke="#fbbf24"
                            strokeWidth="1.5"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            points={card.downtownSparklinePoints}
                          />
                        </svg>
                      </div>

                    </div>
                  ))
                ) : (
                  <p className="text-xs font-mono text-slate-600 p-6 text-center border border-dashed border-slate-900/60 rounded-xl col-span-full">No active case-hit records found.</p>
                )}
              </div>
            </div>

          </div>

        </div>
      </main>
    );
  } catch (err) {
    return <div className="text-red-500 p-20 text-center font-mono bg-slate-950 min-h-screen">Dashboard processing exception encountered.</div>
  }
}