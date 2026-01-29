from __future__ import annotations

from app.bot.constants import SUPPORT_HANDLE

START_TEXT = (
    "Привет! Я собираю новости по выбранным компаниям и присылаю их вам.\n\n"
    "Что можно сделать:\n"
    "• добавить компанию через кнопку или команду /add\n"
    "• посмотреть список компаний через /list\n"
    "• настроить уведомления, частоту проверки и лимит новостей в разделе настроек\n"
    "• получить помощь через кнопку «❓ Помощь»"
)

HELP_TEXT = (
    "Команды:\n"
    "/start — главное меню\n"
    "/help — помощь\n"
    "/add тикер|название — добавить компанию\n"
    "/list — список выбранных компаний\n\n"
    f"Техподдержка: {SUPPORT_HANDLE}"
)

ASK_COMPANY_TEXT = "Введите тикер или название компании (например, LKOH или ЛУКОЙЛ)."

NO_COMPANIES_TEXT = "У вас пока нет подписок. Добавьте компанию через ➕ Добавить компанию."

NOTIFICATIONS_ON = "🔔 Уведомления включены."
NOTIFICATIONS_OFF = "🔕 Уведомления выключены."

def analysis_mode_label(match_threshold: int) -> str:
    return "Точный" if match_threshold >= 4 else "Умный"


def build_settings_text(
    notifications_enabled: bool,
    polling_interval: int,
    hourly_limit: int | None,
    match_threshold: int,
) -> str:
    notifications_status = "ВКЛ" if notifications_enabled else "ВЫКЛ"
    limit_text = f"{hourly_limit}/час" if hourly_limit is not None else "без лимита"
    analysis_label = analysis_mode_label(match_threshold)
    return (
        "Настройки:\n\n"
        f"🔔 Уведомления: {notifications_status} — бот присылает новости автоматически.\n"
        f"⏱ Частота проверки: {polling_interval} сек — как часто проверять источники.\n"
        f"📈 Лимит: {limit_text} — ограничение новостей в час.\n"
        f"🧠 Режим анализа: {analysis_label} — точный строже, умный шире по совпадениям.\n"
        "🌙 Тихий режим — часы, когда уведомления не приходят."
    )


def build_analysis_mode_text(match_threshold: int) -> str:
    current = analysis_mode_label(match_threshold)
    return (
        "Выберите режим анализа:\n"
        f"Сейчас: {current}.\n"
        "• Точный — строгие совпадения по компаниям.\n"
        "• Умный — учитывает контекст и допускает близкие совпадения."
    )
