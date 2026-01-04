import httpx
import re
import base64
import time
from typing import List, Set
from src.parser import decode_if_base64

# List of public repositories to scrape
SOURCE_URLS = [
    "https://raw.githubusercontent.com/freefq/free/master/v2",
    "https://raw.githubusercontent.com/ermaozi/get_subscribe/main/subscribe/v2ray.txt",
    "https://raw.githubusercontent.com/mfuu/v2ray/master/v2ray"
]

# Simple in-memory cache for scraped results
_scraper_cache = {
    "data": [],
    "timestamp": 0
}
CACHE_DURATION = 3600 # 1 hour

async def fetch_url(client: httpx.AsyncClient, url: str) -> str:
    try:
        resp = await client.get(url)
        if resp.status_code == 200:
            return resp.text
    except Exception as e:
        print(f"Error scraping {url}: {e}")
    return ""

async def get_free_accounts() -> List[str]:
    """
    Scrapes free accounts from public repositories, deduplicates them,
    and returns a list of valid links.
    """
    global _scraper_cache
    current_time = time.time()
    
    # Return cached if valid
    if current_time - _scraper_cache["timestamp"] < CACHE_DURATION and _scraper_cache["data"]:
        return _scraper_cache["data"]

    unique_links: Set[str] = set()
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        for url in SOURCE_URLS:
            content = await fetch_url(client, url)
            # Try decoding if it's base64 blob
            decoded = decode_if_base64(content)
            
            # Extract links line by line
            for line in decoded.splitlines():
                line = line.strip()
                if not line:
                    continue
                
                # Basic validation: check prefix
                if any(line.startswith(p) for p in ["vmess://", "vless://", "trojan://", "ss://", "hy2://", "tuic://"]):
                    unique_links.add(line)

    results = list(unique_links)
    
    # Update cache
    if results:
        _scraper_cache["data"] = results
        _scraper_cache["timestamp"] = current_time
        
    return results
