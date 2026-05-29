interface CardSightSearchResult {
  id: string;
  type: string;
  name?: string;
}

// 🌐 CENTRALIZED API ENDPOINT ROUTING
const CARDSIGHT_BASE = "https://api.cardsight.ai/v1"; // 🛠️ FIXED: Re-added versioning scope required for catalog services

/**
 * Executes a network fetch to CardSight AI with a safety timeout guard.
 */
async function queryCardSightSearch(searchString: string, apiKey: string): Promise<any> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 4000);

  const url = `${CARDSIGHT_BASE}/catalog/search?q=${encodeURIComponent(searchString)}&type=card&take=1`;
  
  try {
    const response = await fetch(url, {
      method: "GET",
      headers: {
        "X-API-Key": apiKey,
        "Accept": "application/json"
      },
      signal: controller.signal
    });

    clearTimeout(timeoutId);
    return response.ok ? await response.json() : null;
  } catch (err) {
    clearTimeout(timeoutId);
    return null;
  }
}

/**
 * Searches CardSight to locate an entity ID using a multi-pass text strategy.
 */
export async function fetchCanonicalCardImage(
  year: number | null,
  brand: string,
  playerName: string,
  cardNumber: string
): Promise<string | null> {
  const apiKey = process.env.CARDSIGHT_API_KEY;
  
  if (!apiKey) {
    console.warn("⚠️ CardSight AI API key is missing. Skipping external image fallback sequence.");
    return null;
  }

  const cleanPlayer = playerName.trim();
  const cleanCardNum = cardNumber.trim().replace('#', '');
  const cleanBrand = brand.trim().replace(/^PANINI\s+|^TOPPS\s+/i, '');

  try {
    let routerPayload = null;

    // ==========================================================
    // PASS 1: COMPLETE CONCATENATED SEARCH STRING
    // ==========================================================
    const searchString1 = `${year || ''} ${brand.trim()} ${cleanPlayer} ${cleanCardNum}`.trim();
    console.log(`🔍 CardSight Pass 1: Querying "${searchString1}"`);
    routerPayload = await queryCardSightSearch(searchString1, apiKey);

    // ==========================================================
    // PASS 2: STRIPPED CLEAN BRAND FALLBACK
    // ==========================================================
    let itemsList: CardSightSearchResult[] = routerPayload?.results || routerPayload?.data?.results || [];
    let targetCard = itemsList.find(item => item.type === 'card' || !item.type);

    if (!targetCard) {
      const searchString2 = `${year || ''} ${cleanBrand} ${cleanPlayer} ${cleanCardNum}`.trim();
      console.log(`⚠️ Pass 1 missed. CardSight Pass 2: Querying "${searchString2}"`);
      routerPayload = await queryCardSightSearch(searchString2, apiKey);
      itemsList = routerPayload?.results || routerPayload?.data?.results || [];
      targetCard = itemsList.find(item => item.type === 'card' || !item.type);
    }

    // ==========================================================
    // PASS 3: RAW IDENTITY MATCH (PLAYER + CARD NUMBER ONLY)
    // ==========================================================
    if (!targetCard) {
      const searchString3 = `${cleanPlayer} ${cleanCardNum}`.trim();
      console.log(`🚨 Pass 2 missed. CardSight Pass 3 (Core Profile Match): Querying "${searchString3}"`);
      routerPayload = await queryCardSightSearch(searchString3, apiKey);
      itemsList = routerPayload?.results || routerPayload?.data?.results || [];
      targetCard = itemsList.find(item => item.type === 'card' || !item.type);
    }

    if (!targetCard || !targetCard.id) {
      console.log(`❌ All catalog search variations exhausted. No entity resolved.`);
      return null;
    }

    const cardUuid = targetCard.id;
    console.log(`🎯 Success: Resolved Card ID ➔ ${cardUuid}`);

    // ==========================================================
    // STEP 2: PROFILE DISCOVERY TO GRAB MEDIA LINKS
    // ==========================================================
    const profileUrl = `${CARDSIGHT_BASE}/catalog/cards/${cardUuid}`;
    const pController = new AbortController();
    const pTimeout = setTimeout(() => pController.abort(), 4000);

    const profileResponse = await fetch(profileUrl, {
      method: "GET",
      headers: { "X-API-Key": apiKey, "Accept": "application/json" },
      signal: pController.signal
    });
    
    clearTimeout(pTimeout);

    if (profileResponse.ok) {
      const cardProfile = await profileResponse.json();
      
      // Handle the data mappings returned inside their unified card profiles
      const imageAsset = cardProfile?.image_url || 
                         cardProfile?.data?.image_url || 
                         cardProfile?.imageUrl || 
                         cardProfile?.reference_image || 
                         cardProfile?.data?.reference_image || 
                         cardProfile?.card?.image_url ||
                         null;
                         
      if (imageAsset) {
        console.log(`✨ Success! Secure image link established: ${imageAsset}`);
        return imageAsset;
      }
    }

    console.log(`❌ No image paths populated inside the asset profile for ID: ${cardUuid}`);
    return null;

  } catch (error) {
    console.error("🚨 CardSight pipeline failed:", error);
    return null;
  }
}