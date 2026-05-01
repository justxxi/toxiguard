<div align="center">

# toxiguard

*A quiet sentinel for noisy chats.*

**English** · [Русский](./README.ru.md)

[![CI](https://github.com/justxxi/toxiguard/actions/workflows/ci.yml/badge.svg)](https://github.com/justxxi/toxiguard/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12-blue?logo=python&logoColor=white)](https://www.python.org/)
[![aiogram](https://img.shields.io/badge/aiogram-3.27-2CA5E0?logo=telegram&logoColor=white)](https://aiogram.dev/)
[![License](https://img.shields.io/badge/license-MIT-lightgrey)](./LICENSE)

</div>

---

`toxiguard` is a Telegram moderation bot that reads the room.
It listens for toxicity, deletes the worst of it, and gives offenders three chances before silencing them — all in milliseconds, multilingual, and quietly out of the way.

## Highlights

- **Multilingual ML.** Powered by Detoxify (`xlm-roberta`) — EN, RU, UK, DE, FR, ES, IT, PT, TR.
- **Two layers of defence.** Profanity dictionary for instant decisions, neural classifier for nuance.
- **Adaptive.** Per-chat sensitivity threshold, in-memory caches for predictions, admin status, and settings.
- **Atomic.** Race-free warning counters with SQLite WAL and `ON CONFLICT` upserts.
- **Observable.** A FastAPI dashboard exposes live stats, top offenders, and incident history.
- **Composable.** Bot and dashboard share one image, one volume, one schema.

## Architecture

```
        ┌──────────────┐    ┌──────────────────┐    ┌──────────────┐
Update ─►  middleware  │ ─► │  profanity / ML  │ ─► │   sqlite     │
        └──────┬───────┘    └──────────────────┘    └──────┬───────┘
               │                                            │
               ▼                                            ▼
        delete + warn                              FastAPI dashboard
```

## Quick start

```bash
git clone https://github.com/justxxi/toxiguard.git
cd toxiguard
cp .env.example .env          # set BOT_TOKEN
docker compose up -d --build
```

Dashboard: <http://localhost:8000>

## Commands

| Command          | Who         | Effect                                            |
| ---------------- | ----------- | ------------------------------------------------- |
| `/stats`         | admins      | incident totals, breakdown, current threshold     |
| `/top`           | admins      | top offenders with medals                         |
| `/warn`          | admins      | manual warning (reply to a message)               |
| `/unwarn`        | admins      | revoke a warning                                  |
| `/mute 30m`      | admins      | mute for `30m` / `2h` / `1d`                      |
| `/unmute`        | admins      | restore voice and reset warnings                  |
| `/threshold 0.7` | admins      | tune sensitivity (`0.0` lax — `1.0` strict)       |

Three warnings = an automatic hour of silence.

## Development

```bash
python -m venv .venv && source .venv/bin/activate    # macOS / Linux
pip install -r requirements-dev.txt
ruff check . && ruff format --check .
pytest -q
```

The test suite stubs out the ML model, so you don't need GPU drivers or PyTorch downloads to run it.

## Configuration

| Variable         | Default                                  | Notes                          |
| ---------------- | ---------------------------------------- | ------------------------------ |
| `BOT_TOKEN`      | —                                        | required                       |
| `DB_URL`         | `sqlite+aiosqlite:///toxiguard.db`       | any SQLAlchemy async URL       |
| `LOG_LEVEL`      | `INFO`                                   | `DEBUG` / `INFO` / `WARNING`   |

## License

[MIT](./LICENSE)
