import os
import json
import sys
import requests
import feedparser
from google import genai
from google.genai import types
from supabase import create_client, Client

# 🔐 WORKER AUTHENTICATION
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
UNSPLASH_ACCESS_KEY = os.environ.get("UNSPLASH_ACCESS_KEY")

if not all([SUPABASE_URL, SUPABASE_KEY, GEMINI_API_KEY, UNSPLASH_ACCESS_KEY]):
    raise ValueError("❌ Execution failed: Missing required environment variables.")

# 🔌 INITIALIZE CLIENTS
if not SUPABASE_URL.startswith("http"):
    SUPABASE_URL = f"https://{SUPABASE_URL}"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
ai_client = genai.Client(api_key=GEMINI_API_KEY)

def fetch_espn_news():
    # 🔥 THE FIX 1: Diverse Sports Network Matrix
    feeds_to_try = [
        {"name": "Yahoo Sports NBA", "url": "https://sports.yahoo.com/nba/rss/"},
        {"name": "ESPN NBA News", "url": "https://www.espn.com/espn/rss/nba/news"},
        {"name": "CBS Sports NFL", "url": "https://www.cbssports.com/rss/headlines/nfl/"},
        {"name": "ESPN Top Headlines", "url": "https://www.espn.com/espn/rss/news"}
    ]
    
    # 🔥 THE FIX 2: Chrome Stealth Headers to bypass Datacenter Firewalls
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
    }
    
    for feed_info in feeds_to_try:
        print(f"📊 Attempting to pull breaking story from {feed_info['name']}...")
        try:
            # Fetch the raw XML through requests first to inject the stealth header
            response = requests.get(feed_info["url"], headers=headers, timeout=10)
            response.raise_for_status()
            
            # Feed the raw XML into feedparser
            feed = feedparser.parse(response.content)
            
            if feed.entries and len(feed.entries) > 0:
                top_story = feed.entries[0]
                print(f"✅ Found breaking story in {feed_info['name']}: {top_story.title}")
                return {
                    "title": top_story.title,
                    "summary": top_story.summary if hasattr(top_story, 'summary') else "Breaking sports update.",
                    "link": top_story.link
                }
            else:
                print(f"⚠️ {feed_info['name']} returned XML but no entries. Trying next fallback...")
        except Exception as e:
            print(f"⚠️ Failed reading {feed_info['name']}: {e}. Trying next fallback...")
            continue
            
    return None

def fetch_unsplash_image(headline):
    print("📸 Fetching dynamic feature image from Unsplash...")
    search_words = " ".join(headline.split(" ")[:2])
    search_query = f"{search_words} sports"
    
    url = f"https://api.unsplash.com/search/photos?query={search_query}&client_id={UNSPLASH_ACCESS_KEY}&per_page=1"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        if data.get("results"):
            return data["results"][0]["urls"]["regular"]
    except Exception as e:
        print(f"⚠️ Unsplash fetch failed, using fallback. Error: {e}")
        
    return "https://images.unsplash.com/photo-1540747737956-37872175267a?auto=format&fit=crop&q=80&w=1200"

def generate_article(news_data):
    print("🧠 Processing metrics and generating market report via Gemini 2.5 Flash...")
    
    prompt = f"""
    You are a high-end sports card market analyst and sports pop-culture writer. 
    Your task is to take a real-time breaking sports news headline and write a highly engaging, 3-paragraph article about how this specific real-world event will impact the player's trading card values.
    
    Rules:
    - Paragraph 1: Hook the reader by summarizing the real-world sports news.
    - Paragraph 2: Dive into the hobby economics. Mention specific flagship cards. Discuss "market size multipliers" or performance hype.
    - Paragraph 3: Give a final "Verdict" (Buy, Sell, or Hold) with a quick justification.
    - Tone: Exciting, analytical, modern, and engaging.
    - Output MUST be strict JSON with three exact keys: "title", "subtitle", "body". Do not use markdown blocks.
    
    Here is the current breaking news:
    Headline: "{news_data['title']}"
    Details: "{news_data['summary']}"
    """

   # 🔥 THE DEFINITIVE FIX: Use the flagship production model recognized by the new SDK
    response = ai_client.models.generate_content(
        model='gemini-2.5-pro', # <--- Update this exact line
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
        ),
    )

    raw_content = response.text.replace("```json", "").replace("```", "").strip()
    return json.loads(raw_content)

def publish_to_supabase(article_data, image_url, espn_link):
    print("🚀 Transmitting final layout to hobby_articles database...")
    
    payload = {
        "title": article_data.get("title"),
        "subtitle": article_data.get("subtitle"),
        "body": article_data.get("body"),
        "image_url": image_url,
        "is_live": True,
        "espn_source_link": espn_link
    }
    
    response = supabase.table("hobby_articles").insert(payload).execute()
    print(f"✅ SUCCESS: Article published live!")
    print(f"📰 Headline: {payload['title']}")

if __name__ == "__main__":
    try:
        story = fetch_espn_news()
        
        if not story:
            print("❌ All fallback feeds are currently empty or blocked. Skipping run.")
            sys.exit(0)
            
        image_url = fetch_unsplash_image(story["title"])
        article = generate_article(story)
        publish_to_supabase(article, image_url, story["link"])
        
    except Exception as e:
        print(f"❌ Content generation pipeline failed: {e}")
        sys.exit(1)
