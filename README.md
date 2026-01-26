# Invest News Bot (RU)

## Выбранный стек (обоснование)
- **Python 3.12 + aiogram v3** — современная асинхронная экосистема для Telegram, быстрый запуск и масштабирование.
- **aiohttp + feedparser** — надежная загрузка RSS/Atom с минимальной задержкой и поддержкой conditional GET.
- **SQLAlchemy 2.0 async + SQLite** — простая локальная БД с плавной миграцией на Postgres.
- **APScheduler** — стабильное расписание поллинга лент с гибкой настройкой интервалов.
- **rapidfuzz** — быстрый fuzzy-match для дедупликации заголовков.

## Возможности
- Выбор компаний из списка (тикер/название) через кнопки и команды.
- Уведомления по релевантным новостям без дублей.
- Умный матчинг по алиасам и контексту.
- Настройки частоты поллинга, тихого режима, порога совпадения и лимитов.

## Структура проекта
```
/app
  main.py
  bot/
    handlers.py
    keyboards.py
    states.py
    texts.py
  news/
    fetcher.py
    parser.py
    dedupe.py
    matcher.py
    scheduler.py
    sources.py
  db/
    models.py
    session.py
    repo.py
  data/
    companies_ru.json
  utils/
    normalize.py
    rate_limit.py
  tests/
    test_matcher.py
    test_dedupe.py
    test_normalize.py
README.md
.env.example
requirements.txt
```

## Быстрый старт (локально)
1. Установить зависимости:
   ```bash
   python3.12 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. Создать `.env` на основе `.env.example`, указать `BOT_TOKEN`.
3. Запустить бота:
   ```bash
   python -m app.main
   ```

## Docker
```bash
docker compose up --build
```

> Если используете Docker, убедитесь, что каталог `./data` существует на хосте (в него будет записан `app.db`).

## Как добавить RSS-ленту
Добавьте запись в `app/news/sources.py`:
```python
from app.news.sources import Source

DEFAULT_SOURCES.append(
    Source(name="Новая лента", url="https://example.com/rss.xml")
)
```
После перезапуска бот подхватит новую ленту.

## Тесты
```bash
pytest
```

## Примечания
- По умолчанию используется SQLite. Для Postgres установите `DB_URL` в `.env`.
- Поллинг лент по умолчанию — каждые 60 секунд.
