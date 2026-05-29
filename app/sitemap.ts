import { MetadataRoute } from 'next'
import { createClient } from '@supabase/supabase-js'

// 1. FORCE RUNTIME GENERATION: Tells Next.js to fetch these routes dynamically on demand
export const dynamic = 'force-dynamic';

// 2. LAZY CLIENT ENGINE: Bypasses build-time sandbox crashes
const getSupabaseClient = () => {
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || 'https://placeholder.supabase.co'
  const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || 'placeholder'
  return createClient(supabaseUrl, supabaseAnonKey)
}

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const baseUrl = 'https://cardcomphub.com'

  // Standard static page baseline
  const staticPages: MetadataRoute.Sitemap = [
    {
      url: baseUrl,
      lastModified: new Date(),
      changeFrequency: 'daily',
      priority: 1.0,
    },
  ]

  try {
    const supabase = getSupabaseClient()

    // Fetch card record payloads from your database footprint
    const { data: cards, error } = await supabase
      .from('base_cards')
      .select('id')

    if (error || !cards) {
      console.error('Supabase error fetching sitemap payloads:', error)
      return staticPages // Fallback safely to homepage if query fails
    }

    // Programmatically map out your dynamic card endpoints
    const dynamicCardPages = cards.map((card) => ({
      url: `${baseUrl}/cards/${card.id}`,
      lastModified: new Date(),
      changeFrequency: 'weekly' as const,
      priority: 0.8,
    }))

    // Combine into a singular search index matrix
    return [...staticPages, ...dynamicCardPages]

  } catch (err) {
    console.error('Fatal catch boundary caught in sitemap engine:', err)
    return staticPages // Guarantee Google never receives a hard 404
  }
}