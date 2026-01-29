from __future__ import annotations

import argparse
import asyncio

from app.companies import build_company_directory
from app.config import load_settings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Refresh company directory cache")
    parser.add_argument("--force", action="store_true", help="Force refresh bypassing TTL")
    return parser.parse_args()


async def run(force: bool) -> None:
    settings = load_settings()
    directory = build_company_directory(settings)
    result = await directory.refresh(force=force)
    counts, updated_at = directory.stats()
    updated_str = updated_at.isoformat() if updated_at else "n/a"
    print(f"Updated at: {updated_str}")
    print(f"Counts: {counts}")
    if result.errors:
        print("Errors:")
        for error in result.errors:
            print(f"- {error}")


def main() -> None:
    args = parse_args()
    asyncio.run(run(args.force))


if __name__ == "__main__":
    main()
