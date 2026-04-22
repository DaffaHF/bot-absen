"""
UI Components: Modal, View, dan Embed untuk Discord interactions.
Memisahkan UI logic dari command handler.
"""

import discord
from discord import ui
import logging
from collections.abc import Awaitable, Callable

logger = logging.getLogger(__name__)

ButtonHandler = Callable[[discord.Interaction], Awaitable[None]]
LoginHandler = Callable[[discord.Interaction, str, str], Awaitable[None]]


class LoginModal(ui.Modal, title='Login Portal Amikom'):
    """Form modal untuk login ke portal Amikom secara aman (tidak tersimpan di chat)."""
    
    nim = ui.TextInput(
        label='NIM Mahasiswa',
        placeholder='Contoh: 24SA31A022',
        required=True,
        max_length=20,
    )

    password = ui.TextInput(
        label='Password Portal',
        placeholder='Masukkan password Anda',
        required=True,
        style=discord.TextStyle.short,
    )

    def __init__(self, on_submit_handler: LoginHandler):
        super().__init__()
        self.on_submit_handler = on_submit_handler

    async def on_submit(self, interaction: discord.Interaction):
        """Handle submit modal login."""
        await self.on_submit_handler(
            interaction,
            self.nim.value.strip(),
            self.password.value.strip(),
        )


class AmikomDashboard(ui.View):
    """Dashboard view dengan tombol aksi untuk presensi."""
    
    def __init__(
        self,
        discord_user_id: int,
        status_handler: ButtonHandler,
        absen_handler: ButtonHandler,
        profil_handler: ButtonHandler,
        timeout: int = 300,
    ):
        """
        Inisialisasi dashboard.
        
        Args:
            discord_user_id: ID user Discord pemilik dashboard (untuk access control).
            timeout: Timeout dalam detik sebelum tombol di-disable (default 5 menit).
        """
        super().__init__(timeout=timeout)
        self.discord_user_id = discord_user_id
        self.status_handler = status_handler
        self.absen_handler = absen_handler
        self.profil_handler = profil_handler
        self.message: discord.Message | None = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """
        Validasi: hanya pemilik dashboard yang bisa klik tombol.
        
        Returns:
            True jika interaction author adalah pemilik, False sebaliknya.
        """
        if interaction.user.id != self.discord_user_id:
            await interaction.response.send_message(
                "❌ Dashboard ini bukan milikmu. Gunakan `/absen` di akun Discord milikmu sendiri.",
                ephemeral=True
            )
            return False
        return True

    async def on_timeout(self) -> None:
        """Disable semua button saat timeout."""
        if self.message:
            try:
                for item in self.children:
                    item.disabled = True
                await self.message.edit(view=self)
                logger.info(f"Dashboard for user {self.discord_user_id} timeout - buttons disabled")
            except discord.NotFound:
                pass
            except Exception as e:
                logger.warning(f"AmikomDashboard.on_timeout: {e}")

    async def on_error(self, interaction: discord.Interaction, error: Exception, item: ui.Item) -> None:
        """Handle error dalam button callback."""
        logger.error(f"AmikomDashboard button error for user {self.discord_user_id}: {error}")
        try:
            await interaction.response.send_message(
                f"❌ Terjadi kesalahan: {str(error)[:100]}",
                ephemeral=True
            )
        except discord.HTTPException:
            pass

    @ui.button(label='📋 Status', style=discord.ButtonStyle.blurple, emoji='📋')
    async def status_button(self, interaction: discord.Interaction, button: ui.Button):
        """Tombol untuk lihat status presensi belum validasi."""
        await self.status_handler(interaction)


    @ui.button(label='✅ Absen Semua', style=discord.ButtonStyle.green, emoji='✅')
    async def absen_button(self, interaction: discord.Interaction, button: ui.Button):
        """Tombol untuk validasi semua presensi otomatis."""
        await self.absen_handler(interaction)


    @ui.button(label='👤 Profil', style=discord.ButtonStyle.secondary, emoji='👤')
    async def profil_button(self, interaction: discord.Interaction, button: ui.Button):
        """Tombol untuk lihat profil user."""
        await self.profil_handler(interaction)


def create_login_success_embed(nama: str, nim: str, semester: str, thn_akademik: str) -> discord.Embed:
    """
    Buat embed untuk display hasil login berhasil.
    
    Returns:
        discord.Embed dengan info user.
    """
    embed = discord.Embed(
        title="✅ Login Berhasil!",
        color=discord.Color.green(),
        description="Sesi Anda telah tersimpan dengan aman."
    )
    embed.add_field(name="Nama", value=f"**{nama}**", inline=False)
    embed.add_field(name="NIM", value=f"`{nim}`", inline=False)
    embed.add_field(name="Semester Aktif", value=f"{semester} ({thn_akademik})", inline=True)
    embed.set_footer(text="Gunakan dashboard di bawah atau command lainnya untuk melanjutkan.")
    return embed


def create_dashboard_embed(nama: str, nim: str) -> discord.Embed:
    """Buat embed dashboard utama dengan style Amikom (ungu/emas)."""
    embed = discord.Embed(
        title="Amikom Dashboard",
        description=(
            "Pilih aksi dari tombol di bawah untuk mengelola presensi Anda dengan cepat."
        ),
        color=discord.Color.from_str("#6A0DAD"),
    )
    embed.add_field(name="Mahasiswa", value=f"**{nama or '-'}**", inline=False)
    embed.add_field(name="NIM", value=f"`{nim}`", inline=True)
    embed.add_field(name="Tema", value="Ungu / Emas", inline=True)
    embed.set_footer(text="Tip: gunakan /help untuk daftar command lengkap.")
    return embed


def create_profile_embed(nama: str, nim: str, semester: str, thn_akademik: str) -> discord.Embed:
    """Buat embed profil user."""
    embed = discord.Embed(
        title="🎓 Profil Mahasiswa Amikom",
        color=discord.Color.blue()
    )
    embed.add_field(name="Nama", value=f"**{nama}**", inline=False)
    embed.add_field(name="NIM", value=f"`{nim}`", inline=False)
    embed.add_field(name="Semester Aktif", value=f"{semester} ({thn_akademik})", inline=True)
    return embed


def create_matkul_embed(matkul_list: list[str]) -> discord.Embed:
    """Buat embed daftar mata kuliah."""
    embed = discord.Embed(
        title="📚 Daftar Mata Kuliah",
        color=discord.Color.orange()
    )
    
    if not matkul_list:
        embed.description = "*Tidak ada data mata kuliah.*"
    else:
        matkul_text = "\n".join(f"{idx}. {mk}" for idx, mk in enumerate(matkul_list, 1))
        embed.description = matkul_text
    
    return embed


def create_status_embed(belum: list[dict]) -> discord.Embed:
    """Buat embed status presensi belum validasi."""
    embed = discord.Embed(
        title="📋 Presensi Belum Validasi",
        color=discord.Color.warning()
    )
    
    if not belum:
        embed.description = "✅ **Semua presensi sudah divalidasi!**"
    else:
        msg = ""
        total = 0
        for item in belum:
            count = item.get("count", 0)
            total += int(count) if isinstance(count, int) else 0
            msg += f"• **{item.get('makul', '?')}** — {count} pertemuan\n"
        
        msg += f"\n📊 Total: **{total}** presensi belum validasi"
        embed.description = msg
    
    return embed
