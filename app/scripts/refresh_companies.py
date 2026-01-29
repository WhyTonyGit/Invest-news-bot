from __future__ import annotations

import argparse
import asyncio
import os
from pathlib import Path

from app.news.directory import AlorSPBProvider, CompanyDirectoryService, MOEXProvider


async def main(cache_path: Path, ttl_hours: int) -> None:
    directory = CompanyDirectoryService(
        providers=[
            MOEXProvider(os.getenv("MOEX_ISS_BASE_URL", "https://iss.moex.com/iss")),
            AlorSPBProvider(os.getenv("ALOR_BASE_URL", "https://api.alor.ru")),
        ],
        cache_path=cache_path,
        ttl_hours=ttl_hours,
        fallback_path=Path(os.getenv("COMPANIES_DATASET_PATH", "app/data/companies.json")),
    )
    result = await directory.refresh(force=True)
    print(f"Refreshed companies cache: {result.count} records")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Refresh companies directory cache")
    parser.add_argument(
        "--cache-path",
        default=os.getenv("COMPANIES_CACHE_PATH", "app/data/companies_cache.json"),
    )
    parser.add_argument(
        "--ttl-hours",
        type=int,
        default=int(os.getenv("COMPANIES_REFRESH_TTL_HOURS", "24")),
    )
    args = parser.parse_args()
    asyncio.run(main(Path(args.cache_path), args.ttl_hours))
