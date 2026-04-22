"""
Slash Commands untuk Bot Discord Absensi Amikom.
Memisahkan command logic dari bot main class.
"""

import discord
from discord import app_commands
from discord.ext import commands
import logging
from core.database import Database
from core.amikom_service import AmikomService
from bot.ui import (
    LoginModal,
    AmikomDashboard,
    create_login_success_embed,
    create_profile_embed,
    create_matkul_embed,
    create_status_embed,
    create_dashboard_embed,
)
from bot.messages import (
    privacy_summary_message,
    delete_me_confirmation_message,
    help_message,
)

logger = logging.getLogger(__name__)


class Amikom(commands.Cog):
    """Cog untuk Slash Commands Absensi Amikom Purwokerto."""

    def __init__(self, bot: commands.Bot, db: Database):
        """
        Inisialisasi cog dengan bot instance dan database.
        
        Args:
            bot: Discord bot instance.
            db: Database instance untuk penyimpanan multi-user.
        """
        self.bot = bot
        self.db = db
        self.service = AmikomService(db)

    async def _send_requires_login(self, interaction: discord.Interaction) -> None:
        """Kirim pesan standar jika user belum login."""
        await interaction.followup.send(
            "⚠️ Anda belum login. Silakan gunakan perintah `/start` terlebih dahulu.",
            ephemeral=True,
        )

    async def _show_profile(self, interaction: discord.Interaction) -> None:
        """Render profil mahasiswa untuk slash command atau dashboard button."""
        user_id = interaction.user.id
        try:
            profile = await self.service.get_profile(user_id)
        except Exception as e:
            logger.error(f"_show_profile: {e}")
            await interaction.followup.send(f"❌ Gagal ambil profil: {str(e)[:100]}", ephemeral=True)
            return

        if not profile:
            await self._send_requires_login(interaction)
            return

        embed = create_profile_embed(
            profile.get("nama", ""),
            profile.get("nim", "?"),
            profile.get("semester", "?"),
            profile.get("thn_akademik", "?"),
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

    async def _show_status(self, interaction: discord.Interaction) -> None:
        """Render status presensi pending untuk slash command atau dashboard button."""
        user_id = interaction.user.id
        try:
            belum = await self.service.get_pending_status(user_id)
        except Exception as e:
            logger.error(f"_show_status: {e}")
            await interaction.followup.send(f"❌ Gagal ambil status: {str(e)[:100]}", ephemeral=True)
            return

        if belum is None:
            await self._send_requires_login(interaction)
            return

        embed = create_status_embed(belum)
        await interaction.followup.send(embed=embed, ephemeral=True)

    async def _run_absen_all(self, interaction: discord.Interaction) -> None:
        """Eksekusi validasi semua presensi untuk slash command atau dashboard button."""
        user_id = interaction.user.id
        try:
            validation = await self.service.validate_all_pending(user_id)
        except Exception as e:
            logger.error(f"_run_absen_all: {e}")
            await interaction.followup.send(f"❌ Gagal validasi: {str(e)[:100]}", ephemeral=True)
            return

        if validation is None:
            await self._send_requires_login(interaction)
            return

        if not validation.get("has_pending", False):
            await interaction.followup.send(
                "✅ Tidak ada presensi yang perlu divalidasi saat ini.",
                ephemeral=True,
            )
            return

        await interaction.followup.send(
            f"⏳ **Memproses validasi {validation.get('total_pending', 0)} presensi...** Mohon tunggu sebentar.",
            ephemeral=True,
        )

        result = validation.get("result", {})
        msg = "📊 **Hasil Validasi Absensi:**\n\n"
        if result.get("detail"):
            for line in result["detail"][:20]:
                msg += f"{line}\n"
            if len(result.get("detail", [])) > 20:
                msg += f"\n... dan {len(result['detail']) - 20} item lainnya.\n"

        msg += f"\n✅ Sukses: **{result.get('sukses', 0)}**\n"
        msg += f"❌ Gagal: **{result.get('gagal', 0)}**\n"
        await interaction.followup.send(msg, ephemeral=True)

    async def _handle_start_modal_submit(
        self,
        interaction: discord.Interaction,
        nim_val: str,
        pass_val: str,
    ) -> None:
        """Proses submit modal login lalu tampilkan dashboard interaktif."""
        await interaction.response.defer(ephemeral=True)

        auth_result = await self.service.authenticate_and_save(
            interaction.user.id,
            nim_val,
            pass_val,
        )

        if not auth_result.get("success") and auth_result.get("reason") == "login_error":
            err = auth_result.get("error", "unknown error")
            await interaction.followup.send(f"❌ Gagal login: {str(err)[:100]}", ephemeral=True)
            return

        if not auth_result.get("success") and auth_result.get("reason") == "invalid_credentials":
            await interaction.followup.send(
                "❌ **Login gagal!**\nPastikan NIM dan Password yang Anda masukkan benar.",
                ephemeral=True,
            )
            return

        if not auth_result.get("success") and auth_result.get("reason") == "save_failed":
            await interaction.followup.send(
                "✅ Login berhasil tapi gagal menyimpan data. Coba `/start` lagi.",
                ephemeral=True,
            )
            return

        if not auth_result.get("success"):
            await interaction.followup.send(
                "✅ Login berhasil tapi gagal memuat dashboard. Gunakan command slash seperti `/status`.",
                ephemeral=True,
            )
            return

        info = auth_result.get("info", {})
        embed = create_login_success_embed(
            info.get("nama", ""),
            nim_val,
            info.get("semester", "?"),
            info.get("thn_akademik", "?"),
        )
        dashboard_embed = create_dashboard_embed(info.get("nama", ""), nim_val)
        dashboard = AmikomDashboard(
            discord_user_id=interaction.user.id,
            status_handler=self._dashboard_status,
            absen_handler=self._dashboard_absen,
            profil_handler=self._dashboard_profile,
        )

        message = await interaction.followup.send(
            content="Sesi Anda telah diamankan di database bot.",
            embeds=[embed, dashboard_embed],
            view=dashboard,
            ephemeral=True,
        )
        dashboard.message = message

    async def _dashboard_status(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        await self._show_status(interaction)

    async def _dashboard_absen(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        await self._run_absen_all(interaction)

    async def _dashboard_profile(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        await self._show_profile(interaction)

    @app_commands.command(name="start", description="Mulai dan registrasi akun portal Amikom")
    async def start_cmd(self, interaction: discord.Interaction):
        """Memanggil form modal login untuk registrasi awal atau re-login."""
        modal = LoginModal(self._handle_start_modal_submit)
        await interaction.response.send_modal(modal)

    @app_commands.command(name="profile", description="Lihat profil mahasiswa Anda")
    async def profile_cmd(self, interaction: discord.Interaction):
        """Tampilkan profil user dari data tersimpan atau fresh dari portal."""
        await interaction.response.defer(ephemeral=True)
        await self._show_profile(interaction)

    @app_commands.command(name="matkul", description="Lihat daftar mata kuliah Anda")
    async def matkul_cmd(self, interaction: discord.Interaction):
        """Tampilkan daftar mata kuliah."""
        await interaction.response.defer(ephemeral=True)

        user_id = interaction.user.id

        try:
            matkul_list = await self.service.get_matkul(user_id)
        except Exception as e:
            logger.error(f"matkul_cmd: {e}")
            await interaction.followup.send(f"❌ Gagal ambil mata kuliah: {str(e)[:100]}", ephemeral=True)
            return

        if matkul_list is None:
            await self._send_requires_login(interaction)
            return

        embed = create_matkul_embed(matkul_list)
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="status", description="Cek daftar presensi yang belum divalidasi")
    async def status_cmd(self, interaction: discord.Interaction):
        """Tampilkan status presensi belum validasi."""
        await interaction.response.defer(ephemeral=True)
        await self._show_status(interaction)

    @app_commands.command(name="absen", description="Validasi otomatis SEMUA presensi yang tertunda")
    async def absen_cmd(self, interaction: discord.Interaction):
        """Validasi semua presensi secara otomatis."""
        await interaction.response.defer(ephemeral=True)
        await self._run_absen_all(interaction)

    @app_commands.command(name="dashboard", description="Tampilkan dashboard tombol aksi presensi")
    async def dashboard_cmd(self, interaction: discord.Interaction):
        """Tampilkan dashboard interaktif untuk user yang sudah login."""
        await interaction.response.defer(ephemeral=True)

        user_id = interaction.user.id
        user_data = self.db.get_user(user_id)
        if not user_data:
            await self._send_requires_login(interaction)
            return

        dashboard = AmikomDashboard(
            discord_user_id=user_id,
            status_handler=self._dashboard_status,
            absen_handler=self._dashboard_absen,
            profil_handler=self._dashboard_profile,
        )
        embed = create_dashboard_embed(user_data.get("nama", ""), user_data.get("nim", "?"))
        message = await interaction.followup.send(embed=embed, view=dashboard, ephemeral=True)
        dashboard.message = message

    @app_commands.command(name="logout", description="Hapus sesi dan kredensial Anda dari memori bot")
    async def logout_cmd(self, interaction: discord.Interaction):
        """Logout dan hapus data user dari database."""
        user_id = interaction.user.id
        
        if self.db.user_exists(user_id):
            if self.db.delete_user(user_id):
                await interaction.response.send_message(
                    "✅ **Logout berhasil!** Data NIM dan sesi Anda telah dihapus secara permanen.",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    "❌ Gagal menghapus data. Coba lagi nanti.",
                    ephemeral=True
                )
        else:
            await interaction.response.send_message(
                "⚠️ Anda memang belum login.",
                ephemeral=True
            )

    @app_commands.command(name="privacy", description="Lihat data apa saja yang disimpan bot untuk Anda")
    async def privacy_cmd(self, interaction: discord.Interaction):
        """Tampilkan ringkasan data yang disimpan untuk user ini."""
        await interaction.response.defer(ephemeral=True)
        
        user_id = interaction.user.id
        user_data = self.db.get_user(user_id)
        
        if not user_data:
            await interaction.followup.send(
                "📋 **Data Anda di Bot:**\n\nTidak ada data tersimpan. Silakan `/start` untuk registrasi.",
                ephemeral=True
            )
            return
        
        msg = privacy_summary_message(
            user_id=user_id,
            nim=user_data.get("nim", "?"),
            nama=user_data.get("nama", "(belum tersimpan)"),
        )
        
        await interaction.followup.send(msg, ephemeral=True)

    @app_commands.command(name="delete_me", description="Hapus semua data Anda dari bot (tidak bisa di-undo)")
    async def delete_me_cmd(self, interaction: discord.Interaction):
        """Hapus semua data user dari database (irreversible)."""
        user_id = interaction.user.id
        
        if not self.db.user_exists(user_id):
            await interaction.response.send_message(
                "⚠️ Tidak ada data Anda yang tersimpan.",
                ephemeral=True
            )
            return
        
        # Konfirmasi dua tahap
        confirm_msg = delete_me_confirmation_message()
        
        await interaction.response.send_message(confirm_msg, ephemeral=True)
        
        # Simple confirmation: user harus type HAPUS
        # Untuk phase awal, ini adalah konfirmasi manual. Bisa di-upgrade pakai button later.
        # For now, we proceed dengan simple deletion
        
        if self.db.delete_user(user_id):
            await interaction.followup.send(
                "✅ Semua data Anda telah dihapus dari bot. Untuk registrasi ulang, gunakan `/start`.",
                ephemeral=True
            )
        else:
            await interaction.followup.send(
                "❌ Gagal menghapus data. Coba lagi atau hubungi maintainer.",
                ephemeral=True
            )

    @app_commands.command(name="help", description="Tampilkan panduan penggunaan bot")
    async def help_cmd(self, interaction: discord.Interaction):
        """Tampilkan bantuan penggunaan."""
        msg = help_message()
        await interaction.response.send_message(msg, ephemeral=True)


async def setup(bot: commands.Bot, db: Database):
    """
    Setup cog ke bot.
    
    Args:
        bot: Discord bot instance.
        db: Database instance.
    """
    await bot.add_cog(Amikom(bot, db))
    logger.info("Amikom cog loaded")
