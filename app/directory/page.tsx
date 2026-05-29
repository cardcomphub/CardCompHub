import { createClient } from '@supabase/supabase-js'
import Link from 'next/link'

export const dynamic = 'force-dynamic';

// LAZY CLIENT ENGINE: Guarantees build-time stability on Vercel edge networks
const getSupabaseClient = () => {
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || 'https://placeholder.supabase.co'
  const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || 'placeholder'
  return createClient(supabaseUrl, supabaseAnonKey)
}

export default async function HomePage() {
  const supabase = getSupabaseClient()

  // Pull all base card assets along with their structural relational sets
  const { data: cards, error } = await supabase
    .from('base_cards')
    .select(`
      id,
      card_number,
      player_name,
      is_rookie,
      image_url,
      card_sets (year, brand, series, sport)
    `)
    .order('player_name', { ascending: true })

  if (error) {
    console.error('Error loading master index checklist data:', error)
  }

  // --- PROGRAMMATIC DASHBOARD PROCESSING ---
  const totalCardFootprint = cards?.length || 0
  
  // Group collections dynamically by sport and brand to generate isolated sections
  const sportsMap: Record<string, any[]> = {}
  const brandsMap: Record<string, any[]> = {}

  cards?.forEach((card) => {
    const setInfo = Array.isArray(card.card_sets) ? card.card_sets[0] : card.card_sets;
    const sport = setInfo?.sport || 'Other Sports';
    const brand = setInfo?.brand || 'Miscellaneous';

    const cardWithSet = { ...card, setInfo };

    if (!sportsMap[sport]) sportsMap[sport] = [];
    sportsMap[sport].push(cardWithSet);

    if (!brandsMap[brand]) brandsMap[brand] = [];
    brandsMap[brand].push(cardWithSet);
  });

  const totalSportsCount = Object.keys(sportsMap).length
  const totalBrandsCount = Object.keys(brandsMap).length

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100 selection:bg-emerald-500 selection:text-slate-950 pb-20">
      
      {/* 1. ENTERPRISE HERO DASHBOARD HEADER */}
      <section className="relative overflow-hidden border-b border-slate-900 bg-slate-900/10 py-16 px-6 md:px-12">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(16,185,129,0.03)_0,transparent_55%)]" />
        <div className="relative max-w-7xl mx-auto flex flex-col lg:flex-row lg:items-center lg:justify-between gap-10">
          
          <div className="max-w-2xl text-left">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-500/10 px-3 py-1 text-xs font-medium text-emerald-400 border border-emerald-500/20 font-mono mb-4">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" /> Live Pricing Analytics Core
            </span>
            <h1 className="text-4xl font-black tracking-tight text-white sm:text-5xl font-sans">
              Card<span className="text-emerald-400">Comp</span>Hub
            </h1>
            <p className="mt-3 text-sm md:text-base text-slate-400 font-medium">
              Automated multi-parallel indexing platform. Toggle custom checklists, brand clusters, and real-time variant valuations across sports.
            </p>
          </div>

          {/* Core Analytics Control Widgets */}
          <div className="grid grid-cols-3 gap-4 w-full lg:max-w-md font-mono bg-slate-900/40 border border-slate-900 p-5 rounded-2xl shadow-xl backdrop-blur-sm">
            <div className="border-r border-slate-800/60 p-2">
              <p className="text-xxs font-bold uppercase tracking-wider text-slate-500">Total Cards</p>
              <p className="text-2xl font-black text-white mt-1">{totalCardFootprint}</p>
            </div>
            <div className="border-r border-slate-800/60 p-2 pl-4">
              <p className="text-xxs font-bold uppercase tracking-wider text-slate-500">Indexed Brands</p>
              <p className="text-2xl font-black text-emerald-400 mt-1">{totalBrandsCount}</p>
            </div>
            <div className="p-2 pl-4">
              <p className="text-xxs font-bold uppercase tracking-wider text-slate-500">Active Sports</p>
              <p className="text-2xl font-black text-blue-400 mt-1">{totalSportsCount}</p>
            </div>
          </div>

        </div>
      </section>

      <div className="max-w-7xl mx-auto px-6 mt-12 space-y-16">
        
        {/* 2. SECTION: QUICK LINKS & SPORT CHECKLIST HUBS */}
        <section>
          <div className="border-b border-slate-900 pb-4 mb-6">
            <h2 className="text-lg font-bold text-white tracking-tight flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-blue-500" />
              Browse Checklist Directories
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">Jump directly into complete programmatic sets organized by major athletic category.</p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {Object.keys(sportsMap).sort().map((sport) => {
              const count = sportsMap[sport].length;
              return (
                <a 
                  key={sport} 
                  href={`#sport-section-${sport.toLowerCase().replace(/\s+/g, '-')}`}
                  className="group bg-slate-900/30 border border-slate-900 hover:border-slate-800/80 rounded-xl p-4 flex items-center justify-between transition-all hover:bg-slate-900/60"
                >
                  <div>
                    <h3 className="font-bold text-slate-200 group-hover:text-blue-400 transition-colors text-sm">{sport}</h3>
                    <p className="text-xxs text-slate-500 font-mono mt-0.5 uppercase tracking-wider">{count} Checklist Nodes</p>
                  </div>
                  <span className="text-slate-700 group-hover:text-slate-400 font-mono text-sm transition-colors">&rarr;</span>
                </a>
              );
            })}
          </div>
        </section>


        {/* 3. SECTION: BRAND SEGMENTATION PANELS */}
        <section>
          <div className="border-b border-slate-900 pb-4 mb-6">
            <h2 className="text-lg font-bold text-white tracking-tight flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-purple-500" />
              Sectioned Card Brands
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">Filter pricing checklists grouped strictly by manufacturing catalog lines.</p>
          </div>

          <div className="space-y-10">
            {Object.keys(brandsMap).sort().map((brand) => {
              const brandCards = brandsMap[brand];
              return (
                <div key={brand} className="bg-slate-900/10 border border-slate-900/60 rounded-2xl p-6">
                  <div className="flex items-center justify-between mb-4 border-b border-slate-900 pb-3">
                    <h3 className="text-sm font-bold uppercase tracking-widest font-mono text-emerald-400 bg-emerald-950/20 border border-emerald-900/30 px-3 py-1 rounded-lg">
                      {brand} Collection
                    </h3>
                    <span className="text-xxs font-mono text-slate-500">{brandCards.length} Cards Found</span>
                  </div>

                  {/* Horizontal Scroll or Grid for clean encapsulation */}
                  <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
                    {brandCards.slice(0, 5).map((card) => (
                      <Link 
                        key={card.id} 
                        href={`/cards/${card.id}`}
                        className="group bg-slate-950/40 border border-slate-900/60 hover:border-slate-800 rounded-xl p-3 flex flex-col justify-between transition-all"
                      >
                        <div className="aspect-[3/4] w-full bg-slate-950 rounded-lg overflow-hidden flex items-center justify-center p-2 mb-2 border border-slate-900/80 group-hover:border-slate-800 transition-colors">
                          {card.image_url ? (
                            <img src={card.image_url} alt={card.player_name} className="max-h-full max-w-full object-contain rounded group-hover:scale-105 transition-transform" loading="lazy" />
                          ) : (
                            <span className="text-slate-800 font-mono text-[9px]">NO IMAGE</span>
                          )}
                        </div>
                        <div>
                          <span className="text-[9px] font-bold text-slate-600 font-mono block truncate">{card.setInfo?.year} {card.setInfo?.series}</span>
                          <h4 className="font-bold text-xs text-slate-300 group-hover:text-emerald-400 truncate mt-0.5">{card.player_name}</h4>
                        </div>
                      </Link>
                    ))}
                    
                    {brandCards.length > 5 && (
                      <div className="bg-slate-950/20 border border-dashed border-slate-900 rounded-xl p-3 flex flex-col items-center justify-center text-center group">
                        <p className="text-xxs font-mono text-slate-500">+{brandCards.length - 5} More in Table</p>
                        <a href="#master-directory-table" className="text-xxs font-bold text-emerald-400 hover:underline mt-1 font-mono">View Directory ↓</a>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </section>


        {/* 4. SECTION: MASTER DIRECTORY BREAKDOWN (BY SPORT) */}
        <section id="master-directory-table" className="scroll-mt-10">
          <div className="border-b border-slate-900 pb-4 mb-6">
            <h2 className="text-lg font-bold text-white tracking-tight flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-emerald-500" />
              Master Checklist Matrix Directory
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">Comprehensive tabular configuration broken out explicitly by catalog groupings.</p>
          </div>

          <div className="space-y-12">
            {Object.keys(sportsMap).sort().map((sport) => {
              const sportCards = sportsMap[sport];
              return (
                <div 
                  key={sport} 
                  id={`sport-section-${sport.toLowerCase().replace(/\s+/g, '-')}`}
                  className="scroll-mt-6"
                >
                  <h3 className="text-base font-black text-white mb-4 tracking-tight flex items-center gap-2 border-b border-slate-900 pb-2">
                    {sport} <span className="text-xs font-normal text-slate-500 font-mono">({sportCards.length} entries)</span>
                  </h3>

                  {/* Clean, Scalable Directory Table Grid */}
                  <div className="overflow-x-auto border border-slate-900 rounded-xl bg-slate-900/20 backdrop-blur-sm">
                    <table className="w-full text-left border-collapse text-xs font-mono">
                      <thead>
                        <tr className="bg-slate-950 border-b border-slate-900 text-slate-400 font-bold uppercase tracking-wider text-[10px]">
                          <th className="py-3 px-4">Card Reference</th>
                          <th className="py-3 px-4">Player Name</th>
                          <th className="py-3 px-4">Set Configuration</th>
                          <th className="py-3 px-4">Brand</th>
                          <th className="py-3 px-4 text-right">Action</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-900 text-slate-300">
                        {sportCards.map((card) => (
                          <tr key={card.id} className="hover:bg-slate-900/40 transition-colors group">
                            <td className="py-3 px-4 text-slate-500 font-bold">
                              #{card.card_number || 'N/A'}
                            </td>
                            <td className="py-3 px-4 font-sans font-bold text-slate-200">
                              <Link href={`/cards/${card.id}`} className="hover:text-emerald-400 transition-colors flex items-center gap-2">
                                {card.player_name}
                                {card.is_rookie && (
                                  <span className="bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[9px] px-1 rounded font-black">RC</span>
                                )}
                              </Link>
                            </td>
                            <td className="py-3 px-4 text-slate-400">
                              {card.setInfo?.year} {card.setInfo?.series}
                            </td>
                            <td className="py-3 px-4">
                              <span className="bg-slate-950 px-2 py-0.5 rounded border border-slate-800 text-slate-400 text-[10px]">
                                {card.setInfo?.brand}
                              </span>
                            </td>
                            <td className="py-3 px-4 text-right">
                              <Link 
                                href={`/cards/${card.id}`}
                                className="text-emerald-500 hover:text-emerald-400 font-bold uppercase tracking-wider text-[10px]"
                              >
                                Analyze &rarr;
                              </Link>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              );
            })}
          </div>
        </section>

      </div>

      {/* 5. PLATFORM FOOTER */}
      <footer className="border-t border-slate-900 mt-24 bg-slate-950 py-8 text-center text-xs font-mono text-slate-600">
        <p>&copy; {new Date().getFullYear()} CardCompHub. All data schemas processed and indexed across global database clusters.</p>
      </footer>
    </main>
  )
}