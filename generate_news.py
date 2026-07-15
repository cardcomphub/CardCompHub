import os
import json
import sys
import requests
import feedparser
import re 
from openai import OpenAI
from supabase import create_client, Client

# 🔐 WORKER AUTHENTICATION
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
UNSPLASH_ACCESS_KEY = os.environ.get("UNSPLASH_ACCESS_KEY")

if not all([SUPABASE_URL, SUPABASE_KEY, OPENAI_API_KEY, UNSPLASH_ACCESS_KEY]):
    raise ValueError("❌ Execution failed: Missing required environment variables.")

# 🔌 INITIALIZE CLIENTS
if not SUPABASE_URL.startswith("http"):
    SUPABASE_URL = f"https://{SUPABASE_URL}"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# 🔥 INITIALIZE OPENAI
ai_client = OpenAI(api_key=OPENAI_API_KEY)

def fetch_sports_news():
    feeds_to_try = [
        {"name": "ESPN Top Headlines", "url": "https://www.espn.com/espn/rss/news"}
        {"name": "ESPN NBA News", "url": "https://www.espn.com/espn/rss/nba/news"},
        {"name": "Yahoo Sports NBA", "url": "https://sports.yahoo.com/nba/rss/"},
        {"name": "CBS Sports NFL", "url": "https://www.cbssports.com/rss/headlines/nfl/"},
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
    }
    
    for feed_info in feeds_to_try:
        print(f"📊 Attempting to pull breaking story from {feed_info['name']}...")
        try:
            response = requests.get(feed_info["url"], headers=headers, timeout=10)
            response.raise_for_status()
            
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
    print("🧠 Processing metrics and generating market report via OpenAI gpt-4o...")
    
    # 🔥 UPDATED PROMPT: Requesting a structured 'target_player' extraction element
    prompt = f"""
    You are a high-end sports card market analyst and sports pop-culture writer for CardCompHub. 
    Your task is to take a real-time breaking sports news headline and write a highly engaging, 3-paragraph article about how this specific real-world event will impact the player's trading card values.
    
    Rules:
    - Paragraph 1: Hook the reader by summarizing the real-world sports news.
    - Paragraph 2: Dive into the hobby economics. Mention specific flagship cards (e.g., Prizm, Optic, Topps Chrome). Discuss "market size multipliers" or performance hype.
    - Paragraph 3: Give a final "Verdict" (Buy, Sell, or Hold) with a quick justification.
    - Tone: Exciting, analytical, modern, and engaging.
    - Output MUST be a strict JSON object with exactly FOUR keys: "title", "subtitle", "body", "target_player".
    - "target_player": Extract the exact first and last name of the main athlete this article focuses on (e.g., "Terry McLaurin", "Elly De La Cruz"). If no specific athlete matches, return null.
    
    Here is the current breaking news:
    Headline: "{news_data['title']}"
    Details: "{news_data['summary']}"
    """

    response = ai_client.chat.completions.create(
        model="gpt-4o",
        response_format={ "type": "json_object" },
        messages=[
            {"role": "system", "content": "You output strict JSON objects combining clean titles, subtitles, bodies, and player targets."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7
    )

    raw_content = response.choices[0].message.content
    return json.loads(raw_content)

def generate_slug(text):
    slug = re.sub(r'[^a-z0-9]+', '-', text.lower())
    return slug.strip('-')

# 🔥 NEW: Programmatic Link Engine
def inject_internal_links(article_data):
    player_name = article_data.get("target_player")
    if not player_name:
        return article_data

    print(f"🔍 Scanning database footprints for an active card profile matching: '{player_name}'")
    
    # Pull one valid matching base card profile entry for this player name
    response = supabase.table("base_cards").select("slug").eq("player_name", player_name).limit(1).execute()
    
    if response.data and len(response.data) > 0:
        card_slug = response.data[0]["slug"]
        print(f"🔗 Direct match isolated! Intercepting text stream to link to slug: {card_slug}")
        
        body_text = article_data.get("body", "")
        
        # Build high-authority styled HTML link matching your app's frontend theme
        anchor_tag = f'<a href="/cards/{card_slug}" class="text-emerald-400 font-bold hover:underline">{player_name}</a>'
        
        # Case-insensitive safe text replace to turn plain text player names into link nodes
        updated_body = re.sub(re.escape(player_name), anchor_tag, body_text, flags=re.IGNORECASE)
        article_data["body"] = updated_body
    else:
        print(f"⚠️ No active base_cards reference found for '{player_name}'. Retaining default layout strings.")
        
    return article_data

def publish_to_supabase(article_data, image_url, source_link):
    # 🔥 Runs text processing pipeline right before shipping payload off to production tables
    article_data = inject_internal_links(article_data)
    
    print("🚀 Transmitting final layout to hobby_articles database...")
    title = article_data.get("title", "Breaking News")
    slug = generate_slug(title)
    
    payload = {
        "title": title,
        "slug": slug,
        "subtitle": article_data.get("subtitle"),
        "body": article_data.get("body"),
        "image_url": image_url,
        "is_live": True,
        "espn_source_link": source_link
    }
    
    supabase.table("hobby_articles").insert(payload).execute()
    print(f"✅ SUCCESS: Article published live!")
    print(f"📰 Headline: {payload['title']}")
    print(f"🔗 URL Slug: {slug}")

if __name__ == "__main__":
    try:
        story = fetch_sports_news()
        
        if not story:
            print("❌ All fallback feeds are currently empty or blocked. Skipping run.")
            sys.exit(0)
            
        image_url = fetch_unsplash_image(story["title"])
        article = generate_article(story)
        publish_to_supabase(article, image_url, story["link"])
        
    except Exception as e:
        print(f"❌ Content generation pipeline failed: {e}")
        sys.exit(1)
