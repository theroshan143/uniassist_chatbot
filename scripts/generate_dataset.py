



"""
Generate a 5000-row synthetic dataset for the UniAssist AI Chatbot project.
Output: uniassist/data/dataset.csv
"""

import csv
import random
import math
from datetime import datetime, timedelta

random.seed(42)

# ── Constants ──────────────────────────────────────────────────────────────
NUM_ROWS = 5000
OUTPUT_PATH = r"c:\Users\kumar\AI CHATBOT\uniassist\data\dataset.csv"

QUERY_TYPES = ["query_type_1", "query_type_2", "query_type_3", "query_type_4", "query_type_5"]
QUERY_WEIGHTS = [25, 25, 20, 18, 12]

INTENTS = ["admissions", "exams", "fees", "hostel", "grievance", "library"]
INTENT_WEIGHTS = [22, 20, 18, 15, 13, 12]

RATING_VALUES = [1, 2, 3, 4, 5]
RATING_WEIGHTS = [10, 15, 25, 30, 20]

START_TIME = datetime(2026, 1, 15, 8, 0, 0)
BIZ_START_HOUR = 8
BIZ_END_HOUR = 21  # 9 PM

# ── Helpers ────────────────────────────────────────────────────────────────

def weighted_choice(items, weights):
    """random.choices wrapper returning a single item."""
    return random.choices(items, weights=weights, k=1)[0]


def next_timestamp(current: datetime) -> datetime:
    """Advance by 5-30 min, skipping outside business hours."""
    gap = random.randint(5, 30)
    nxt = current + timedelta(minutes=gap)
    # If past 9 PM, jump to next day 8 AM + 0-30 min jitter
    if nxt.hour >= BIZ_END_HOUR:
        next_day = nxt.date() + timedelta(days=1)
        jitter = random.randint(0, 30)
        nxt = datetime(next_day.year, next_day.month, next_day.day,
                       BIZ_START_HOUR, jitter, random.randint(0, 59))
    return nxt


def gen_confidence(is_anomaly_low: bool) -> float:
    """Beta-distributed confidence in [0.55, 0.999], mostly 0.70-0.95."""
    if is_anomaly_low:
        # Anomalously low: uniform in [0.55, 0.62]
        return round(random.uniform(0.55, 0.62), 3)
    # Beta(5, 2) shifted & scaled into [0.55, 0.999]
    raw = random.betavariate(5, 2)  # mode ~0.8, range (0,1)
    val = 0.55 + raw * (0.999 - 0.55)
    return round(val, 3)


def gen_escalated(confidence: float, intent: str) -> int:
    """~3-4 % overall; higher chance when confidence < 0.70 or grievance."""
    base_prob = 0.02
    if confidence < 0.70:
        base_prob += 0.15
    if intent == "grievance":
        base_prob += 0.06
    return 1 if random.random() < base_prob else 0


def gen_rating(escalated: int, confidence: float, is_anomaly_high_conf_low_rate: bool,
               is_anomaly_low_conf_high_rate: bool) -> int:
    """Weighted rating with correlation to escalation/confidence + anomalies."""
    if is_anomaly_high_conf_low_rate:
        return random.choice([1, 2])
    if is_anomaly_low_conf_high_rate:
        return random.choice([4, 5])

    weights = list(RATING_WEIGHTS)  # copy
    if escalated:
        # Shift toward lower ratings
        weights = [25, 30, 25, 15, 5]
    elif confidence < 0.70:
        weights = [20, 25, 25, 20, 10]
    elif confidence > 0.92:
        weights = [5, 10, 20, 35, 30]
    return weighted_choice(RATING_VALUES, weights)


# ── Main generation ───────────────────────────────────────────────────────

def generate():
    rows = []
    ts = START_TIME

    # Pre-decide which rows are anomalies (~3 % = 150 rows)
    # Half: low-confidence + high-rating;  Half: high-confidence + low-rating
    anomaly_indices = set(random.sample(range(NUM_ROWS), 150))
    low_conf_high_rate = set(list(anomaly_indices)[:75])
    high_conf_low_rate = anomaly_indices - low_conf_high_rate

    for i in range(NUM_ROWS):
        sid = f"S{i+1:04d}"

        query_type = weighted_choice(QUERY_TYPES, QUERY_WEIGHTS)
        intent = weighted_choice(INTENTS, INTENT_WEIGHTS)

        is_anom_low = i in low_conf_high_rate
        is_anom_high = i in high_conf_low_rate

        confidence = gen_confidence(is_anom_low)
        if is_anom_high:
            # Force high confidence for the "high-conf but low-rating" anomaly
            confidence = round(random.uniform(0.92, 0.999), 3)

        escalated = gen_escalated(confidence, intent)
        rating = gen_rating(escalated, confidence, is_anom_high, is_anom_low)

        rows.append([
            sid,
            ts.strftime("%Y-%m-%d %H:%M:%S"),
            query_type,
            intent,
            f"{confidence:.3f}",
            escalated,
            rating,
        ])

        ts = next_timestamp(ts)

    # Write CSV
    with open(OUTPUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "session_id", "timestamp", "user_query_type", "intent",
            "confidence_score", "escalated", "user_rating"
        ])
        writer.writerows(rows)

    print(f"Wrote {len(rows)} data rows to {OUTPUT_PATH}")
    return rows


if __name__ == "__main__":
    rows = generate()

    # ── Quick verification stats ──
    from collections import Counter
    qt_counts = Counter(r[2] for r in rows)
    int_counts = Counter(r[3] for r in rows)
    esc_count = sum(1 for r in rows if r[5] == 1)
    rat_counts = Counter(r[6] for r in rows)

    print("\n=== Distribution Summary ===")
    print(f"Total rows : {len(rows)}")
    print(f"\nQuery-type distribution:")
    for k in sorted(qt_counts):
        print(f"  {k}: {qt_counts[k]}  ({qt_counts[k]/len(rows)*100:.1f}%)")
    print(f"\nIntent distribution:")
    for k in sorted(int_counts):
        print(f"  {k}: {int_counts[k]}  ({int_counts[k]/len(rows)*100:.1f}%)")
    print(f"\nEscalated: {esc_count}  ({esc_count/len(rows)*100:.1f}%)")
    print(f"\nRating distribution:")
    for k in sorted(rat_counts):
        print(f"  {k}: {rat_counts[k]}  ({rat_counts[k]/len(rows)*100:.1f}%)")

    # Timestamp span
    print(f"\nTimestamp range: {rows[0][1]} to {rows[-1][1]}")
