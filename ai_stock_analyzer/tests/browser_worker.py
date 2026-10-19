"""Separate worker using the same guarded, isolated providers as browser_app."""

import asyncio

from app.worker.product_worker import main
from tests import browser_app  # noqa: F401 -- installs guarded fixture providers

if __name__ == "__main__":
    asyncio.run(main())
