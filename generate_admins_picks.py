import os
import json
import sys
from datetime import datetime, timezone
from supabase import create_client, Client
from openai import OpenAI
import re

# 🔐 WORKER AUTHENTICATION
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

if not all([SUPABASE_URL, SUPABASE_KEY, OPENAI_API_KEY]):
    raise ValueError("❌ Execution failed: Missing required environment variables.")

# 🔌 Initialize Clients
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
ai_client = OpenAI(api_key=OPENAI_API_KEY)

# 🎯 ADMIN SELECTION CONFIGURATION (UPGRADED)
ADMIN_CHOSEN_CARDS = [
    {
        "slug": "2025-topps-chrome-shadow-etch-josh-allen-se2?set=2025-topps-chrome-shadow-etch",
        "variant": "Gold Refractor" 
    },
    {
        "slug": "2025-topps-cosmic-chrome-stars-in-the-night-cam-ward-stn1?set=2025-topps-cosmic-chrome-football-stars-in-the-night",
        "variant": "Base"
    },
    {
        "slug": "2025-topps-cosmic-chrome-stars-in-the-night-jaxson-dart-stn2?set=2025-topps-cosmic-chrome-football-stars-in-the-night",
        "variant": "Base"
    },
    {
        "slug": "2025-topps-chrome-xs-and-whoas-dylan-harper-xw9",
        "variant": "Base"
    },
    {
        "slug": "2026-topps-series-1-1991-topps-baseball-autographs-jacob-misiorowski-91amis",
        "variant": "Base" # Corrected to "Base" to find the autograph tier properly
    }
]

def generate_slug(title):
    clean_title = re.sub(r'[^a-zA-Z0-9\s-]', '', title).strip().lower()
    return re.sub(r'[\s-]+', '-', clean_title)

def fetch_specific_variants(cards_config):
    print(r"🔎 Querying database for specific Card Variants...")
    detailed_picks = []

    for item in cards_config:
        target_slug = item['slug']
        target_variant = item['variant']

        # 1. Fetch base card, set info, and filter down to the specific variant ID
        card_response = supabase.table("base_cards").select(
            "player_name, image_url, slug, card_sets(year, brand, series), card_variants!inner(id, variant_name)"
        ).eq("slug", target_slug).ilike("card_variants.variant_name", f"%{target_variant}%").execute()

        if not card_response.data:
            print(f"⚠️ SKIP: Could not find variant '{target_variant}' for slug '{target_slug}'.")
            continue

        card_data = card_response.data[0]
        variant_id = card_data['card_variants'][0]['id']
        actual_variant_name = card_data['card_variants'][0]['variant_name']

        # 2. Fetch the 10 most recent sales for this exact variant to give the AI context
        comps_response = supabase.table("price_comps").select(
            "sale_price, sale_date"
        ).eq("variant_id", variant_id).order("sale_date", desc=True).limit(10).execute()

        # Calculate a quick rolling average of the last 3 sales for the floor
        recent_sales = [float(comp['sale_price']) for comp in (comps_response.data or [])]
        current_floor = sum(recent_sales[:3]) / 3 if len(recent_sales) >= 3 else (recent_sales[0] if recent_sales else 0)
        
        detailed_picks.append({
            "player_name": card_data['player_name'],
            "set_info": f"{card_data['card_sets']['year']} {card_data['card_sets']['brand']} {card_data['card_sets']['series']}",
            "specific_variant_analyzed": actual_variant_name,
            "image_url": card_data['image_url'],
            "recent_sales_history": comps_response.data,
            "estimated_current_floor": round(current_floor, 2)
        })

    return detailed_picks

def generate_editorial_article(picks_data):
    print("🧠 Drafting expert hobby review via OpenAI...")
    
    current_date_str = datetime.now(timezone.utc).strftime("%B %d, %Y")
    data_payload = json.dumps(picks_data, indent=2)

    prompt = f"""
    You are an expert sports card curator and long-time hobbyist writing an exclusive "Admin's Picks" showcase article for CardCompHub.
    Your writing must sound authentic, technical, and deeply embedded in the trading card culture.
    
    Current Date: {current_date_str}
    
    Target Variant Data & Recent Sales History:
    {data_payload}
    
    Strict Content Requirements for Each Card:
    1. EXACT VARIANT FOCUS: You must explicitly mention the exact parallel/variant being analyzed and the set/series/brand/year that it is in (e.g., "Silver Prizm", "Red Refractor"). Do not talk about the card generically.
    2. IMAGE EMBEDDING (CRITICAL): Immediately beneath the `##` header for each card, you MUST insert the card's image using standard Markdown syntax. Example: `![Player Name - Variant](image_url)`. The exact `image_url` is provided in the JSON data.
    3. VELOCITY & PRICING: Use the provided `recent_sales_history` array to describe the card's liquidity. Did it sell multiple times this week? Is the `estimated_current_floor` holding steady based on the transaction dates?
    4. THE VISUAL AESTHETIC: Describe the concrete physical design of this specific set/variant (e.g., Chromium finish, color matching to team jerseys, print lines, centering tolerances). But also include the coolness of this card. You are reviewing this card because I think they are very good looking and aesthetic.
    5. TEMPORAL ANCHORING: Weave the current date ({current_date_str}) into the narrative to ground the market analysis.

    Output Format:
    Return a JSON object containing exactly three keys: "title", "meta_description", and "content".
    
    Formatting Rules:
    - "title": An engaging, premium headline featuring the targeted players/variants.
    - "meta_description": A crisp SEO snippet under 160 characters.
    - "content": Clean Markdown text. Use ## headers for each card, bold exact price points, embed the image below the header, and write detailed, narrative paragraphs.
    """

    response = ai_client.chat.completions.create(
        model="gpt-4o",
        response_format={ "type": "json_object" },
        messages=[
            {"role": "system", "content": "You output professional sports card portfolio analysis wrapped in strict JSON format."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.75
    )

    raw_content = response.choices[0].message.content
    return json.loads(raw_content)

def publish_to_supabase(article_data, picks_data):
    print("🚀 Uploading Admin Picks article to production table...")
    
    title = article_data.get("title")
    slug = f"admins-picks-{generate_slug(title)}-{datetime.now(timezone.utc).strftime('%m-%d-%y')}"
    
    # Feature Image: Uses the image of the first card successfully found in the list
    feature_image_url = None
    if picks_data and len(picks_data) > 0:
        feature_image_url = picks_data[0].get("image_url")

    payload = {
        "title": title,
        "slug": slug,
        "content": article_data.get("content"),
        "meta_description": article_data.get("meta_description"),
        "feature_image": feature_image_url, 
        "is_published": True
    }
    
    supabase.table("blog_posts").insert(payload).execute()
    print(f"✅ SUCCESS: Editorial published!")
    print(f"🔗 URL Slug: /blog/{slug}")

if __name__ == "__main__":
    if not ADMIN_CHOSEN_CARDS:
        print("⏩ No cards configured inside ADMIN_CHOSEN_CARDS. Exiting pipeline.")
        sys.exit(0)
        
    try:
        picks_data = fetch_specific_variants(ADMIN_CHOSEN_CARDS)
        
        if not picks_data:
            print("❌ Error: Could not find any matching database rows for the provided slugs and variants.")
            sys.exit(1)
            
        article = generate_editorial_article(picks_data)
        publish_to_supabase(article, picks_data)
        
    except Exception as e:
        print(f"❌ Failed to run Admin Picks pipeline: {e}")
