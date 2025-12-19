from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
import numpy as np

# ------------------------
# Baseline: VADER
# ------------------------
_vader = SentimentIntensityAnalyzer()

def vader_sentiment(text: str) -> float:
    if not text:
        return 0.0
    return _vader.polarity_scores(text)["compound"]  # [-1, 1]

# ------------------------
# Transformer: RoBERTa
# ------------------------
_MODEL = "cardiffnlp/twitter-roberta-base-sentiment"
_tokenizer = AutoTokenizer.from_pretrained(_MODEL)
_model = AutoModelForSequenceClassification.from_pretrained(_MODEL)
_model.eval()

LABEL_MAP = {
    0: -1.0,  # negative
    1: 0.0,   # neutral
    2: 1.0    # positive
}

def transformer_sentiment(text: str) -> float:
    if not text:
        return 0.0

    inputs = _tokenizer(
        text,
        truncation=True,
        padding=True,
        return_tensors="pt"
    )

    with torch.no_grad():
        logits = _model(**inputs).logits
        probs = torch.softmax(logits, dim=1).numpy()[0]

    return float(np.dot(probs, [-1.0, 0.0, 1.0]))  # weighted polarity

# ------------------------
# Rating + Text Fusion
# ------------------------
def combine_sentiment(text_score: float, rating: int | None) -> float:
    if rating is None:
        return text_score

    rating_norm = (rating - 3) / 2  # maps 1–5 → [-1, 1]
    return 0.7 * text_score + 0.3 * rating_norm

def sentiment_label(score: float) -> str:
    if score > 0.2:
        return "positive"
    if score < -0.2:
        return "negative"
    return "neutral"
