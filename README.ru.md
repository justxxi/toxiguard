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
- **Адаптивность.** Порог чувствительности на каждый чат, кэши предсказаний, прав админов и настроек в памяти.
- **Атомарность.** Счётчики варнов без гонок: SQLite WAL и UPSERT через `ON CONFLICT`.
- **Прозрачность.** FastAPI-дашборд показывает статистику, топ нарушителей и историю инцидентов.
- **Цельность.** Бот и дашборд — один образ, один том, одна схема.

## Архитектура

```
        ┌──────────────┐    ┌──────────────────┐    ┌──────────────┐
Update ─►  middleware  │ ─► │  profanity / ML  │ ─► │   sqlite     │
        └──────┬───────┘    └──────────────────┘    └──────┬───────┘
               │                                            │
               ▼                                            ▼
       удалить + варн                            дашборд FastAPI
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
| `/warn`          | админы      | ручной варн (ответом на сообщение)                  |
| `/unwarn`        | админы      | снять варн                                          |
| `/mute 30m`      | админы      | мут на `30m` / `2h` / `1d`                          |
| `/unmute`        | админы      | вернуть голос и обнулить варны                      |
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
| `BOT_TOKEN`      | —                                        | обязательна                    |
| `DB_URL`         | `sqlite+aiosqlite:///toxiguard.db`       | любой async-URL SQLAlchemy     |
| `LOG_LEVEL`      | `INFO`                                   | `DEBUG` / `INFO` / `WARNING`   |

## Лицензия

[MIT](./LICENSE)
