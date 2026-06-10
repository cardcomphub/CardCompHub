import { MetadataRoute } from 'next'
import { createClient } from '@supabase/supabase-js'

const getSupabaseClient = () => {
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || 'https://placeholder.supabase.co'
  const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || 'placeholder'
  return createClient(supabaseUrl, supabaseAnonKey)
}

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const supabase = getSupabaseClient()
  const baseUrl = 'https://www.cardcomphub.com'

  // 1️⃣ FETCH UPGRADE: Explicitly grab the 'slug' field instead of the 'id'
  const { data: cards, error } = await supabase
    .from('base_cards')
    .select('slug')

  if (error) {
    console.error('Sitemap compilation database interruption:', error)
  }

  // 2️⃣ MAP UPGRADE: Loop over the records using the text slug keys
  const cardUrls = (cards || []).map((card) => ({
    url: `${baseUrl}/cards/${card.slug}`,
    lastModified: new Date(),
    changeFrequency: 'weekly' as const,
    priority: 0.8,
  }))

  // 3️⃣ Combine your static home directory layout with your dynamic player pages
  return [
    {
      url: baseUrl,
      lastModified: new Date(),
      changeFrequency: 'daily',
      priority: 1,
    },
    ...cardUrls,
  ]
}