from __future__ import annotations

from prometheus_client import Counter, Histogram

messages_processed = Counter(
    "toxiguard_messages_total",
    "Messages processed",
    ["chat_id"],
)

toxicity_detected = Counter(
    "toxiguard_toxicity_total",
    "Toxic messages detected",
    ["category", "chat_id"],
)

ml_duration = Histogram(
    "toxiguard_ml_inference_seconds",
    "ML inference duration",
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
)

telegram_api_errors = Counter(
    "toxiguard_telegram_errors_total",
    "Telegram API errors",
    ["method"],
)
