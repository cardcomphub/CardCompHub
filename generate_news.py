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

# 🔥 THE FIX: Initialize the new, official Google GenAI client
ai_client = genai.Client(api_key=GEMINI_API_KEY)

def fetch_espn_news():
    print("📊 Pulling top breaking story from ESPN NBA RSS feed...")
    feed = feedparser.parse('https://www.espn.com/espn/rss/nba/news')
    
    if not feed.entries:
        return None
        
    top_story = feed.entries[0]
    return {
        "title": top_story.title,
        "summary": top_story.summary,
        "link": top_story.link
    }

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
    
    Here is the current breaking news from ESPN:
    Headline: "{news_data['title']}"
    Details: "{news_data['summary']}"
    """

    # 🔥 THE FIX: Using the new SDK's structural generation syntax
    response = ai_client.models.generate_content(
        model='gemini-2.5-flash',
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
            print("⏩ ESPN feed empty or unreachable. Skipping run.")
            sys.exit(0)
            
        image_url = fetch_unsplash_image(story["title"])
        article = generate_article(story)
        publish_to_supabase(article, image_url, story["link"])
        
    except Exception as e:
        print(f"❌ Content generation pipeline failed: {e}")
        sys.exit(1)
