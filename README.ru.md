<div align="center">

# toxiguard

*Тихий страж шумных чатов.*

[English](./README.md) · **Русский**

[![CI](https://github.com/justxxi/toxiguard/actions/workflows/ci.yml/badge.svg)](https://github.com/justxxi/toxiguard/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12-blue?logo=python&logoColor=white)](https://www.python.org/)
[![aiogram](https://img.shields.io/badge/aiogram-3.27-2CA5E0?logo=telegram&logoColor=white)](https://aiogram.dev/)
[![License](https://img.shields.io/badge/license-MIT-lightgrey)](./LICENSE)

</div>

---

`toxiguard` — это телеграм-бот, который чувствует настроение чата.
Он молча слушает токсичность, удаляет худшее и даёт три шанса перед тем, как заглушить нарушителя — за миллисекунды, на десяти языках, не привлекая внимания.

## Что внутри

- **Многоязычный ML.** Detoxify (`xlm-roberta`) понимает RU, EN, UK, DE, FR, ES, IT, PT, TR.
- **Два слоя защиты.** Словарь мата для мгновенного решения, нейросеть — для оттенков.
- **Адаптивность.** Порог чувствительности на каждый чат, Redis кэш прав админов и настроек.
- **Атомарность.** Счётчики варнов без гонок: PostgreSQL и UPSERT через `ON CONFLICT`.
- **Прозрачность.** Prometheus метрики + FastAPI-дашборд с live статистикой.
- **Цельность.** Бот и дашборд — один образ, PostgreSQL + Redis бэкенд.

## Архитектура

```
        ┌──────────────┐    ┌──────────────────┐    ┌──────────────┐
Update ─►  middleware  │ ─► │  profanity / ML  │ ──► │  PostgreSQL  │
        └──────┬───────┘    └──────────────────┘    └──────┬───────┘
               │                     │                    │
               ▼                     ▼                    ▼
       удалить + варн          Redis кэш           дашборд FastAPI
                                                      Prometheus /metrics
```

## Быстрый старт

```bash
git clone https://github.com/justxxi/toxiguard.git
cd toxiguard
cp .env.example .env          # вставь BOT_TOKEN
docker compose up -d --build
```

Дашборд: <http://localhost:8000>

## Команды

| Команда          | Кто         | Что делает                                          |
| ---------------- | ----------- | --------------------------------------------------- |
| `/stats`         | админы      | сводка по инцидентам, разбивка, текущий порог       |
| `/top`           | админы      | топ нарушителей с медалями                          |
| `/warn`          | админы      | ручной варн (ответом или `@username`)               |
| `/unwarn`        | админы      | снять варн (ответом или `@username`)                |
| `/mute 30m`      | админы      | мут на `30m`/`2h`/`1d` (ответом или `@user`)        |
| `/unmute`        | админы      | вернуть голос (ответом или `@username`)             |
| `/threshold 0.7` | админы      | подстроить чувствительность (`0.0` — `1.0`)         |

Три варна — автоматически час молчания.

## Разработка

```bash
python -m venv .venv && source .venv/bin/activate    # macOS / Linux
pip install -r requirements-dev.txt
ruff check . && ruff format --check .
pytest -q
```

Тесты подменяют ML-модель заглушкой — не нужен ни PyTorch, ни GPU.

## Конфигурация

| Переменная       | По умолчанию                             | Примечание                     |
| ---------------- | ---------------------------------------- | ------------------------------ |
| `BOT_TOKEN`           | —                                      | обязательна                    |
| `DB_URL`              | `sqlite+aiosqlite:///toxiguard.db`     | любой async-URL SQLAlchemy     |
| `REDIS_URL`           | `redis://localhost:6379`                 | опционально, для кэша и rate limit |
| `LOG_LEVEL`           | `INFO`                                 | `DEBUG` / `INFO` / `WARNING`     |
| `DEFAULT_THRESHOLD`   | `0.75`                                 | глобальный порог токсичности   |
| `MUTE_AFTER`          | `3`                                    | варнов до автомута             |
| `ML_CONCURRENCY`      | `4`                                    | параллельных ML-инференсов     |
| `EVENT_RETENTION_DAYS`| `90`                                   | хранение истории (дней)        |
| `DASHBOARD_PASSWORD`  | —                                      | basic auth для API дашборда    |

## Лицензия

[MIT](./LICENSE)
