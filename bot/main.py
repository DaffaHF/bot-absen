"""
Main entrypoint untuk Bot Discord Absensi Amikom.
Menangani startup, database init, encryption setup, dan bot lifecycle.
"""

import discord
from discord.ext import commands
import logging
import asyncio
import os
import sys

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Import config setelah setup logging
from config import DISCORD_BOT_TOKEN, ENVIRONMENT, ENCRYPTION_KEY, DATABASE_PATH, DEBUG
from core.crypto import CryptoManager
from core.database import Database
from bot.commands import setup as setup_commands


# Bot setup dengan minimal intents (tidak perlu message_content untuk slash commands)
intents = discord.Intents.default()
intents.message_content = False  # Slash commands tidak butuh message_content


class AmikomBot(commands.Bot):
    """Custom Bot class untuk Absensi Amikom dengan lifecycle hooks."""

    def __init__(self, db: Database, **kwargs):
        """
        Inisialisasi bot custom.
        
        Args:
            db: Database instance untuk penyimpanan multi-user.
        """
        super().__init__(**kwargs)
        self.db = db

    async def setup_hook(self):
        """Setup hook: sinkronisasi slash commands dengan Discord."""
        logger.info("Syncing slash commands...")
        try:
            await self.tree.sync()
            logger.info(f"Synced {len(self.tree._get_all_commands())} slash commands globally.")
        except Exception as e:
            logger.error(f"Failed to sync slash commands: {e}")
            raise


async def main():
    """Main entry point aplikasi."""
    
    # Step 1: Validasi konfigurasi
    if not DISCORD_BOT_TOKEN or DISCORD_BOT_TOKEN == "your_discord_token_here":
        logger.error("DISCORD_BOT_TOKEN tidak ditemukan atau tidak valid. Isi di .env file.")
        sys.exit(1)

    # Step 2: Inisialisasi encryption
    logger.info(f"Environment: {ENVIRONMENT}")
    crypto = None
    
    if ENVIRONMENT == "production":
        if not ENCRYPTION_KEY:
            logger.error("Production mode: ENCRYPTION_KEY harus disetting di environment. Exit.")
            sys.exit(1)
        try:
            crypto = CryptoManager(ENCRYPTION_KEY.encode() if isinstance(ENCRYPTION_KEY, str) else ENCRYPTION_KEY)
            logger.info("Encryption enabled (production mode)")
        except Exception as e:
            logger.error(f"Gagal inisialisasi encryption: {e}")
            sys.exit(1)
    else:
        logger.warning("Development mode: encryption DISABLED. Jangan gunakan di production!")

    # Step 3: Inisialisasi database
    logger.info(f"Initializing database at {DATABASE_PATH}...")
    try:
        db = Database(db_path=DATABASE_PATH, crypto=crypto)
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        sys.exit(1)

    # Step 4: Setup bot instance
    logger.info("Setting up Discord bot...")
    bot = AmikomBot(
        db=db,
        command_prefix="!",
        intents=intents,
        help_command=None,
    )

    # Step 5: Load commands cog
    try:
        await setup_commands(bot, db)
        logger.info("Commands loaded")
    except Exception as e:
        logger.error(f"Failed to load commands: {e}")
        sys.exit(1)

    # Step 6: Bot event handlers
    @bot.event
    async def on_ready():
        logger.info(f"Bot {bot.user} siap digunakan dan berjalan dengan Slash Commands!")
        logger.info(f"Bot aktif di {len(bot.guilds)} guild(s)")

    # Step 7: Jalankan bot
    logger.info("Starting bot...")
    try:
        async with bot:
            await bot.start(DISCORD_BOT_TOKEN)
    except KeyboardInterrupt:
        logger.info("Bot interrupted by user")
    except Exception as e:
        logger.error(f"Bot error: {e}")
        sys.exit(1)
