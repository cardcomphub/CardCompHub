import { createClient } from '@supabase/supabase-js'
import Link from 'next/link'

export const dynamic = 'force-dynamic';

const getSupabaseClient = () => {
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || 'https://placeholder.supabase.co'
  const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || 'placeholder'
  return createClient(supabaseUrl, supabaseAnonKey)
}

export default async function HomePage({
  searchParams,
}: {
  searchParams: Promise<{ q?: string; sport?: string }>;
}) {
  const supabase = getSupabaseClient()
  
  // Resolve incoming search tokens and sport parameters
  const resolvedSearchParams = await searchParams
  const searchQuery = resolvedSearchParams?.q || ''
  const sportFilter = resolvedSearchParams?.sport || ''

  // 1. DYNAMIC SERVER-SIDE QUERY: Filter on the database level to prevent alphabetical truncation traps
  let cardQuery = supabase
    .from('base_cards')
    .select(`
      id,
      card_number,
      player_name,
      is_rookie,
      image_url,
      slug,
      card_sets (year, brand, series, sport)
    `);

  // 🚀 THE SEARCH VISIBILITY FIX: Database handles the text match filter BEFORE the limit floor is enforced
  if (searchQuery) {
    cardQuery = cardQuery.ilike('player_name', `%${searchQuery}%`);
  }

  const { data: allCards, error } = await cardQuery
    .order('player_name', { ascending: true })
    .limit(5000);

  if (error) {
    console.error('Error loading master index checklist data:', error)
  }

  // 2. IN-MEMORY FILTERING PIPELINE: Handles remaining contextual sports filters cleanly
  let filteredCards = allCards || []

  // Apply case-insensitive sport filtering matching
  if (sportFilter) {
    filteredCards = filteredCards.filter((card) => {
      const setInfo = Array.isArray(card.card_sets) ? card.card_sets[0] : card.card_sets;
      return setInfo?.sport?.toLowerCase() === sportFilter.toLowerCase()
    })
  }

  // --- PROGRAMMATIC DASHBOARD MAP GENERATION WITH DEDUPLICATION ---
  const sportsMap: Record<string, any[]> = {}
  const brandsSet = new Set<string>()

  // Count occurrences within the active query footprint snapshot
  const playerGlobalCounts: Record<string, number> = {}
  allCards?.forEach((card) => {
    if (card.player_name) {
      playerGlobalCounts[card.player_name] = (playerGlobalCounts[card.player_name] || 0) + 1
    }
  })

  filteredCards.forEach((card) => {
    const setInfo = Array.isArray(card.card_sets) ? card.card_sets[0] : card.card_sets;
    const sport = setInfo?.sport || 'Other Sports';
    if (setInfo?.brand) brandsSet.add(setInfo.brand);

    if (!sportsMap[sport]) sportsMap[sport] = [];
    
    const alreadyExists = sportsMap[sport].some((c) => c.player_name === card.player_name);
    if (!alreadyExists) {
      sportsMap[sport].push({ 
        ...card, 
        setInfo,
        total_set_count: playerGlobalCounts[card.player_name || ''] || 1
      });
    }
  });

  let visualRowCount = 0
  Object.values(sportsMap).forEach((arr) => { visualRowCount += arr.length })
  const totalCardFootprint = visualRowCount

  return (
    <main className="bg-slate-950 text-slate-100 selection:bg-emerald-500 selection:text-slate-950 pb-20">
      
      {/* HERO SECTION */}
      <section className="relative overflow-hidden border-b border-slate-900 bg-slate-900/10 py-16 px-6 md:px-12">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(16,185,129,0.02)_0,transparent_55%)]" />
        <div className="relative max-w-7xl mx-auto flex flex-col lg:flex-row lg:items-center lg:justify-between gap-10">
          
          <div className="max-w-xl text-left w-full">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-500/10 px-3 py-1 text-xs font-medium text-emerald-400 border border-emerald-500/20 font-mono mb-4">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" /> Platform Analytics Engine Active
            </span>
            <h1 className="text-3xl font-black tracking-tight text-white sm:text-5xl font-sans">
              Hobby Index <span className="text-emerald-400">Dashboard</span>
            </h1>
            <p className="mt-3 text-xs md:text-sm text-slate-400 font-medium leading-relaxed mb-6">
              Search across active checklists, explore modern manufacturing sets, and locate real-time market value valuation metrics.
            </p>

            {/* HIGH-PERFORMANCE SEARCH BAR */}
            <form action="/" method="GET" className="relative max-w-md w-full flex items-center gap-2">
              <div className="relative flex-1">
                <input
                  type="text"
                  name="q"
                  defaultValue={searchQuery}
                  placeholder="Search player name (e.g., Stroud, Mahomes)..."
                  className="w-full bg-slate-900 border border-slate-800 focus:border-emerald-500 rounded-xl px-4 py-2.5 text-xs font-mono text-slate-200 placeholder-slate-500 focus:outline-none transition-colors"
                />
                {sportFilter && <input type="hidden" name="sport" value={sportFilter} />}
                
                {searchQuery && (
                  <Link
                    href={sportFilter ? `/?sport=${sportFilter}` : "/"}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 text-xs font-mono font-bold"
                  >
                    Clear
                  </Link>
                )}
              </div>
              <button
                type="submit"
                className="bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-mono text-xs font-bold px-4 py-2.5 rounded-xl transition-colors shadow-lg shadow-emerald-950/20"
              >
                Search
              </button>
            </form>
          </div>

          {/* Quick Metrics Widget Panel */}
          <div className="grid grid-cols-3 gap-4 w-full lg:max-w-md font-mono bg-slate-900/40 border border-slate-900 p-5 rounded-2xl shadow-xl h-fit">
            <div className="border-r border-slate-800/60 p-1">
              <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Players</p>
              <p className="text-xl font-black text-white mt-1">{totalCardFootprint}</p>
            </div>
            <div className="border-r border-slate-800/60 p-1 pl-3">
              <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Brands</p>
              <p className="text-xl font-black text-emerald-400 mt-1">{brandsSet.size}</p>
            </div>
            <div className="p-1 pl-3">
              <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Sports</p>
              <p className="text-xl font-black text-blue-400 mt-1">{Object.keys(sportsMap).length}</p>
            </div>
          </div>
        </div>
      </section>

      {/* HUBS SEGMENTATION LAYOUT */}
      <div className="max-w-7xl mx-auto px-6 mt-12 space-y-12">
        
        {/* Active Context Breadcrumbs */}
        {(sportFilter || searchQuery) && (
          <div className="bg-slate-900/40 border border-slate-900 rounded-xl px-4 py-3 text-xs font-mono text-slate-400 flex items-center justify-between">
            <div>
              Active Filter Parameters: {sportFilter && <span className="text-emerald-400 font-bold">Sport: {sportFilter}</span>} {searchQuery && <span className="text-blue-400 font-bold ml-2">Search: "{searchQuery}"</span>}
            </div>
            <Link href="/" className="text-xxs font-bold uppercase text-slate-500 hover:text-slate-300 underline">
              Reset Filters
            </Link>
          </div>
        )}

        {/* Sports Categories Directory Panel */}
        <section id="categories">
          <div className="border-b border-slate-900 pb-3 mb-5">
            <h2 className="text-base font-bold text-white tracking-tight flex items-center gap-2">
              <span className="h-1.5 w-1.5 rounded-full bg-blue-500" /> Filtered Checklist Sub-Hubs
            </h2>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {Object.keys(sportsMap).length > 0 ? (
              Object.keys(sportsMap).sort().map((sport) => (
                <Link 
                  key={sport} 
                  href={`/?sport=${sport}`}
                  className="group bg-slate-900/30 border border-slate-900 hover:border-slate-800 rounded-xl p-4 flex items-center justify-between transition-all hover:bg-slate-900/60"
                >
                  <div>
                    <h3 className="font-bold text-slate-300 group-hover:text-blue-400 text-xs transition-colors">{sport} Hub</h3>
                    <p className="text-[10px] text-slate-500 font-mono mt-0.5 uppercase tracking-wider">{sportsMap[sport].length} Players</p>
                  </div>
                  <span className="text-slate-700 group-hover:text-slate-400 font-mono text-xs transition-colors">&rarr;</span>
                </Link>
              ))
            ) : (
              <div className="col-span-full text-slate-500 italic font-mono text-xs text-center py-4 bg-slate-900/10 border border-slate-900 rounded-xl">
                No categorical segments match your current filter parameters.
              </div>
            )}
          </div>
        </section>

        {/* DYNAMIC CHECKLIST HUBS SECTION */}
        <section id="master-directory" className="scroll-mt-20">
          <div className="border-b border-slate-900 pb-3 mb-6">
            <h2 className="text-base font-bold text-white tracking-tight flex items-center gap-2">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" /> Active Checklist Index Tables
            </h2>
          </div>

          <div className="space-y-10">
            {Object.keys(sportsMap).length > 0 ? (
              Object.keys(sportsMap).sort().map((sport) => {
                const sportCards = sportsMap[sport];
                return (
                  <div key={sport} className="bg-slate-900/10 border border-slate-900 rounded-2xl p-5">
                    <h3 className="text-sm font-bold text-white mb-3 font-mono tracking-wider uppercase border-b border-slate-900/80 pb-2 flex items-center justify-between">
                      <span>{sport} Database</span>
                      <span className="text-xxs text-slate-500 normal-case font-normal">({sportCards.length} matching profiles)</span>
                    </h3>

                    <div className="overflow-x-auto border border-slate-900 rounded-xl bg-slate-950/40">
                      <table className="w-full text-left border-collapse text-xxs font-mono">
                        <thead>
                          <tr className="bg-slate-950 border-b border-slate-900 text-slate-500 font-bold uppercase tracking-wider">
                            <th className="py-2.5 px-4 w-20">Card Ref</th>
                            <th className="py-2.5 px-4">Player Profile Name</th>
                            <th className="py-2.5 px-4">Set Specification</th>
                            <th className="py-2.5 px-4">Brand Line</th>
                            <th className="py-2.5 px-4 text-right w-24">Analysis</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-900 text-slate-300">
                          {sportCards.map((card) => (
                            <tr key={card.id} className="hover:bg-slate-900/30 transition-colors group">
                              <td className="py-2.5 px-4 font-bold text-slate-600">#{card.card_number || 'N/A'}</td>
                              <td className="py-2.5 px-4 font-sans font-bold text-slate-200">
                                <div className="flex items-center gap-2">
                                  <Link href={`/cards/${card.slug}`} className="hover:text-emerald-400 transition-colors flex items-center gap-1.5">
                                    {card.player_name}
                                    {card.is_rookie && <span className="bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[8px] px-1 rounded font-black">RC</span>}
                                  </Link>
                                  {card.total_set_count > 1 && (
                                    <span className="inline-flex items-center rounded bg-blue-500/10 px-1.5 py-0.5 text-[8px] font-bold text-blue-400 border border-blue-500/20 font-mono tracking-wide uppercase">
                                      {card.total_set_count} Sets Tracked
                                    </span>
                                  )}
                                </div>
                              </td>
                              <td className="py-2.5 px-4 text-slate-400">
                                {card.total_set_count > 1 ? (
                                  <span className="text-slate-500 italic">Multi-Set Catalog</span>
                                ) : (
                                  `${card.setInfo?.year} ${card.setInfo?.series}`
                                )}
                              </td>
                              <td className="py-2.5 px-4">
                                <span className="bg-slate-950 px-1.5 py-0.5 rounded border border-slate-900 text-slate-400 text-[9px] font-bold">
                                  {card.total_set_count > 1 ? "Various" : card.setInfo?.brand}
                                </span>
                              </td>
                              <td className="py-2.5 px-4 text-right">
                                <Link href={`/cards/${card.slug}`} className="text-emerald-500 hover:text-emerald-400 font-bold uppercase tracking-wider text-[9px]">
                                  View Comps &rarr;
                                </Link>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                );
              })
            ) : (
              <div className="text-center py-16 border border-dashed border-slate-900 rounded-2xl bg-slate-900/10">
                <p className="text-xs text-slate-500 font-mono">No trading card rows match the parameters inside your current catalog selection.</p>
              </div>
            )}
          </div>
        </section>

      </div>

      {/* FOOTER */}
      <footer className="border-t border-slate-900 mt-24 bg-slate-950 py-8 text-center text-xs font-mono text-slate-600">
        <p>&copy; {new Date().getFullYear()} CardCompHub. All data schemas processed and indexed across global database clusters.</p>
      </footer>
    </main>
  )
}