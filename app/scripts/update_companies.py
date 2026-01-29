from __future__ import annotations

from app.scripts.refresh_companies import main


if __name__ == "__main__":
    import asyncio
    import os
    from pathlib import Path

    cache_path = Path(os.getenv("COMPANIES_CACHE_PATH", "app/data/companies_cache.json"))
    ttl_hours = int(os.getenv("COMPANIES_REFRESH_TTL_HOURS", "24"))
    asyncio.run(main(cache_path, ttl_hours))
