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
  { params }: { params: Promise<{ id?: string; slug?: string }> }
) {
  try {
    const resolvedParams = await params
    // 🌟 FALLBACK: Captures either the string slug key or traditional UUID index parameter cleanly
    const cardIdentifier = resolvedParams?.id || resolvedParams?.slug
    
    if (!cardIdentifier || cardIdentifier === 'undefined') {
      return NextResponse.json({ trends: [] }, { status: 400 })
    }
    
    const { searchParams } = new URL(request.url)
    const range = searchParams.get('range') || 'month' 

    const supabase = await getSupabaseClient()

    // 🌟 FLEXIBLE LOOKUP: Detects if the url param is an asset slug or database row ID token
    let dbQuery = supabase.from('base_cards').select(`
      id,
      card_variants (
        id,
        price_comps (id, sale_price, sale_date)
      )
    `)

    if (cardIdentifier.includes('-') && !/^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$/.test(cardIdentifier)) {
      dbQuery = dbQuery.eq('slug', cardIdentifier)
    } else {
      dbQuery = dbQuery.eq('id', cardIdentifier)
    }

    const { data: card, error } = await dbQuery.single()

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

    // Sanitize date string structure and filter records
    const filteredComps = globalCompsList.filter((comp: any) => {
      if (!comp.sale_date) return false
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

    // 🎯 RECONCILED SEGMENTATION: Keep tracking only the absolute lowest price point per day label
    const trendMap = new Map<string, number>()

    filteredComps.forEach((comp: any) => {
      const dateObj = new Date(comp.sale_date.replace(' ', 'T'))
      const label = dateObj.toLocaleDateString('en-US', formatOptions)
      
      const currentPrice = Number(comp.sale_price) || 0
      
      if (currentPrice > 0) {
        const existingLowestPrice = trendMap.get(label)
        // If the day hasn't been added yet, or this sale is lower than what we recorded, overwrite it
        if (existingLowestPrice === undefined || currentPrice < existingLowestPrice) {
          trendMap.set(label, currentPrice)
        }
      }
    })

    // Convert map straight to the clean coordinate sequence payload Recharts expects
    const structuredTrends = Array.from(trendMap.entries()).map(([dateLabel, lowestPrice]) => ({
      dateLabel,
      price: lowestPrice
    }))

    console.log(`📈 Floor Trends Pipeline: Processed ${structuredTrends.length} unique daily markers for chart canvas.`)
    return NextResponse.json({ trends: structuredTrends }, { status: 200 })

  } catch (error: any) {
    console.error("🚨 Price trend calculation exception:", error)
    return NextResponse.json({ error: "Failed to compile market charts." }, { status: 500 })
  }
}