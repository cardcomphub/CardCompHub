import { NextRequest, NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'

async function getSupabaseClient() {
  const { createClient } = await import('@supabase/supabase-js')
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL
  const secretKey = process.env.SUPABASE_SERVICE_ROLE_KEY || 
                    process.env.SUPABASE_ANON_KEY || 
                    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY

  if (!url || !secretKey) {
    throw new Error("Missing Supabase environment variables at request runtime.")
  }
  return createClient(url, secretKey)
}

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const resolvedParams = await params
    const { id } = resolvedParams
    
    const { searchParams } = new URL(request.url)
    const range = searchParams.get('range') || 'month' 

    const supabase = await getSupabaseClient()

    // Fetch the raw nested records matching your working layout path
    const { data: card, error } = await supabase
      .from('base_cards')
      .select(`
        id,
        card_variants (
          id,
          price_comps (id, sale_price, sale_date)
        )
      `)
      .eq('id', id)
      .single()

    if (error || !card) {
      return NextResponse.json({ trends: [] })
    }

    const variantsArray = Array.isArray(card.card_variants) ? card.card_variants : []
    const globalCompsList = variantsArray.flatMap((variant: any) => {
      return Array.isArray(variant.price_comps) ? variant.price_comps : []
    })

    // Calculate timeframe boundaries
    const now = new Date()
    let startDate = new Date()
    if (range === 'week') startDate.setDate(now.getDate() - 7)
    else if (range === 'year') startDate.setFullYear(now.getFullYear() - 1)
    else startDate.setDate(now.getDate() - 30)

    // 🛠️ FIXED: Sanitize date string structure and filter records
    const filteredComps = globalCompsList.filter((comp: any) => {
      if (!comp.sale_date) return false
      // Replace the PostgreSQL space with a clean 'T' for bulletproof JS Date parsing
      const formattedDateStr = comp.sale_date.replace(' ', 'T')
      const saleDate = new Date(formattedDateStr)
      return saleDate.getTime() >= startDate.getTime()
    })

    // Sort chronologically (oldest to newest) for left-to-right tracking lines
    filteredComps.sort((a: any, b: any) => {
      return new Date(a.sale_date.replace(' ', 'T')).getTime() - new Date(b.sale_date.replace(' ', 'T')).getTime()
    })

    const formatOptions: Intl.DateTimeFormatOptions = 
      range === 'week' ? { weekday: 'short' } : 
      range === 'year' ? { month: 'short' } : 
      { month: 'short', day: 'numeric' }

    // 🛠️ FIXED: Roll up multiple sales on the same day into a single clean point average
    const trendMap = new Map<string, { total: number; count: number }>()

    filteredComps.forEach((comp: any) => {
      const dateObj = new Date(comp.sale_date.replace(' ', 'T'))
      const label = dateObj.toLocaleDateString('en-US', formatOptions)
      
      const current = trendMap.get(label) || { total: 0, count: 0 }
      trendMap.set(label, {
        total: current.total + (Number(comp.sale_price) || 0),
        count: current.count + 1
      })
    })

    // Convert map to the clean object sequence format Recharts expects
    const structuredTrends = Array.from(trendMap.entries()).map(([dateLabel, data]) => ({
      dateLabel,
      price: Number((data.total / data.count).toFixed(2))
    }))

    console.log(`📈 Trends Pipeline: Processed ${structuredTrends.length} unique daily markers for chart canvas.`)
    return NextResponse.json({ trends: structuredTrends }, { status: 200 })

  } catch (error: any) {
    console.error("🚨 Price trend calculation exception:", error)
    return NextResponse.json({ error: "Failed to compile market charts." }, { status: 500 })
  }
}