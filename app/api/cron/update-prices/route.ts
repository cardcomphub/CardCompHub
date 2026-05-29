import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';

export const dynamic = 'force-dynamic';

const getSupabaseClient = () => {
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || '';
  const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || '';
  return createClient(supabaseUrl, supabaseAnonKey);
};

export async function GET(request: NextRequest) {
  // 1. Restore standard CRON security verification block
  const authHeader = request.headers.get('authorization');
  if (authHeader !== `Bearer ${process.env.CRON_SECRET}`) {
    return new NextResponse('Unauthorized Pipeline Access Attempt', { status: 401 });
  }

  const supabase = getSupabaseClient();
  const apifyToken = process.env.APIFY_TOKEN;

  if (!apifyToken) {
    return NextResponse.json({ success: false, error: 'Apify system token not configured on server settings.' }, { status: 500 });
  }

  try {
    // 2. Gather active master card checklist rows
    const { data: cards, error: cardError } = await supabase
      .from('base_cards')
      .select(`
        id, player_name, card_number,
        card_sets (year, brand, series)
      `);

    if (cardError || !cards) throw new Error('Could not pull base profile checklist');

    // 3. Process card loops cleanly
    for (const card of cards) {
      const setInfo = Array.isArray(card.card_sets) ? card.card_sets[0] : card.card_sets;
      if (!setInfo) continue;

      const targetQuery = `${setInfo.year} ${setInfo.brand} ${card.player_name} #${card.card_number}`;
      
      const { data: variants } = await supabase
        .from('card_variants')
        .select('id, variant_name')
        .eq('base_card_id', card.id);

      const baseVariant = variants?.find(v => v.variant_name === 'Base');
      if (!baseVariant) continue;

      // Spin up the Apify task worker node
      const apifyRunResponse = await fetch(
        `https://api.apify.com/v2/actor-tasks/automation-lab~ebay-sold-scraper/runs?token=${apifyToken}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            query: targetQuery,
            maxItems: 5,
            ebaySite: "ebay.com",
            sortBy: "date_desc"
          })
        }
      );

      const runData = await apifyRunResponse.json();
      const defaultDatasetId = runData?.data?.defaultDatasetId;

      if (!defaultDatasetId) continue;

      // Wait interval delay
      await new Promise((resolve) => setTimeout(resolve, 8000));

      // Stream the dataset items down
      const datasetResponse = await fetch(
        `https://api.apify.com/v2/datasets/${defaultDatasetId}/items?token=${apifyToken}`
      );
      const scrapedComps = await datasetResponse.json();

      if (!Array.isArray(scrapedComps) || scrapedComps.length === 0) continue;

      for (const item of scrapedComps) {
        const finalPrice = parseFloat(item.soldPrice) || 0;
        if (finalPrice === 0) continue;

        const titleLower = item.title?.toLowerCase() || '';
        let resolvedGrade = 'RAW';
        if (titleLower.includes('psa 10')) resolvedGrade = 'PSA 10';
        else if (titleLower.includes('psa 9')) resolvedGrade = 'PSA 9';

        await supabase.from('price_comps').insert({
          card_variant_id: baseVariant.id,
          sale_price: finalPrice,
          grade: resolvedGrade,
          sale_date: item.soldDate ? new Date(item.soldDate).toISOString().split('T')[0] : new Date().toISOString().split('T')[0]
        });
      }
    }

    return NextResponse.json({ success: true, processed: cards.length });

  } catch (error: any) {
    console.error('Fatal automated price update crash:', error);
    return NextResponse.json({ success: false, error: error.message }, { status: 500 });
  }
}