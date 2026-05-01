from __future__ import annotations

import os
import sys
import types

os.environ.setdefault("DB_URL", "sqlite+aiosqlite:///:memory:")


class _StubModel:
    def predict(self, text: str) -> dict[str, float]:
        score = 0.95 if "kill" in text.lower() else 0.05
        return {
            "toxicity": score,
            "insult": score,
            "threat": score,
            "obscene": 0.0,
            "identity_attack": 0.0,
        }


detoxify_stub = types.ModuleType("detoxify")
detoxify_stub.Detoxify = lambda *_a, **_kw: _StubModel()
sys.modules.setdefault("detoxify", detoxify_stub)
