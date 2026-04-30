from __future__ import annotations

import asyncio
from functools import lru_cache
from typing import TypedDict

from detoxify import Detoxify

# xlm-r checkpoint: en, ru, uk, de, fr, es, it, pt, tr
MODEL_NAME = "multilingual"


class Scores(TypedDict):
    toxicity: float
    insult: float
    threat: float
    obscene: float
    identity_hate: float


_ZERO: Scores = {"toxicity": 0.0, "insult": 0.0, "threat": 0.0, "obscene": 0.0, "identity_hate": 0.0}


@lru_cache(maxsize=1)
def _model() -> Detoxify:
    return Detoxify(MODEL_NAME)


def warmup() -> None:
    _model()


def _predict(text: str) -> Scores:
    raw = _model().predict(text)
    return {
        "toxicity": float(raw.get("toxicity", 0.0)),
        "insult": float(raw.get("insult", 0.0)),
        "threat": float(raw.get("threat", 0.0)),
        "obscene": float(raw.get("obscene", 0.0)),
        "identity_hate": float(raw.get("identity_attack", 0.0)),
    }


async def analyze(text: str) -> Scores:
    text = (text or "").strip()
    if not text:
        return dict(_ZERO)
    return await asyncio.to_thread(_predict, text)
