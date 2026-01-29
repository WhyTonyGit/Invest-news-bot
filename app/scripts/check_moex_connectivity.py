from __future__ import annotations

import asyncio

import aiohttp

MOEX_URL = "https://iss.moex.com/iss/engines/stock/markets/shares/securities.json"


async def main() -> None:
    timeout = aiohttp.ClientTimeout(total=10, connect=5, sock_read=5)
    try:
        async with aiohttp.ClientSession(timeout=timeout, trust_env=True) as session:
            async with session.get(MOEX_URL, params={"iss.meta": "off", "limit": 1}) as response:
                response.raise_for_status()
                await response.text()
        print("MOEX connectivity: success")
    except Exception as exc:  # noqa: BLE001
        print(f"MOEX connectivity: failed ({type(exc).__name__}: {exc})")


if __name__ == "__main__":
    asyncio.run(main())
