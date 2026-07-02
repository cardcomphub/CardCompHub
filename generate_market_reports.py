import os
import json
import re
from datetime import datetime, timezone, timedelta
from supabase import create_client, Client
from openai import OpenAI

# 🔐 WORKER AUTHENTICATION
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

if not all([SUPABASE_URL, SUPABASE_KEY, OPENAI_API_KEY]):
    raise ValueError("❌ Execution failed: Missing required environment variables.")

# 🔌 Initialize Clients
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
ai_client = OpenAI(api_key=OPENAI_API_KEY)

def generate_slug(title):
    # Strip special characters and replace spaces with hyphens for perfect SEO URLs
    clean_title = re.sub(r'[^a-zA-Z0-9\s-]', '', title).strip().lower()
    return re.sub(r'[\s-]+', '-', clean_title)

def fetch_market_movers():
    print("📊 Pulling latest market data from Supabase Materialized View...")
    
    # Grab the top 3 highest percentage gainers (Minimum $5 floor and 5 recent sales to filter out junk)
    gainers_response = supabase.table("hottest_players_leaderboard") \
        .select("player_name, current_floor, past_floor, percentage_change, recent_sales_volume, series, brand, year") \
        .gte("current_floor", 5) \
        .gte("recent_sales_volume", 5) \
        .order("percentage_change", desc=True) \
        .limit(3) \
        .execute()

    # Grab the top 3 biggest losers
    losers_response = supabase.table("hottest_players_leaderboard") \
        .select("player_name, current_floor, past_floor, percentage_change, recent_sales_volume, series, brand, year") \
        .gte("past_floor", 10) \
        .gte("recent_sales_volume", 5) \
        .order("percentage_change", desc=False) \
        .limit(3) \
        .execute()

    return gainers_response.data, losers_response.data

def generate_article(gainers, losers):
    print("🧠 Handing data to OpenAI for Markdown generation...")
    
    date_str = datetime.now(timezone.utc).strftime("%B %d, %Y")
    
    # Convert database arrays into formatted text for the prompt
    gainers_text = json.dumps(gainers, indent=2)
    losers_text = json.dumps(losers, indent=2)

    prompt = f"""
    You are an elite sports card market analyst writing for CardCompHub. Write a highly engaging, SEO-optimized weekly market report in Markdown format.
    
    Use the following real market data from our tracking engine.
    
    Top Gainers:
    {gainers_text}
    
    Biggest Losers:
    {losers_text}
    
    Formatting Rules:
    - Return a JSON object with exactly three keys: "title", "meta_description", and "content".
    - "title" should be a catchy, SEO-friendly headline (e.g., "Market Watch: [Player Name] Surges 105% while [Player Name] Plummets").
    - "meta_description" should be under 160 characters.
    - "content" must be beautifully formatted Markdown. Use ## headers for each player, bold their exact price movements, and analyze why their market is moving (mention their team, recent real-world performance, or hobby hype).
    - Maintain a professional, analytical, yet hype-driven tone.
    """

    response = ai_client.chat.completions.create(
        model="gpt-4o",
        response_format={ "type": "json_object" },
        messages=[
            {"role": "system", "content": "You output strict JSON combining SEO metadata and Markdown article content."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7
    )

    # Parse the returned JSON payload
    raw_content = response.choices[0].message.content
    return json.loads(raw_content)

def publish_to_supabase(article_data):
    print("🚀 Publishing article to Supabase...")
    
    title = article_data.get("title")
    slug = f"{generate_slug(title)}-{datetime.now(timezone.utc).strftime('%m-%d-%y')}"
    
    payload = {
        "title": title,
        "slug": slug,
        "content": article_data.get("content"),
        "meta_description": article_data.get("meta_description"),
        "is_published": True
    }
    
    # Insert straight into your blog table
    supabase.table("blog_posts").insert(payload).execute()
    print(f"✅ Successfully published: {title}")
    print(f"🔗 URL Slug: /{slug}")

if __name__ == "__main__":
    try:
        gainers, losers = fetch_market_movers()
        
        if not gainers or not losers:
            print("⏩ Not enough active market data to generate a report today. Skipping.")
            sys.exit(0)
            
        article = generate_article(gainers, losers)
        publish_to_supabase(article)
        
    except Exception as e:
        print(f"❌ Pipeline failed: {e}")
