import { createClient } from '@supabase/supabase-js'
import Link from 'next/link'
import EbayButton from '@/components/EbayButton'
import ZoomableThumbnail from '@/components/ZoomableThumbnail'
import PriceTrendsChart from '@/components/PriceTrendsChart'
import AmazonSuppliesBanner from '@/components/AmazonSuppliesBanner' 
import SignatureDisplay from '@/components/SignatureDisplay' // 🌟 ADDED COMPONENT

export const dynamic = 'force-dynamic';

const getSupabaseClient = () => {
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || 'https://placeholder.supabase.co'
  const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || 'placeholder'
  return createClient(supabaseUrl, supabaseAnonKey)
}

function generateEbayAffiliateLink(year: string, brand: string, series: string, playerName: string): string {
  const searchQuery = encodeURIComponent(`${year} ${brand} ${series} ${playerName}`);
  return `https://www.ebay.com/sch/i.html?_nkw=${searchQuery}&mkcid=1&mkrid=711-53200-19255-0&siteid=0&campid=5339053355&toolid=10001&customid=cardcomphub`;
}

export async function generateMetadata({ 
  params,
  searchParams 
}: { 
  params: Promise<{ slug?: string; id?: string }>;
  searchParams: Promise<{ set?: string }>;
}) {
  try {
    const supabase = getSupabaseClient()
    const resolvedParams = await params;
    const resolvedSearchParams = await searchParams;
    const cardSlug = resolvedParams?.slug || resolvedParams?.id;

    if (!cardSlug || cardSlug === 'undefined') {
      return { title: 'Card Profile Not Found | CardCompHub' };
    }
    
    const { data: initialCard } = await supabase
      .from('base_cards')
      .select('player_name')
      .eq('slug', cardSlug)
      .single();

    if (!initialCard) {
      return { title: 'Card Profile Not Found | CardCompHub' };
    }

    const { data: playerRootCards } = await supabase
      .from('base_cards')
      .select('id, card_number, image_url, slug, card_sets(year, brand, series)')
      .eq('player_name', initialCard.player_name);

    let activeCard = playerRootCards?.[0];
    if (resolvedSearchParams?.set) {
      activeCard = playerRootCards?.find((c: any) => {
        const s = Array.isArray(c.card_sets) ? c.card_sets[0] : c.card_sets;
        const slug = `${s?.year} ${s?.brand} ${s?.series}`.toLowerCase().replace(/[^a-z0-9]+/g, '-');
        return slug === resolvedSearchParams.set;
      }) || activeCard;
    } else {
      activeCard = playerRootCards?.find((c: any) => c.slug === cardSlug) || activeCard;
    }

    const setInfo = Array.isArray(activeCard?.card_sets) ? activeCard?.card_sets[0] : activeCard?.card_sets;
    
    // 🌟 UPDATED: Added "& Autograph" to the page title for better organic CTR
    const pageTitle = `${setInfo?.year || ''} ${setInfo?.brand || ''} ${initialCard.player_name || ''} #${activeCard?.card_number || ''} Value, Comps & Autograph`;

    // 🌟 NEW: Rich description detailing the AI signature analysis to capture high-intent search traffic
    const pageDescription = `Track real-time market value, historical sales comps, and view the verified autograph signature layout for ${initialCard.player_name} (${setInfo?.year || ''} ${setInfo?.brand || ''} #${activeCard?.card_number || ''}).`;

    return {
      title: pageTitle,
      description: pageDescription,
      openGraph: { 
        title: pageTitle, 
        description: pageDescription,
        images: [activeCard?.image_url || ''] 
      },
      twitter: {
        card: 'summary_large_image',
        title: pageTitle,
        description: pageDescription,
        images: [activeCard?.image_url || '']
      }
    };
  } catch (e) {
    return { title: 'Card Tracking Dashboard | CardCompHub' };
  }
}

export default async function CardProfilePage({ 
  params,
  searchParams
}: { 
  params: Promise<{ slug?: string; id?: string }>;
  searchParams: Promise<{ set?: string }>;
}) {
  try {
    const supabase = getSupabaseClient()
    const resolvedParams = await params;
    const resolvedSearchParams = await searchParams;
    const cardSlug = resolvedParams?.slug || resolvedParams?.id;

    if (!cardSlug || cardSlug === 'undefined') {
      return <div className="text-red-500 p-20 text-center font-mono bg-slate-950 min-h-screen">Invalid Card Reference ID parameters.</div>
    }

    const { data: initialCard } = await supabase
      .from('base_cards')
      .select('player_name')
      .eq('slug', cardSlug)
      .single();

    if (!initialCard) {
      return <div className="text-red-500 p-20 text-center font-mono bg-slate-950 min-h-screen">Card footprint missing.</div>
    }

    const { data: playerRootCards, error } = await supabase
      .from('base_cards')
      .select(`
        id, card_number, player_name, is_rookie, image_url, slug,
        card_sets (year, brand, series, sport),
        card_variants (
          id, variant_name, variant_category, 
          price_comps (id, sale_price, grade, sale_date, sale_image_url)
        )
      `)
      .eq('player_name', initialCard.player_name)
      .order('id', { ascending: true })

    if (error || !playerRootCards || playerRootCards.length === 0) {
      return (
        <div className="text-red-500 p-20 text-center font-mono bg-slate-950 min-h-screen">
          Card profile records missing.
        </div>
      )
    }

    const setsMap: Record<string, any> = {};
    playerRootCards.forEach((c: any) => {
      const set = Array.isArray(c.card_sets) ? c.card_sets[0] : c.card_sets;
      if (!set) return;
      const setName = `${set.year} ${set.brand} ${set.series}`;
      const setSlug = setName.toLowerCase().replace(/[^a-z0-9]+/g, '-');
      
      setsMap[setSlug] = {
        cardId: c.id,
        cardSlug: c.slug,
        name: setName,
        setInfo: set,
        cardRecord: c,
        variants: Array.isArray(c.card_variants) ? c.card_variants : []
      };
    });

    const availableSetSlugs = Object.keys(setsMap);
    
    let defaultSlug = availableSetSlugs[0];
    for (const slug of availableSetSlugs) {
      if (setsMap[slug].cardSlug === cardSlug) {
        defaultSlug = slug;
        break;
      }
    }

    const activeSetSlug = resolvedSearchParams?.set || defaultSlug;
    const activeSetData = setsMap[activeSetSlug] || setsMap[defaultSlug];

    const card = activeSetData.cardRecord;
    const setInfo = activeSetData.setInfo;
    const variantsArray = activeSetData.variants;

    const mainHeaderAffiliateUrl = generateEbayAffiliateLink(
      setInfo?.year || '', setInfo?.brand || '', setInfo?.series || '', card.player_name || ''
    );
    
    const globalCompsList = variantsArray.flatMap((variant: any) => {
      const comps = Array.isArray(variant.price_comps) ? variant.price_comps : [];
      return comps.map((comp: any) => ({
        ...comp,
        variant_name: variant.variant_name
      }));
    });

    const sortedGlobalComps = [...globalCompsList]
      .sort((a: any, b: any) => {
        const dateA = a.sale_date ? new Date(a.sale_date).getTime() : 0;
        const dateB = b.sale_date ? new Date(b.sale_date).getTime() : 0;
        return dateB - dateA;
      })
      .slice(0, 10);

    const jsonLd = {
      "@context": "https://schema.org",
      "@type": "ItemPage",
      "name": `${card.player_name} Market Comps Data Directory`,
      "description": `Historical sales data and parallel values tracking for ${card.player_name} across multiple checklists.`,
      "mainEntity": {
        "@type": "ItemList",
        "numberOfItems": availableSetSlugs.length,
        "itemListElement": availableSetSlugs.map((slug: string, idx: number) => ({
          "@type": "ListItem",
          "position": idx + 1,
          "name": setsMap[slug].name,
          "url": `https://www.cardcomphub.com/cards/${setsMap[slug].cardSlug}`
        }))
      }
    };

    // 🎯 Dynamically generate the signature URL for this specific player
    const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || 'https://placeholder.supabase.co';
    const formattedPlayerName = card.player_name ? card.player_name.toLowerCase().replace(/ /g, '_').replace(/\./g, '') : 'unknown';
    const signatureUrl = `${supabaseUrl}/storage/v1/object/public/signatures/${formattedPlayerName}.jpg`;

    return (
      <main className="min-h-screen bg-slate-950 text-slate-100 p-6 md:p-12 selection:bg-emerald-500 selection:text-slate-950">
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
        />

        <div className="max-w-5xl mx-auto">
          
          {/* BREADCRUMB */}
          <Link href="/" className="text-xs text-slate-400 hover:text-emerald-400 font-medium font-mono flex items-center gap-1 mb-8 transition-colors">
            &larr; Back to Master Directory Hub
          </Link>

          {/* 🧭 Dynamic Side-by-Side Nav Tabs */}
          {availableSetSlugs.length > 1 && (
            <div className="flex border-b border-slate-900 gap-2 overflow-x-auto mb-6 font-mono text-xs">
              {availableSetSlugs.map((slug: string) => {
                const isActive = slug === activeSetSlug;
                return (
                  <Link
                    key={slug}
                    href={`/cards/${setsMap[slug].cardSlug}`}
                    className={`px-4 py-2.5 font-bold transition-all border-b-2 whitespace-nowrap ${
                      isActive 
                        ? 'border-emerald-500 text-emerald-400 bg-emerald-500/5' 
                        : 'border-transparent text-slate-500 hover:text-slate-300'
                    }`}
                  >
                    {setsMap[slug].name}
                  </Link>
                )
              })}
            </div>
          )}

          {/* HERO PROFILE SUMMARY PANEL */}
          <div className="bg-slate-900 border border-slate-900 rounded-3xl p-6 md:p-10 flex flex-col md:flex-row gap-10 shadow-2xl relative overflow-hidden mb-10 items-start">
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(16,185,129,0.015)_0,transparent_50%)]" />
            
            {/* Locked Sticky Image Holder */}
            <div className="w-full md:w-80 flex-shrink-0 bg-slate-950/50 rounded-2xl p-6 border border-slate-800/40 flex items-center justify-center relative md:sticky md:top-8 h-fit">
              {card.image_url ? (
                <img src={card.image_url} alt={card.player_name} className="max-h-96 w-auto object-contain rounded-xl shadow-2xl relative z-10" />
              ) : (
                <div className="text-slate-700 text-xs font-mono">No Image Asset Present</div>
              )}
            </div>

            {/* Profile Core Attributes Metadata */}
            <div className="flex-1 relative z-10 flex flex-col justify-between w-full">
              <div className="border-b border-slate-800/80 pb-5 mb-6">
                <span className="inline-flex items-center gap-1.5 rounded-md bg-blue-500/10 px-2.5 py-0.5 text-xs font-medium text-blue-400 border border-blue-500/20 font-mono mb-3 uppercase tracking-wider">
                  {setInfo?.year} &bull; {setInfo?.brand} {setInfo?.series} ({setInfo?.sport || 'Unassigned'})
                </span>
                <h1 className="text-3xl font-black text-white tracking-tight sm:text-4xl flex items-center gap-3 font-sans">
                  {card.player_name}
                  {card.is_rookie && <span className="bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-xs px-2 py-0.5 rounded-md font-mono font-bold uppercase tracking-wide">Rookie Card</span>}
                </h1>
                
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mt-4">
                  <p className="text-xs text-slate-400 font-mono tracking-wide">Official Factory Checklist Reference: <span className="text-slate-200 font-bold">#{card.card_number}</span></p>
                  
                  <EbayButton 
                    url={mainHeaderAffiliateUrl}
                    playerName={card.player_name || ''}
                    cardSet={`${setInfo?.year || ''} ${setInfo?.brand || ''}`}
                  />
                </div>

                {/* 🎯 AI-Cropped Signature Block */}
                <div className="mt-6 pt-5 border-t border-slate-800/50">
                  <SignatureDisplay 
                    signatureUrl={signatureUrl} 
                    playerName={card.player_name || 'Player'} 
                  />
                </div>

              </div>

              {/* REGISTERED VARIANT BLOCKS */}
              <div>
                <h2 className="text-xs font-bold text-slate-400 uppercase font-mono tracking-widest mb-3 flex items-center gap-2">
                  <span className="h-1 w-1 bg-emerald-400 rounded-full" /> Catalog Parallel Variants Market Estimates
                </h2>
                {variantsArray.length > 0 ? (
                  <div className="space-y-3">
                    {variantsArray.map((variant: any) => {
                      const comps = Array.isArray(variant.price_comps) ? variant.price_comps : []; 
                      
                      let floorPrice = 0;
                      
                      if (comps.length > 0) {
                        const compsWithNormalizedDates = comps.map((comp: any) => {
                          const d = comp.sale_date ? new Date(comp.sale_date) : new Date(0);
                          const dateStr = !isNaN(d.getTime()) ? d.toISOString().split('T')[0] : '1970-01-01';
                          return { ...comp, dateStr };
                        }).filter((c: any) => c.dateStr !== '1970-01-01');

                        if (compsWithNormalizedDates.length > 0) {
                          const mostRecentDay = compsWithNormalizedDates.reduce((latest: string, current: any) => 
                            current.dateStr > latest ? current.dateStr : latest, 
                            compsWithNormalizedDates[0].dateStr
                          );

                          const finalDayComps = compsWithNormalizedDates.filter((c: any) => c.dateStr === mostRecentDay);
                          const validPrices = finalDayComps.map((c: any) => Number(c.sale_price)).filter((p: number) => !isNaN(p));
                          
                          if (validPrices.length > 0) {
                            floorPrice = Math.min(...validPrices);
                          }
                        }
                      }
                        
                      return (
                        <div key={variant.id} className="bg-slate-950/40 border border-slate-900 rounded-xl p-3.5 flex justify-between items-center hover:border-slate-800/80 transition-colors">
                          <div>
                            <h3 className="font-bold text-slate-200 text-xs font-sans">{variant.variant_name}</h3>
                            <p className="text-[9px] text-slate-500 font-mono uppercase tracking-wider mt-0.5">{variant.variant_category}</p>
                          </div>
                          <p className="font-black text-emerald-400 text-xs font-mono bg-emerald-950/20 border border-emerald-900/30 px-2.5 py-1 rounded-lg">
                            {floorPrice > 0 ? `$${floorPrice.toFixed(2)}` : 'No Comps'}
                          </p>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <p className="text-slate-500 italic font-mono text-xs">No active parallel variant tiers linked to this profile.</p>
                )}
              </div>

            </div>
          </div>

         {/* 📊 HISTORICAL PRICE TRENDS SECTION */}
<section className="mt-10 mb-6">
  {/* 🚀 FIXED: Pass the data array instead of the cardId */}
  <PriceTrendsChart data={globalCompsList} />
</section>
          {/* 🛍️ RESTORED: Amazon Affiliate Supplies Banner Insertion Point */}
          <AmazonSuppliesBanner />

          {/* HISTORICAL RECENT SALES GRID */}
          <section id="historical-sales-comps" className="mt-12">
            <div className="border-b border-slate-900 pb-3 mb-6">
              <h2 className="text-base font-bold text-white tracking-tight flex items-center gap-2">
                <span className="h-1.5 w-1.5 rounded-full bg-blue-500" /> Historic Real-Time Market Comps Log
                <span className="text-xxs text-slate-500 font-mono font-normal normal-case ml-2">(Optimized: showing 10 most recent transactions)</span>
              </h2>
            </div>

            {sortedGlobalComps.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {sortedGlobalComps.map((comp: any) => {
                  const targetImageSource = comp.sale_image_url || card.image_url || '';
                  
                  return (
                    <div 
                      key={comp.id} 
                      className="bg-slate-900/40 border border-slate-900 rounded-xl p-3 flex items-center gap-4 font-mono text-xs hover:bg-slate-900/60 transition-colors"
                    >
                      {targetImageSource && (
                        <ZoomableThumbnail 
                          src={targetImageSource} 
                          alt={`${setInfo?.year || ''} ${setInfo?.brand || ''} ${card.player_name || ''} ${comp.variant_name} (${comp.grade || 'RAW'})`} 
                        />
                      )}

                      <div className="flex-1 min-w-0 space-y-1">
                        <span className="inline-flex px-1.5 py-0.5 rounded bg-slate-950 text-slate-400 text-[9px] font-bold uppercase tracking-wider border border-slate-900">
                          {comp.variant_name}
                        </span>
                        <h4 className="font-sans font-bold text-slate-200 text-sm mt-1 truncate">
                          {setInfo?.year} {setInfo?.brand} {card.player_name}
                        </h4>
                        <p className="text-[10px] text-slate-500">
                          Settled on: <span className="text-slate-400 font-bold">
                            {comp.sale_date ? comp.sale_date.split('T')[0] : 'N/A'}
                          </span>
                        </p>
                      </div>

                      <div className="text-right space-y-1 flex-shrink-0">
                        <p className="text-sm font-black text-emerald-400">${(Number(comp.sale_price) || 0).toFixed(2)}</p>
                        <span className={`inline-block text-[9px] font-black px-1.5 py-0.2 rounded ${
                          comp.grade === 'RAW' ? 'bg-slate-800 text-slate-300 border border-slate-700/50' : 'bg-blue-950 text-blue-400 border border-blue-900/40'
                        }`}>
                          {comp.grade || 'RAW'}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="text-center py-12 border border-dashed border-slate-900 rounded-2xl bg-slate-900/10">
                <p className="text-xs text-slate-500 font-mono">
                  No individual completed sales entries are currently indexed for this player checklist sequence. Market sweeps occur nightly.
                </p>
              </div>
            )}
          </section>

        </div>
      </main>
    )
  } catch (runtimeError: any) {
    return (
      <div className="bg-slate-950 text-slate-200 p-20 min-h-screen font-mono text-xs">
        <h1 className="text-red-500 font-black text-sm uppercase tracking-wider mb-2">🚨 Isolated Component Runtime Interception</h1>
        <p className="bg-red-950/20 border border-red-900/50 p-4 rounded-xl text-red-300 max-w-xl">
          {runtimeError?.message || 'An unknown execution error triggered a local crash.'}
        </p>
      </div>
    )
  }
}