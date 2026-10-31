"""Sentiment analysis module for UniAssist chatbot.

Uses TextBlob for rule-based sentiment analysis on user queries.
Provides polarity/subjectivity scores and categorical labels.
"""

import logging
from typing import Any

from textblob import TextBlob

logger = logging.getLogger("uniassist.sentiment")

# ── Thresholds ──────────────────────────────────────────────────────────────

POSITIVE_THRESHOLD = 0.1
NEGATIVE_THRESHOLD = -0.1


def analyze_sentiment(text: str) -> dict[str, Any]:
    """Analyze the sentiment of a given text string.

    Uses TextBlob's rule-based approach to compute polarity and subjectivity.

    Args:
        text: The input text to analyze.

    Returns:
        A dictionary with keys:
            - label: "positive", "negative", or "neutral"
            - polarity: float in [-1.0, 1.0] (negative → positive)
            - subjectivity: float in [0.0, 1.0] (objective → subjective)
    """
    if not text or not text.strip():
        return {"label": "neutral", "polarity": 0.0, "subjectivity": 0.0}

    blob = TextBlob(text.strip())
    polarity = round(blob.sentiment.polarity, 4)
    subjectivity = round(blob.sentiment.subjectivity, 4)

    if polarity > POSITIVE_THRESHOLD:
        label = "positive"
    elif polarity < NEGATIVE_THRESHOLD:
        label = "negative"
    else:
        label = "neutral"

    return {"label": label, "polarity": polarity, "subjectivity": subjectivity}


def get_sentiment_summary(sentiments: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute aggregate statistics from a list of sentiment results.

    Args:
        sentiments: A list of dictionaries as returned by ``analyze_sentiment``.

    Returns:
        A dictionary with keys:
            - total: total number of sentiments analyzed
            - positive: count of positive sentiments
            - negative: count of negative sentiments
            - neutral: count of neutral sentiments
            - avg_polarity: average polarity across all sentiments
            - avg_subjectivity: average subjectivity across all sentiments
            - distribution: dict mapping each label to its percentage
    """
    if not sentiments:
        return {
            "total": 0,
            "positive": 0,
            "negative": 0,
            "neutral": 0,
            "avg_polarity": 0.0,
            "avg_subjectivity": 0.0,
            "distribution": {"positive": 0.0, "negative": 0.0, "neutral": 0.0},
        }

    total = len(sentiments)
    positive = sum(1 for s in sentiments if s.get("label") == "positive")
    negative = sum(1 for s in sentiments if s.get("label") == "negative")
    neutral = sum(1 for s in sentiments if s.get("label") == "neutral")

    avg_polarity = round(sum(s.get("polarity", 0.0) for s in sentiments) / total, 4)
    avg_subjectivity = round(
        sum(s.get("subjectivity", 0.0) for s in sentiments) / total, 4
    )

    distribution = {
        "positive": round(positive / total * 100, 1),
        "negative": round(negative / total * 100, 1),
        "neutral": round(neutral / total * 100, 1),
    }

    return {
        "total": total,
        "positive": positive,
        "negative": negative,
        "neutral": neutral,
        "avg_polarity": avg_polarity,
        "avg_subjectivity": avg_subjectivity,
        "distribution": distribution,
    }
