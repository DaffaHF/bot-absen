"""
Service layer untuk orchestration data portal Amikom + database user.
Memisahkan business logic dari Discord command handlers.
"""

import asyncio
import logging
from core.amikom_client import AmikomClient
from core.database import Database

logger = logging.getLogger(__name__)


class AmikomService:
    """Use-case layer untuk fitur absensi Amikom."""

    def __init__(self, db: Database):
        self.db = db

    async def _run_blocking(self, func, *args):
        """Jalankan operasi blocking di thread executor."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, func, *args)

    async def ensure_login(self, user_id: int) -> tuple[AmikomClient | None, dict | None]:
        """
        Pastikan user bisa login menggunakan kredensial tersimpan.

        Returns:
            Tuple (client, user_data). client None jika gagal login.
        """
        user_data = self.db.get_user(user_id)
        if not user_data or not user_data.get("nim"):
            return None, user_data

        client = AmikomClient()
        try:
            success = await self._run_blocking(
                client.login,
                user_data["nim"],
                user_data["password"],
            )
            if not success:
                return None, user_data
            return client, user_data
        except Exception as exc:
            logger.error("AmikomService.ensure_login: %s", exc)
            return None, user_data

    async def authenticate_and_save(self, user_id: int, nim: str, password: str) -> dict:
        """
        Login ke portal lalu simpan kredensial user jika berhasil.

        Returns:
            dict berisi success, reason, dan info (opsional).
        """
        client = AmikomClient()
        try:
            login_success = await self._run_blocking(client.login, nim, password)
        except Exception as exc:
            logger.error("AmikomService.authenticate_and_save.login: %s", exc)
            return {"success": False, "reason": "login_error", "error": str(exc)}

        if not login_success:
            return {"success": False, "reason": "invalid_credentials"}

        try:
            info = await self._run_blocking(client.get_student_info)
            saved = self.db.save_user(user_id, nim, password, info.get("nama", ""))
            if not saved:
                return {
                    "success": False,
                    "reason": "save_failed",
                    "info": info,
                }
            return {
                "success": True,
                "reason": "ok",
                "info": info,
            }
        except Exception as exc:
            logger.error("AmikomService.authenticate_and_save.info: %s", exc)
            return {
                "success": False,
                "reason": "info_error",
                "error": str(exc),
            }

    async def get_profile(self, user_id: int) -> dict | None:
        """Ambil profil mahasiswa user yang sudah login."""
        client, user_data = await self.ensure_login(user_id)
        if not client:
            return None

        info = await self._run_blocking(client.get_student_info)
        return {
            "nama": info.get("nama", ""),
            "nim": (user_data or {}).get("nim", "?"),
            "semester": info.get("semester", "?"),
            "thn_akademik": info.get("thn_akademik", "?"),
        }

    async def get_matkul(self, user_id: int) -> list[str] | None:
        """Ambil list mata kuliah user yang sudah login."""
        client, _ = await self.ensure_login(user_id)
        if not client:
            return None

        info = await self._run_blocking(client.get_student_info)
        return info.get("matkul", [])

    async def get_pending_status(self, user_id: int) -> list[dict] | None:
        """Ambil status presensi yang belum divalidasi."""
        client, _ = await self.ensure_login(user_id)
        if not client:
            return None

        return await self._run_blocking(client.get_makul_belum_validasi)

    async def validate_all_pending(self, user_id: int) -> dict | None:
        """
        Validasi semua presensi pending.

        Returns:
            None jika user belum login, atau dict hasil validasi.
        """
        client, _ = await self.ensure_login(user_id)
        if not client:
            return None

        pending = await self._run_blocking(client.get_makul_belum_validasi)
        total_pending = 0
        for item in pending:
            try:
                total_pending += int(item.get("count", 0))
            except (TypeError, ValueError):
                continue

        if total_pending == 0:
            return {
                "has_pending": False,
                "total_pending": 0,
                "result": {"sukses": 0, "gagal": 0, "detail": []},
            }

        result = await self._run_blocking(client.validasi_semua)
        return {
            "has_pending": True,
            "total_pending": total_pending,
            "result": result,
        }