// 🌐 EBAY API CONFIGURATION
const EBAY_AUTH_URL = "https://api.ebay.com/identity/v1/oauth2/token";
const EBAY_SEARCH_URL = "https://api.ebay.com/buy/browse/v1/item_summary/search";

/**
 * Fetches a short-lived App-Only Access Token from eBay using Client Credentials.
 */
async function getEbayAccessToken(): Promise<string | null> {
  const clientId = process.env.EBAY_CLIENT_ID;
  const clientSecret = process.env.EBAY_CLIENT_SECRET;

  if (!clientId || !clientSecret) {
    console.warn("⚠️ eBay Client ID or Secret missing in environment variables.");
    return null;
  }

  try {
    // Basic Auth header requires Base64 encoding of client_id:client_secret
    const authHeader = Buffer.from(`${clientId}:${clientSecret}`).toString('base64');

    const response = await fetch(EBAY_AUTH_URL, {
      method: "POST",
      headers: {
        "Authorization": `Basic ${authHeader}`,
        "Content-Type": "application/x-www-form-urlencoded"
      },
      body: new URLSearchParams({
        grant_type: "client_credentials",
        // The Browse API requires this specific public data scope
        scope: "https://api.ebay.com/oauth/api_scope"
      })
    });

    if (!response.ok) {
      console.error(`🚨 eBay Auth token request failed with status: ${response.status}`);
      return null;
    }

    const data = await response.json();
    return data.access_token || null;
  } catch (error) {
    console.error("🚨 Failed to retrieve eBay access token:", error);
    return null;
  }
}

/**
 * Searches eBay for a matching sports card and extracts the top listing's image.
 */
export async function fetchEbayCardImage(
  year: number | null,
  brand: string,
  playerName: string,
  cardNumber: string
): Promise<string | null> {
  try {
    const token = await getEbayAccessToken();
    if (!token) return null;

    // Clean up incoming fields for an optimal eBay search string
    const cleanPlayer = playerName.trim();
    const cleanCardNum = cardNumber.trim().replace('#', '');
    const cleanBrand = brand.trim().replace(/^PANINI\s+|^TOPPS\s+/i, '');

    // Construct a high-intent query string (e.g., "2023 Hoops Victor Wembanyama 277")
    const searchString = `${year || ''} ${cleanBrand} ${cleanPlayer} ${cleanCardNum}`.trim();
    console.log(`🔍 eBay API: Querying live listings for "${searchString}"`);

    const url = `${EBAY_SEARCH_URL}?q=${encodeURIComponent(searchString)}&limit=1`;

    const response = await fetch(url, {
      method: "GET",
      headers: {
        "Authorization": `Bearer ${token}`,
        "Content-Type": "application/json",
        "X-EBAY-C-MARKETPLACE-ID": "EBAY_US" // Focus on US Card Market
      }
    });

    if (!response.ok) {
      console.error(`🚨 eBay Search API responded with status error: ${response.status}`);
      return null;
    }

    const payload = await response.json();
    const items = payload?.itemSummaries || [];

    if (items.length > 0) {
      // Pull the high-res primary image, falling back to standard thumbnail if missing
      const targetImage = items[0].image?.imageUrl || items[0].thumbnailImages?.[0]?.imageUrl || null;
      
      if (targetImage) {
        console.log(`✨ eBay match secured: ${targetImage}`);
        return targetImage;
      }
    }

    console.log(`🔍 eBay returned 0 active listings for: "${searchString}"`);
    return null;
  } catch (error) {
    console.error("🚨 eBay image lookup operation failed:", error);
    return null;
  }
}