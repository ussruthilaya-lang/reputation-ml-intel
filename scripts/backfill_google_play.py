# ingestion/scripts/backfill_google_play.py

import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


from ingestion.reviews.google_play import fetch_google_play_reviews
from ingestion.load_to_db import insert_mentions

BRANDS = {
    "Chase": "com.chase.sig.android",
    "Bank of America": "com.infonow.bofa",
    "Capital One": "com.konylabs.capitalone",
    "Wells Fargo": "com.wf.wellsfargomobile",
}

PAGES = 6        # 6 × 30 ≈ 180 reviews per brand
PAGE_SIZE = 30  # keep small

def backfill_brand(brand, app_id):
    token = None
    total = 0

    for page in range(PAGES):
        rows, token = fetch_google_play_reviews(
            app_id=app_id,
            brand=brand,
            limit=PAGE_SIZE,
            continuation_token=token
        )

        if not rows:
            print(f"[INFO] No more reviews for {brand}")
            break

        insert_mentions(rows)
        total += len(rows)

        print(f"[OK] {brand}: page {page+1}, inserted {len(rows)}")

        if not token:
            break

    print(f"[DONE] {brand}: total inserted ≈ {total}")

if __name__ == "__main__":
    for brand, app_id in BRANDS.items():
        backfill_brand(brand, app_id)
