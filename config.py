# Konfigurasi Bot Discord Absensi Amikom Purwokerto

import os
from dotenv import load_dotenv

load_dotenv()

# Discord Bot
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

# Portal Amikom
BASE_URL = "https://student.amikompurwokerto.ac.id/"

# Default jawaban form validasi presensi
DEFAULT_KESESUAIAN_PERKULIAHAN = "1"  # 1 = Benar
DEFAULT_KESESUAIAN_MATERI = "1"       # 1 = Ya sesuai
DEFAULT_PENILAIAN_MHS = "4"           # 4 = Sangat Baik
DEFAULT_KRITIK_SARAN = ""             # Kosong

# Database & Security
DATABASE_PATH = os.getenv("DATABASE_PATH", "bot_data.db")
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")  # Harus disetting untuk production mode

# Mode: "development" atau "production" (default: development)
# Production mode memerlukan ENCRYPTION_KEY yang valid
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

# Logging & Debug
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
