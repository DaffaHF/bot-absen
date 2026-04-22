"""
Bot Telegram untuk absensi otomatis di Student Portal Amikom Purwokerto.

Commands:
  /start          - Mulai dan registrasi NIM + Password
  /login          - Login ulang ke portal
  /logout         - Logout dan hapus data sesi
  /status         - Cek presensi yang belum divalidasi
  /absen          - Validasi semua presensi yang belum divalidasi
  /help           - Tampilkan bantuan
"""

import logging
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from amikom_client import AmikomClient
from config import TELEGRAM_BOT_TOKEN

# Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Conversation states
INPUT_NIM, INPUT_PASSWORD = range(2)

# Per-user storage: chat_id -> {"nim": str, "password": str, "client": AmikomClient}
user_data: dict[int, dict] = {}


# ======================================================================
# HELPERS
# ======================================================================

def get_client(chat_id: int) -> AmikomClient | None:
    """Ambil client yang sudah login untuk user tertentu."""
    entry = user_data.get(chat_id)
    if entry and entry.get("client") and entry["client"].logged_in:
        return entry["client"]
    return None


async def ensure_login(chat_id: int) -> AmikomClient | None:
    """Pastikan user sudah login, re-login jika session expired."""
    entry = user_data.get(chat_id)
    if not entry or not entry.get("nim"):
        return None

    client = entry.get("client")
    if client and client.logged_in:
        # Coba test session masih valid dengan request ringan
        try:
            belum = client.get_makul_belum_validasi()
            # Jika response kosong bukan berarti error, bisa saja memang kosong
            return client
        except Exception:
            pass

    # Re-login
    client = AmikomClient()
    if client.login(entry["nim"], entry["password"]):
        entry["client"] = client
        return client
    return None


# ======================================================================
# COMMAND HANDLERS
# ======================================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handler /start — mulai registrasi."""
    await update.message.reply_text(
        "🎓 *Bot Absensi Amikom Purwokerto*\n\n"
        "Bot ini membantu validasi presensi kehadiran secara otomatis.\n\n"
        "Silakan masukkan *NIM* Anda:",
        parse_mode="Markdown",
    )
    return INPUT_NIM


async def input_nim(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Terima input NIM dari user."""
    nim = update.message.text.strip()
    chat_id = update.message.chat_id

    if chat_id not in user_data:
        user_data[chat_id] = {}
    user_data[chat_id]["nim"] = nim

    await update.message.reply_text(
        f"NIM: `{nim}`\n\nSekarang masukkan *Password* Anda:",
        parse_mode="Markdown",
    )
    return INPUT_PASSWORD


async def input_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Terima input password, langsung login."""
    password = update.message.text.strip()
    chat_id = update.message.chat_id

    user_data[chat_id]["password"] = password

    # Hapus pesan password dari chat untuk keamanan
    try:
        await update.message.delete()
    except Exception:
        pass

    await update.message.reply_text("⏳ Mencoba login ke portal...")

    client = AmikomClient()
    nim = user_data[chat_id]["nim"]

    if client.login(nim, password):
        user_data[chat_id]["client"] = client
        await update.message.reply_text(
            f"✅ *Login berhasil!*\n\n"
            f"NIM: `{nim}`\n\n"
            f"Gunakan perintah:\n"
            f"• /status — Cek presensi belum validasi\n"
            f"• /absen — Validasi semua presensi\n"
            f"• /login — Login ulang\n"
            f"• /help — Bantuan",
            parse_mode="Markdown",
        )
    else:
        await update.message.reply_text(
            "❌ *Login gagal!*\n\n"
            "Periksa NIM dan password Anda.\n"
            "Gunakan /start untuk mencoba lagi.",
            parse_mode="Markdown",
        )

    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel conversation."""
    await update.message.reply_text(
        "❌ Dibatalkan. Gunakan /start untuk memulai lagi.",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END


async def login_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler /login — login ulang."""
    chat_id = update.message.chat_id
    entry = user_data.get(chat_id)

    if not entry or not entry.get("nim"):
        await update.message.reply_text(
            "⚠️ Anda belum registrasi. Gunakan /start terlebih dahulu."
        )
        return

    await update.message.reply_text("⏳ Mencoba login ulang...")

    client = AmikomClient()
    if client.login(entry["nim"], entry["password"]):
        entry["client"] = client
        await update.message.reply_text("✅ Login ulang berhasil!")
    else:
        await update.message.reply_text(
            "❌ Login gagal. Gunakan /start untuk registrasi ulang."
        )


async def logout_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler /logout — logout dan hapus data sesi."""
    chat_id = update.message.chat_id

    if chat_id in user_data:
        del user_data[chat_id]
        await update.message.reply_text(
            "✅ *Logout berhasil!*\n\n"
            "Data NIM dan sesi Anda telah dihapus.\n"
            "Gunakan /start untuk login kembali.",
            parse_mode="Markdown",
        )
    else:
        await update.message.reply_text(
            "⚠️ Anda belum login. Gunakan /start untuk registrasi."
        )


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler /status — cek presensi yang belum divalidasi."""
    chat_id = update.message.chat_id
    client = await ensure_login(chat_id)

    if not client:
        await update.message.reply_text(
            "⚠️ Anda belum login. Gunakan /start untuk registrasi."
        )
        return

    await update.message.reply_text("⏳ Mengecek status presensi...")

    belum = client.get_makul_belum_validasi()

    if not belum:
        await update.message.reply_text(
            "✅ *Semua presensi sudah divalidasi!*\n\n"
            "Tidak ada presensi yang perlu divalidasi saat ini.",
            parse_mode="Markdown",
        )
        return

    msg = "📋 *Presensi Belum Validasi:*\n\n"
    total = 0
    for item in belum:
        count = item["count"]
        total += int(count) if str(count).isdigit() else 0
        msg += f"• *{item['makul']}* — {count} pertemuan\n"

    msg += f"\n📊 Total: *{total}* presensi belum validasi\n"
    msg += f"\nGunakan /absen untuk validasi semua."

    await update.message.reply_text(msg, parse_mode="Markdown")


async def absen_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler /absen — validasi semua presensi yang belum divalidasi."""
    chat_id = update.message.chat_id
    client = await ensure_login(chat_id)

    if not client:
        await update.message.reply_text(
            "⚠️ Anda belum login. Gunakan /start untuk registrasi."
        )
        return

    # Cek dulu apakah ada yang perlu divalidasi
    belum = client.get_makul_belum_validasi()
    if not belum:
        await update.message.reply_text(
            "✅ Tidak ada presensi yang perlu divalidasi saat ini."
        )
        return

    total_belum = sum(int(b["count"]) for b in belum if str(b["count"]).isdigit())
    status_msg = await update.message.reply_text(
        f"⏳ Memproses validasi *{total_belum}* presensi...\n"
        f"Mohon tunggu, ini mungkin memakan waktu beberapa detik.",
        parse_mode="Markdown",
    )

    # Jalankan validasi
    result = client.validasi_semua()

    # Bangun pesan hasil
    msg = "📊 *Hasil Validasi Presensi:*\n\n"

    if result["detail"]:
        for line in result["detail"]:
            msg += f"{line}\n"
        msg += "\n"

    msg += f"✅ Sukses: *{result['sukses']}*\n"
    msg += f"❌ Gagal: *{result['gagal']}*\n"

    if result["sukses"] > 0 and result["gagal"] == 0:
        msg += "\n🎉 Semua presensi berhasil divalidasi!"
    elif result["gagal"] > 0:
        msg += "\n⚠️ Beberapa presensi gagal. Coba /absen lagi nanti."

    await status_msg.edit_text(msg, parse_mode="Markdown")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler /help."""
    await update.message.reply_text(
        "🎓 *Bot Absensi Amikom Purwokerto*\n\n"
        "*Perintah:*\n"
        "• /start — Registrasi NIM & Password\n"
        "• /login — Login ulang ke portal\n"
        "• /logout — Logout & hapus data sesi\n"
        "• /status — Cek presensi belum validasi\n"
        "• /absen — Validasi semua presensi\n"
        "• /help — Tampilkan bantuan ini\n\n"
        "*Cara kerja:*\n"
        "1. Registrasi dengan /start\n"
        "2. Cek status dengan /status\n"
        "3. Validasi dengan /absen\n\n"
        "Bot akan otomatis mengisi form validasi dengan:\n"
        "• Dosen hadir: ✅ Benar\n"
        "• Materi sesuai: ✅ Ya\n"
        "• Penilaian: ⭐ Sangat Baik",
        parse_mode="Markdown",
    )


# ======================================================================
# MAIN
# ======================================================================

def main() -> None:
    """Start the bot."""
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Conversation handler untuk registrasi /start
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            INPUT_NIM: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_nim)],
            INPUT_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_password)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("login", login_command))
    app.add_handler(CommandHandler("logout", logout_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("absen", absen_command))
    app.add_handler(CommandHandler("help", help_command))

    logger.info("Bot started! Polling...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
