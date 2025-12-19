import requests
from datetime import datetime, timezone

BASE_URL = "https://api.pullpush.io/reddit/search/submission"

def scrape_reddit(brand: str, limit: int = 50):
    """
    Scrape Reddit submissions using PullPush (Pushshift mirror).
    Fails gracefully if the upstream service is unavailable.
    """

    params = {
        "q": brand,
        "size": limit,
        "sort": "desc",
        "sort_type": "created_utc"
    }

    try:
        response = requests.get(BASE_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json().get("data", [])
    except Exception as e:
        # IMPORTANT: never crash the app due to ingestion
        print(f"[WARN] Reddit ingestion failed for brand='{brand}': {e}")
        return []

    results = []
    for post in data:
        results.append({
            "source": "reddit",
            "source_id": str(post.get("id")),
            "brand": brand.lower(),
            "created_utc": datetime.fromtimestamp(
                post.get("created_utc"), tz=timezone.utc
            ),
            "author": post.get("author") or "",
            "title": post.get("title") or "",
            "body": post.get("selftext") or "",
            "url": post.get("full_link") or "",
            "subreddit": post.get("subreddit") or "",
        })

    return results
