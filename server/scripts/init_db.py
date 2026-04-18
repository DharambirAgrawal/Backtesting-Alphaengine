import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))
load_dotenv(ROOT / ".env")

from core.database import init_models


async def main() -> None:
    await init_models()
    print("Database schema initialized.")


if __name__ == "__main__":
    asyncio.run(main())
