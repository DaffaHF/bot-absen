"""Template pesan teks untuk command Discord."""


def privacy_summary_message(user_id: int, nim: str, nama: str) -> str:
    """Bangun pesan ringkasan data privacy untuk user."""
    return (
        "📋 **Data Anda di Bot:**\n\n"
        f"• Discord ID: `{user_id}`\n"
        f"• NIM: `{nim}`\n"
        f"• Nama: {nama}\n\n"
        "**Kebijakan Data:**\n"
        "• Password disimpan terenkripsi (tidak bisa dibaca oleh admin bot).\n"
        "• Data hanya digunakan untuk validasi presensi otomatis.\n"
        "• Gunakan `/logout` atau `/delete_me` untuk menghapus data kapan saja.\n\n"
        "**Pertanyaan?** Hubungi maintainer bot."
    )


def delete_me_confirmation_message() -> str:
    """Pesan konfirmasi penghapusan permanen user."""
    return (
        "⚠️ **PERINGATAN: Aksi ini tidak bisa di-undo!**\n\n"
        "Semua data Anda akan dihapus permanen dari database bot:\n"
        "• NIM dan nama Anda\n"
        "• Password terenkripsi\n"
        "• Riwayat akses\n\n"
        "Ketik **HAPUS** di bawah untuk konfirmasi (case-sensitive)."
    )


def help_message() -> str:
    """Pesan bantuan utama bot."""
    return (
        "🎓 **Bot Absensi Amikom Purwokerto**\n\n"
        "Bot ini menggunakan **Slash Commands** (`/`) untuk interaksi yang aman dan privat.\n\n"
        "**Perintah Utama:**\n"
        "• `/start` — Buka form login untuk registrasi/re-login\n"
        "• `/dashboard` — Buka tombol cepat (Status, Absen Semua, Profil)\n"
        "• `/profile` — Lihat profil Anda dari portal Amikom\n"
        "• `/matkul` — Lihat daftar mata kuliah semester ini\n"
        "• `/status` — Cek presensi mana saja yang belum divalidasi\n"
        "• `/absen` — Validasi SEMUA presensi secara otomatis\n"
        "• `/privacy` — Lihat data apa yang disimpan untuk Anda\n"
        "• `/logout` — Hapus sesi Anda\n"
        "• `/delete_me` — Hapus SEMUA data Anda (permanent)\n\n"
        "**Catatan Keamanan:**\n"
        "✅ Password Anda dienkripsi sebelum disimpan.\n"
        "✅ Semua response bersifat ephemeral (hanya Anda yang bisa lihat).\n"
        "✅ Data dipisahkan per user Discord secara aman.\n\n"
        "Butuh bantuan? Hubungi maintainer bot."
    )