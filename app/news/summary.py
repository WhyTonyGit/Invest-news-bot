from __future__ import annotations

import hashlib
import json
import logging
import re
from dataclasses import dataclass
from typing import Iterable

import aiohttp

LOGGER = logging.getLogger("news.summary")

FACT_PATTERN = re.compile(
    r"(?P<value>\\b\\d{1,3}(?:[\\s,]\\d{3})*(?:[\\.,]\\d+)?\\b\\s*(?:%|млн|млрд|тыс)?\\s*(?:руб|₽|usd|\\$|eur|€)?)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class SummaryResult:
    tldr: str
    importance: str
    facts: list[str]


def _hash_content(title: str, summary: str | None, url: str) -> str:
    base = f"{title}|{summary or ''}|{url}"
    return hashlib.sha256(base.encode("utf-8")).hexdigest()


def extract_facts(text: str) -> list[str]:
    candidates = {match.group("value").strip() for match in FACT_PATTERN.finditer(text)}
    return sorted({c for c in candidates if c})


def render_summary(result: SummaryResult, source_url: str) -> str:
    facts_block = "\n".join(f"• {fact}" for fact in result.facts) if result.facts else "• нет"
    return (
        f"<b>TL;DR</b> {result.tldr}\n"
        f"<b>Почему важно</b> {result.importance}\n"
        f"<b>Факты</b>\n{facts_block}\n"
        f"<a href=\"{source_url}\">Источник</a>"
    )


class LLMProvider:
    async def summarize(self, title: str, text: str, facts: Iterable[str]) -> SummaryResult:
        raise NotImplementedError


class OpenAILLMProvider(LLMProvider):
    def __init__(self, api_key: str, model: str, timeout: int, base_url: str | None = None) -> None:
        self._api_key = api_key
        self._model = model
        self._timeout = timeout
        self._base_url = (base_url or "https://api.openai.com").rstrip("/")

    async def summarize(self, title: str, text: str, facts: Iterable[str]) -> SummaryResult:
        prompt = (
            "Ты готовишь краткое резюме инвестиционной новости без домыслов. "
            "Используй только факты из текста и списка фактов. "
            "Верни JSON с ключами: tldr, importance, facts (массив строк)."
        )
        payload = {
            "model": self._model,
            "temperature": 0.2,
            "messages": [
                {"role": "system", "content": prompt},
                {
                    "role": "user",
                    "content": f"Заголовок: {title}\nТекст: {text}\nФакты: {list(facts)}",
                },
            ],
        }
        headers = {"Authorization": f"Bearer {self._api_key}"}
        url = f"{self._base_url}/v1/chat/completions"
        timeout = aiohttp.ClientTimeout(total=self._timeout)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, json=payload, headers=headers) as response:
                response.raise_for_status()
                data = await response.json()
        content = data["choices"][0]["message"]["content"]
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            LOGGER.warning("LLM response was not JSON, fallback to heuristic")
            raise ValueError("Invalid LLM response")
        return SummaryResult(
            tldr=str(parsed.get("tldr", "")).strip(),
            importance=str(parsed.get("importance", "")).strip(),
            facts=[str(item).strip() for item in parsed.get("facts", []) if str(item).strip()],
        )


class SummaryService:
    def __init__(self, provider: LLMProvider | None) -> None:
        self._provider = provider

    @staticmethod
    def hash_content(title: str, text: str, url: str) -> str:
        return _hash_content(title, text, url)

    async def build_summary(self, title: str, text: str, url: str) -> tuple[str, str, str]:
        facts = extract_facts(text)
        if self._provider:
            try:
                result = await self._provider.summarize(title, text, facts)
            except Exception:  # noqa: BLE001
                result = self._fallback(title, facts)
        else:
            result = self._fallback(title, facts)
        summary = render_summary(result, url)
        facts_serialized = ", ".join(result.facts)
        return summary, facts_serialized, _hash_content(title, text, url)

    @staticmethod
    def _fallback(title: str, facts: list[str]) -> SummaryResult:
        tldr = title.strip()
        importance = "Следите за деталями новости."
        return SummaryResult(tldr=tldr, importance=importance, facts=facts[:5])
