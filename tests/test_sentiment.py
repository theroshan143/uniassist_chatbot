"""Tests for the sentiment analysis module."""

import pytest

from app.sentiment import analyze_sentiment, get_sentiment_summary


class TestAnalyzeSentiment:
    """Tests for the analyze_sentiment function."""

    def test_positive_sentiment(self):
        """Positive text should be labeled 'positive' with polarity > 0."""
        result = analyze_sentiment("I love this university! The campus is amazing and wonderful.")
        assert result["label"] == "positive"
        assert result["polarity"] > 0
        assert 0.0 <= result["subjectivity"] <= 1.0

    def test_negative_sentiment(self):
        """Negative text should be labeled 'negative' with polarity < 0."""
        result = analyze_sentiment("This is terrible and awful. I hate the horrible service.")
        assert result["label"] == "negative"
        assert result["polarity"] < 0
        assert 0.0 <= result["subjectivity"] <= 1.0

    def test_neutral_sentiment(self):
        """Factual/neutral text should be labeled 'neutral'."""
        result = analyze_sentiment("The library is open from 9am to 5pm.")
        assert result["label"] == "neutral"
        assert -0.1 <= result["polarity"] <= 0.1
        assert 0.0 <= result["subjectivity"] <= 1.0

    def test_empty_input(self):
        """Empty or whitespace-only input should return neutral defaults."""
        result = analyze_sentiment("")
        assert result["label"] == "neutral"
        assert result["polarity"] == 0.0
        assert result["subjectivity"] == 0.0

        result_ws = analyze_sentiment("   ")
        assert result_ws["label"] == "neutral"
        assert result_ws["polarity"] == 0.0

    def test_none_input(self):
        """None input should return neutral defaults without raising."""
        result = analyze_sentiment(None)
        assert result["label"] == "neutral"
        assert result["polarity"] == 0.0
        assert result["subjectivity"] == 0.0

    def test_return_keys(self):
        """Result should always contain the expected keys."""
        result = analyze_sentiment("Hello world")
        assert "label" in result
        assert "polarity" in result
        assert "subjectivity" in result

    def test_label_values(self):
        """Label must be one of the three allowed values."""
        for text in ["great!", "bad!", "The office is at room 101."]:
            result = analyze_sentiment(text)
            assert result["label"] in ("positive", "negative", "neutral")


class TestGetSentimentSummary:
    """Tests for the get_sentiment_summary function."""

    def test_summary_aggregation(self):
        """Summary should correctly count and average a mixed list."""
        sentiments = [
            {"label": "positive", "polarity": 0.5, "subjectivity": 0.6},
            {"label": "negative", "polarity": -0.4, "subjectivity": 0.8},
            {"label": "neutral", "polarity": 0.0, "subjectivity": 0.1},
            {"label": "positive", "polarity": 0.3, "subjectivity": 0.5},
        ]
        summary = get_sentiment_summary(sentiments)

        assert summary["total"] == 4
        assert summary["positive"] == 2
        assert summary["negative"] == 1
        assert summary["neutral"] == 1
        assert summary["avg_polarity"] == round((0.5 - 0.4 + 0.0 + 0.3) / 4, 4)
        assert summary["avg_subjectivity"] == round((0.6 + 0.8 + 0.1 + 0.5) / 4, 4)
        assert summary["distribution"]["positive"] == 50.0
        assert summary["distribution"]["negative"] == 25.0
        assert summary["distribution"]["neutral"] == 25.0

    def test_empty_list(self):
        """Empty list should return zero counts and zero averages."""
        summary = get_sentiment_summary([])
        assert summary["total"] == 0
        assert summary["positive"] == 0
        assert summary["negative"] == 0
        assert summary["neutral"] == 0
        assert summary["avg_polarity"] == 0.0
        assert summary["avg_subjectivity"] == 0.0
        assert summary["distribution"]["positive"] == 0.0

    def test_all_positive(self):
        """All-positive list should show 100% positive distribution."""
        sentiments = [
            {"label": "positive", "polarity": 0.8, "subjectivity": 0.5},
            {"label": "positive", "polarity": 0.6, "subjectivity": 0.7},
        ]
        summary = get_sentiment_summary(sentiments)
        assert summary["positive"] == 2
        assert summary["negative"] == 0
        assert summary["neutral"] == 0
        assert summary["distribution"]["positive"] == 100.0
