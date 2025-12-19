from google_play_scraper import reviews, Sort
from datetime import datetime, timezone

def fetch_google_play_reviews(app_id: str, brand: str, limit: int = 30, continuation_token=None):
    try:
        result, token = reviews(
            app_id,
            lang="en",
            country="us",
            sort=Sort.NEWEST,
            count=limit,
            continuation_token=continuation_token
        )
    except Exception as e:
        print(f"[WARN] Google Play ingestion failed for {app_id}: {e}")
        return [], None

    rows = []
    for r in result:
        rows.append({
            "source": "google_play",
            "source_id": f"{app_id}_{r.get('reviewId')}",
            "brand": brand.lower(),
            "created_utc": datetime.fromtimestamp(
                r.get("at").timestamp(), tz=timezone.utc
            ),
            "author": r.get("userName"),
            "title": "",
            "body": r.get("content"),
            "rating": r.get("score"),
            "version": r.get("reviewCreatedVersion"),
            "source_context": app_id,
            "url": f"https://play.google.com/store/apps/details?id={app_id}",
        })

    return rows, token
