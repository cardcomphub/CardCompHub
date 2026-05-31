import os
import requests
import unicodedata
import re
from supabase import create_client, Client

# 🔐 WORKER AUTHENTICATION
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not all([SUPABASE_URL, SUPABASE_KEY]):
    raise ValueError("❌ Missing environment variables for database execution.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# 📊 COMPLETE WORKING LEADERBOARD CONFIGURATIONS
LEADERBOARD_TASKS = [
    # 🏀 Basketball (NBA) Core Nodes
    {"sport": "basketball", "league": "nba", "category": None, "sort": "offensive.avgPoints:desc"},
    {"sport": "basketball", "league": "nba", "category": None, "sort": "offensive.avgAssists:desc"},
    {"sport": "basketball", "league": "nba", "category": None, "sort": "general.avgRebounds:desc"}, # Fixed to general path
    
    # 🏈 Football (NFL) Core Nodes
    {"sport": "football", "league": "nfl", "category": "offense:passing", "sort": "passing.passingYards:desc"},
    {"sport": "football", "league": "nfl", "category": "offense:passing", "sort": "passing.passingTouchdowns:desc"}, # Explicit off-shoot split
    {"sport": "football", "league": "nfl", "category": "offense:rushing", "sort": "rushing.rushingYards:desc"},
    {"sport": "football", "league": "nfl", "category": "offense:rushing", "sort": "rushing.rushingTouchdowns:desc"}, # Explicit off-shoot split
    {"sport": "football", "league": "nfl", "category": "offense:receiving", "sort": "receiving.receivingYards:desc"},
    {"sport": "football", "league": "nfl", "category": "offense:receiving", "sort": "receiving.receivingTouchdowns:desc"}, # Explicit off-shoot split
    
    # ⚾ Baseball (MLB) Core Nodes
    {"sport": "baseball", "league": "mlb", "category": "batting", "sort": "batting.homeRuns:desc"},
    {"sport": "baseball", "league": "mlb", "category": "batting", "sort": "batting.rbi:desc"}, # Shortened to database shorthand
    {"sport": "baseball", "league": "mlb", "category": "pitching", "sort": "pitching.strikeouts:desc"}
]

def normalize_name(name: str) -> str:
    """Standardizes player names by stripping accents, punctuation, and suffixes."""
    if not name:
        return ""
    name = name.lower().strip()
    name = unicodedata.normalize('NFKD', name)
    name = "".join([c for c in name if not unicodedata.combining(c)])
    suffixes = [r'\bjr\b', r'\bsr\b', r'\bii\b', r'\biii\b', r'\biv\b']
    for suffix in suffixes:
        name = re.sub(suffix, '', name)
    name = re.sub(r"[.'\-,]", "", name)
    return " ".join(name.split())

def fetch_top_five_leaders():
    """Queries fully qualified internal endpoints to gather current elite sports talent lists."""
    leader_names = set()
    base_url = "https://site.web.api.espn.com/apis/common/v3/sports"
    
    request_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.9"
    }
    
    for task in LEADERBOARD_TASKS:
        url = f"{base_url}/{task['sport']}/{task['league']}/statistics/byathlete"
        
        query_params = {
            "region": "us",
            "lang": "en",
            "contentorigin": "espn",
            "isqualified": "false",
            "sort": task["sort"]
        }
        
        if task["category"]:
            query_params["category"] = task["category"]
            
        try:
            response = requests.get(url, params=query_params, headers=request_headers, timeout=15)
            if response.status_code != 200:
                print(f"⚠️ Query skipped with code {response.status_code} for: {task['league']} ({task['sort']})")
                continue
                
            data = response.json()
            athletes_list = data.get("athletes", [])
            
            for entry in athletes_list[:5]:
                athlete_info = entry.get("athlete", {})
                name = athlete_info.get("displayName")
                if name:
                    leader_names.add(normalize_name(name))
                    
        except Exception as e:
            print(f"❌ Network anomaly encountered parsing {task['league']}: {e}")
            
    return leader_names

def sync_stats_to_supabase():
    print("🚀 Running Dynamic Stats Leadership Realignment Loop...")
    
    # Run the queries and compile clean names
    elite_stat_leaders = fetch_top_five_leaders()
    print(f"📊 Processed {len(elite_stat_leaders)} total unique statistical benchmark leaders.")
    
    if not elite_stat_leaders:
        print("❌ Sync aborted: No response data returned from live network nodes.")
        return

    # Pull down existing base card rows from your database
    cards_response = supabase.table("base_cards").select("id, player_name").execute()
    db_cards = cards_response.data or []
    
    print("⏳ Synchronizing state switches inside your catalog...")
    for card in db_cards:
        clean_player_name = normalize_name(card["player_name"])
        
        # Match current name parameters to the dynamic sports results
        is_currently_leader = clean_player_name in elite_stat_leaders
        
        try:
            supabase.table("base_cards") \
                .update({"is_stat_leader": is_currently_leader}) \
                .eq("id", card["id"]) \
                .execute()
        except Exception as db_err:
            print(f"⚠️ Table write skipped for {card['player_name']}: {db_err}")

    print("✅ Complete database stats synchronization finalized successfully!")

if __name__ == "__main__":
    sync_stats_to_supabase()