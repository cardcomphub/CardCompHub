import os
import json
import re
import sys
from datetime import datetime, timezone
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

def fetch_hottest_movers():
    print("📊 Pulling top trending market assets from Hottest Players Leaderboard...")
    
    # Fetch the top 5 absolute movers based on your custom hype_score engine
    response = supabase.table("hottest_players_leaderboard") \
        .select("player_name, current_floor, past_floor, percentage_change, recent_sales_volume, hype_score, series, brand, year, image_url") \
        .order("hype_score", desc=True) \
        .limit(5) \
        .execute()

    return response.data

def generate_article(movers_data):
    print("🧠 Processing metrics and generating dated Markdown report via OpenAI...")
    
    # Capture the exact execution date to anchor the AI's temporal writing
    current_date_str = datetime.now(timezone.utc).strftime("%B %d, %Y")
    movers_payload = json.dumps(movers_data, indent=2)

    prompt = f"""
    You are an elite sports card market macro-analyst writing for CardCompHub. 
    Write a comprehensive, deeply analytical weekly market report in Markdown format.
    
    Current Report Date: {current_date_str}
    
    Top Leaderboard Movers Data:
    {movers_payload}
    
    Strict Editorial Guidelines:
    1. INCORPORATE DATES: You must explicitly include calendar dates and temporal context directly into your prose (e.g., "During the week ending {current_date_str}...", "Comparing late-month transaction data to prior baselines...", "As of {current_date_str}..."). Do not let the data float without temporal anchors.
    2. VARIANT SKEW AWARENESS: Note that past astronomical percentage spikes (e.g., thousands of percent) were often tracking noise caused by high-end autographed parallels or low-pop serial-numbered variants mixed into base card transaction data. This report evaluates newly stabilized, apples-to-apples baseline floor prices.
    3. JSON STRUCTURE: Return a JSON object containing exactly three keys: "title", "meta_description", and "content".
    
    Formatting Rules:
    - "title": A sharp, highly clickable SEO headline focusing on the week's dominant market trends.
    - "meta_description": Under 160 characters for clean Google snippet rendering.
    - "content": Clean Markdown. Use ## headers for each prominent athlete, bold their precise price movements, and give context behind their volume adjustments.
    """

    response = ai_client.chat.completions.create(
        model="gpt-4o",
        response_format={ "type": "json_object" },
        messages=[
            {"role": "system", "content": "You output strict JSON schema combining clean meta descriptions and dated Markdown content blocks."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7
    )

    raw_content = response.choices[0].message.content
    return json.loads(raw_content)

def publish_to_supabase(article_data, movers_data):
    print("🚀 Transmitting final layout to database...")
    
    title = article_data.get("title")
    slug = f"{generate_slug(title)}-{datetime.now(timezone.utc).strftime('%m-%d-%y')}"
    
    # 📸 Feature Image Pipeline: Extract the image_url of the #1 trending card on the leaderboard
    feature_image_url = None
    if movers_data and len(movers_data) > 0:
        feature_image_url = movers_data[0].get("image_url")

    payload = {
        "title": title,
        "slug": slug,
        "content": article_data.get("content"),
        "meta_description": article_data.get("meta_description"),
        "feature_image": feature_image_url, 
        "is_published": True
    }
    
    supabase.table("blog_posts").insert(payload).execute()
    print(f"✅ SUCCESS: Article published live!")
    print(f"🔗 Target Path: /blog/{slug}")
    if feature_image_url:
        print(f"🖼️ Linked Feature Image: {feature_image_url}")

if __name__ == "__main__":
    try:
        movers = fetch_hottest_movers()
        
        if not movers:
            print("⏩ Leaderboard payload empty. Checking index connections. Skipping run.")
            sys.exit(0)
            
        article = generate_article(movers)
        publish_to_supabase(article, movers)
        
    except Exception as e:
        print(f"❌ Content generation pipeline failed: {e}")
