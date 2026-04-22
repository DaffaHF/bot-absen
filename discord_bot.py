"""
Bot Discord untuk absensi otomatis di Student Portal Amikom Purwokerto.
Versi Modern: Menggunakan Slash Commands (/) & UI Modals.
"""

import discord
from discord import app_commands
from discord.ext import commands
import logging
import asyncio
from amikom_client import AmikomClient
from config import DISCORD_BOT_TOKEN

# Logging setup
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Intents (Minimal, karena Slash Commands tidak butuh message_content intent)
intents = discord.Intents.default()

# Bot Setup
class AmikomBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents, help_command=None)
        
    async def setup_hook(self):
        # Sinkronisasi Slash Commands ke Discord saat bot menyala
        logger.info("Syncing slash commands...")
        await self.tree.sync()
        logger.info("Slash commands synced globally.")

bot = AmikomBot()

# Database Sementara (In-Memory)
# user_id -> {"nim": str, "password": str, "client": AmikomClient}
user_data: dict[int, dict] = {}


# ======================================================================
# HELPERS
# ======================================================================

async def ensure_login(user_id: int) -> AmikomClient | None:
    """Pastikan user sudah login, re-login jika session expired."""
    entry = user_data.get(user_id)
    if not entry or not entry.get("nim"):
        return None

    client = entry.get("client")
    if client and client.logged_in:
        try:
            client.get_makul_belum_validasi()
            return client
        except Exception:
            pass

    # Re-login di background
    client = AmikomClient()
    loop = asyncio.get_event_loop()
    success = await loop.run_in_executor(None, client.login, entry["nim"], entry["password"])
    if success:
        entry["client"] = client
        return client
    return None


# ======================================================================
# UI MODALS
# ======================================================================

class LoginModal(discord.ui.Modal, title='Login Portal Amikom'):
    """Pop-up form aman untuk memasukkan NIM dan Password."""
    
    nim = discord.ui.TextInput(
        label='NIM Mahasiswa',
        placeholder='Contoh: 24SA31A022',
        required=True,
        max_length=20,
    )

    password = discord.ui.TextInput(
        label='Password Portal',
        placeholder='Masukkan password Anda',
        required=True,
        style=discord.TextStyle.short,
    )

    async def on_submit(self, interaction: discord.Interaction):
        # Beritahu Discord bahwa kita sedang memproses agar tidak time-out
        await interaction.response.defer(ephemeral=True)
        
        user_id = interaction.user.id
        nim_val = self.nim.value.strip()
        pass_val = self.password.value.strip()

        # Inisialisasi client
        client = AmikomClient()
        
        # Eksekusi login secara asynchronous agar bot tidak freeze
        loop = asyncio.get_event_loop()
        login_success = await loop.run_in_executor(None, client.login, nim_val, pass_val)
        
        if login_success:
            user_data[user_id] = {
                "nim": nim_val,
                "password": pass_val,
                "client": client
            }
            # Ambil data profil setelah login
            info = await loop.run_in_executor(None, client.get_student_info)
            
            embed = discord.Embed(title="✅ Login Berhasil!", color=discord.Color.green())
            embed.add_field(name="Nama", value=f"**{info['nama']}**", inline=False)
            embed.add_field(name="NIM", value=f"`{nim_val}`", inline=False)
            embed.add_field(name="Semester Aktif", value=f"{info['semester']} ({info['thn_akademik']})", inline=True)
            embed.add_field(name="IPK", value="*(Data belum dirilis/AJAX)*", inline=True)
            
            await interaction.followup.send(
                content="Sesi Anda telah diamankan. Gunakan perintah `/status` atau `/absen`.",
                embed=embed,
                ephemeral=True
            )
        else:
            await interaction.followup.send(
                "❌ **Login gagal!**\nPastikan NIM dan Password yang Anda masukkan benar.",
                ephemeral=True
            )


# ======================================================================
# SLASH COMMANDS
# ======================================================================

@bot.event
async def on_ready():
    logger.info(f"Bot {bot.user} siap digunakan dan berjalan dengan Slash Commands!")


@bot.tree.command(name="start", description="Mulai dan registrasi akun portal Amikom")
async def start_cmd(interaction: discord.Interaction):
    """Memanggil pop-up UI Modal untuk login secara rahasia."""
    # Memunculkan form pop-up login
    await interaction.response.send_modal(LoginModal())


@bot.tree.command(name="profile", description="Lihat profil mahasiswa Anda")
async def profile_cmd(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    
    user_id = interaction.user.id
    client = await ensure_login(user_id)
    entry = user_data.get(user_id)

    if not client or not entry:
        await interaction.followup.send("⚠️ Anda belum login. Silakan gunakan perintah `/start` terlebih dahulu.", ephemeral=True)
        return

    info = await asyncio.get_event_loop().run_in_executor(None, client.get_student_info)
    
    embed = discord.Embed(title="🎓 Profil Mahasiswa Amikom", color=discord.Color.blue())
    embed.add_field(name="Nama", value=f"**{info['nama']}**", inline=False)
    embed.add_field(name="NIM", value=f"`{entry['nim']}`", inline=False)
    embed.add_field(name="Semester Aktif", value=f"{info['semester']} ({info['thn_akademik']})", inline=True)
    embed.add_field(name="IPK", value="*(Data belum dirilis/AJAX)*", inline=True)
    
    await interaction.followup.send(embed=embed, ephemeral=True)


@bot.tree.command(name="matkul", description="Lihat daftar mata kuliah Anda")
async def matkul_cmd(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    
    user_id = interaction.user.id
    client = await ensure_login(user_id)

    if not client:
        await interaction.followup.send("⚠️ Anda belum login. Silakan gunakan perintah `/start` terlebih dahulu.", ephemeral=True)
        return

    info = await asyncio.get_event_loop().run_in_executor(None, client.get_student_info)
    
    embed = discord.Embed(title="📚 Daftar Mata Kuliah", color=discord.Color.orange())
    
    matkul_text = ""
    for idx, mk in enumerate(info['matkul'], start=1):
        matkul_text += f"{idx}. {mk}\n"
        
    if matkul_text:
        embed.description = matkul_text
    else:
        embed.description = "*Tidak ada data mata kuliah.*"
        
    await interaction.followup.send(embed=embed, ephemeral=True)


@bot.tree.command(name="status", description="Cek daftar presensi yang belum divalidasi")
async def status_cmd(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    
    user_id = interaction.user.id
    client = await ensure_login(user_id)

    if not client:
        await interaction.followup.send("⚠️ Anda belum login. Silakan gunakan perintah `/start` terlebih dahulu.", ephemeral=True)
        return

    # Ambil data
    loop = asyncio.get_event_loop()
    belum = await loop.run_in_executor(None, client.get_makul_belum_validasi)

    if not belum:
        await interaction.followup.send("✅ **Semua presensi sudah divalidasi!**\nTidak ada yang pending hari ini.", ephemeral=True)
        return

    msg = "📋 **Presensi Belum Validasi:**\n\n"
    total = 0
    for item in belum:
        count = item["count"]
        total += int(count) if str(count).isdigit() else 0
        msg += f"• **{item['makul']}** — {count} pertemuan\n"

    msg += f"\n📊 Total: **{total}** presensi belum validasi\nGunakan `/absen` untuk menyelesaikan semua secara otomatis."
    
    await interaction.followup.send(msg, ephemeral=True)


@bot.tree.command(name="absen", description="Validasi otomatis SEMUA presensi yang tertunda")
async def absen_cmd(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    
    user_id = interaction.user.id
    client = await ensure_login(user_id)

    if not client:
        await interaction.followup.send("⚠️ Anda belum login. Silakan gunakan perintah `/start`.", ephemeral=True)
        return

    loop = asyncio.get_event_loop()
    belum = await loop.run_in_executor(None, client.get_makul_belum_validasi)
    
    if not belum:
        await interaction.followup.send("✅ Tidak ada presensi yang perlu divalidasi saat ini.", ephemeral=True)
        return

    total_belum = sum(int(b["count"]) for b in belum if str(b["count"]).isdigit())
    await interaction.followup.send(f"⏳ **Memproses validasi {total_belum} presensi...** Mohon tunggu sebentar.", ephemeral=True)

    # Lakukan validasi
    result = await loop.run_in_executor(None, client.validasi_semua)

    msg = "📊 **Hasil Validasi Absensi:**\n\n"
    if result["detail"]:
        for line in result["detail"]:
            msg += f"{line}\n"
        msg += "\n"

    msg += f"✅ Sukses: **{result['sukses']}**\n"
    msg += f"❌ Gagal: **{result['gagal']}**\n"

    if result["sukses"] > 0 and result["gagal"] == 0:
        msg += "\n🎉 Semua presensi berhasil divalidasi!"
        
    # Karena pesan sebelumnya sudah di-send via followup, kita kirim pesan hasil baru
    await interaction.followup.send(msg, ephemeral=True)


@bot.tree.command(name="logout", description="Hapus sesi dan kredensial Anda dari memori bot")
async def logout_cmd(interaction: discord.Interaction):
    user_id = interaction.user.id
    if user_id in user_data:
        del user_data[user_id]
        await interaction.response.send_message("✅ **Logout berhasil!** Data NIM dan sesi Anda telah dihapus secara permanen.", ephemeral=True)
    else:
        await interaction.response.send_message("⚠️ Anda memang belum login.", ephemeral=True)


@bot.tree.command(name="help", description="Tampilkan panduan penggunaan bot")
async def help_cmd(interaction: discord.Interaction):
    msg = (
        "🎓 **Bot Absensi Amikom Purwokerto (Versi Modern)**\n\n"
        "Bot ini beroperasi menggunakan **Slash Commands** (`/`) yang bersifat rahasia (hanya Anda yang bisa melihat responnya).\n\n"
        "**Daftar Perintah:**\n"
        "• `/start` — Buka form pop-up untuk Login aman\n"
        "• `/profile` — Lihat profil Anda\n"
        "• `/matkul` — Lihat daftar mata kuliah Anda semester ini\n"
        "• `/status` — Cek daftar matkul yang belum divalidasi\n"
        "• `/absen` — Langsung validasi semua presensi\n"
        "• `/logout` — Hapus memori akun Anda dari bot\n\n"
        "**Catatan Keamanan:**\n"
        "Dengan UI Modals, password Anda tidak akan pernah tersimpan di riwayat obrolan channel maupun DM Anda!"
    )
    await interaction.response.send_message(msg, ephemeral=True)


if __name__ == "__main__":
    if DISCORD_BOT_TOKEN and DISCORD_BOT_TOKEN != "your_discord_token_here":
        try:
            bot.run(DISCORD_BOT_TOKEN)
        except Exception as e:
            logger.error(f"Failed to start bot: {e}")
    else:
        print("Silakan isi DISCORD_BOT_TOKEN di config.py")
