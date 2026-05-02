from __future__ import annotations

import asyncio
import hashlib
import logging
from collections import OrderedDict
from functools import lru_cache
from typing import TypedDict

from detoxify import Detoxify

from core.config import settings

log = logging.getLogger(__name__)


class Scores(TypedDict):
    toxicity: float
    insult: float
    threat: float
    obscene: float
    identity_hate: float


_ZERO: Scores = {
    "toxicity": 0.0,
    "insult": 0.0,
    "threat": 0.0,
    "obscene": 0.0,
    "identity_hate": 0.0,
}

_cache: OrderedDict[str, Scores] = OrderedDict()
_semaphore = asyncio.Semaphore(settings.ml_concurrency)


@lru_cache(maxsize=1)
def _model() -> Detoxify:
    log.info("loading detoxify model: %s", settings.model_name)
    return Detoxify(settings.model_name)


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


def _cache_get(key: str) -> Scores | None:
    hit = _cache.get(key)
    if hit is None:
        return None
    _cache.move_to_end(key)
    return hit


def _cache_put(key: str, value: Scores) -> None:
    _cache[key] = value
    _cache.move_to_end(key)
    if len(_cache) > settings.cache_size:
        _cache.popitem(last=False)


def _cache_key(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


async def analyze(text: str) -> Scores:
    text = (text or "").strip()
    if len(text) < settings.min_text_len:
        return dict(_ZERO)

    key = _cache_key(text.lower())
    hit = _cache_get(key)
    if hit is not None:
        return dict(hit)

    async with _semaphore:
        scores = await asyncio.to_thread(_predict, text)
    _cache_put(key, scores)
    return scores
