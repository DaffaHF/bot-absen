#!/usr/bin/env python3
"""
Entry point untuk menjalankan Bot Discord Absensi Amikom.
Script ini menambahkan project root ke PYTHONPATH supaya import relative bekerja.
"""

import sys
import os
import asyncio
import logging

# Add project root ke sys.path agar relative import bekerja
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import main function dari bot module
from bot.main import main

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


if __name__ == "__main__":
    """Entry point untuk bot. Jalankan dengan: python run_bot.py"""
    try:
        logger.info("Bot starting...")
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)
