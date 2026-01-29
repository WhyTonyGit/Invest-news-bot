import asyncio

import pytest


try:
    import pytest_asyncio  # noqa: F401
except ModuleNotFoundError:  # pragma: no cover - optional local dependency
    pytest_asyncio = None


@pytest.fixture(scope="session")
def event_loop() -> asyncio.AbstractEventLoop:
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_settings() -> dict:
    return {
        "default_notifications_enabled": True,
        "default_quiet_hours": "23:00-07:00",
        "default_poll_seconds": 60,
        "default_match_threshold": 3,
        "default_hourly_limit": 20,
        "default_feed_mode": "watchlist",
        "default_digest_frequency": "daily",
        "summary_enabled": True,
    }


def pytest_collection_modifyitems(config, items):  # type: ignore[no-untyped-def]
    if pytest_asyncio is None:
        skip_async = pytest.mark.skip(reason="pytest-asyncio not installed")
        for item in items:
            if item.get_closest_marker("asyncio"):
                item.add_marker(skip_async)
