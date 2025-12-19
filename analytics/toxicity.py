import re
import os
import sys
import psycopg2
from dotenv import load_dotenv

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

TOXIC_KEYWORDS = [
    "scam", "fraud", "cheat", "stole", "scammer",
    "lawsuit", "worst", "never again", "hate",
    "terrible", "unacceptable", "pathetic", "useless",
    "broken", "garbage", "ridiculous", "disappointing",
    "disgusting", "shameful", "embarrassing", "unbelievable",
    "unfortunate", "awful", "poor", "annoying", "horrible", "shit", "bullshit",
    "waste", "worthless", "disgrace", "dishonor", "shame", "disgraceful", "dishonorable",
    "unworthy"
]

def toxicity_score(text: str) -> float:
    if not text:
        return 0.0

    text = text.lower()
    hits = sum(1 for kw in TOXIC_KEYWORDS if kw in text)
    return min(hits / 3, 1.0)  # cap at 1.0

def escalation_flag(sentiment_score: float, toxicity: float, text: str) -> bool:
    signals = 0

    if toxicity >= 0.65:
        signals += 1
    if sentiment_score <= -0.5:
        signals += 1
    if any(kw in text.lower() for kw in ["refund", "fraud", "scam", "lawsuit"]):
        signals += 1

    return signals >= 2
