"""
Database layer untuk penyimpanan multi-user.
Menggunakan SQLite untuk persistensi data antar session.
Tabel: users (discord_user_id, nim, encrypted_password, updated_at)
"""

import sqlite3
import logging
from pathlib import Path
from datetime import datetime
from core.crypto import CryptoManager

logger = logging.getLogger(__name__)


class Database:
    """Manager SQLite untuk user data multi-user."""

    def __init__(self, db_path: str = "bot_data.db", crypto: CryptoManager | None = None):
        """
        Inisialisasi database.
        
        Args:
            db_path: Path ke file SQLite database.
            crypto: CryptoManager untuk enkripsi/dekripsi (optional).
        """
        self.db_path = db_path
        self.crypto = crypto
        self._init_db()

    def _init_db(self):
        """Inisialisasi database schema jika belum ada."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Tabel users: menyimpan data user terenkripsi
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        discord_user_id INTEGER PRIMARY KEY,
                        nim TEXT NOT NULL,
                        encrypted_password TEXT NOT NULL,
                        nama TEXT,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Tabel audit_log: tracking akses/perubahan data (optional untuk phase awal)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS audit_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        discord_user_id INTEGER,
                        action TEXT NOT NULL,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (discord_user_id) REFERENCES users(discord_user_id)
                    )
                """)
                
                conn.commit()
                logger.info(f"Database initialized at {self.db_path}")
        except sqlite3.Error as e:
            logger.error(f"Database._init_db: {e}")
            raise

    def save_user(self, discord_user_id: int, nim: str, password: str, nama: str = "") -> bool:
        """
        Simpan atau update user credentials.
        
        Args:
            discord_user_id: Discord user ID (unique key).
            nim: NIM mahasiswa.
            password: Password portal (akan dienkripsi jika crypto tersedia).
            nama: Nama user (optional).
            
        Returns:
            True jika berhasil.
        """
        try:
            encrypted_password = password
            if self.crypto:
                encrypted_password = self.crypto.encrypt(password)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO users 
                    (discord_user_id, nim, encrypted_password, nama, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (discord_user_id, nim, encrypted_password, nama, datetime.utcnow()))
                conn.commit()
                
            logger.info(f"User {discord_user_id} saved/updated")
            self._log_audit(discord_user_id, "login_credentials_saved")
            return True
        except sqlite3.Error as e:
            logger.error(f"Database.save_user: {e}")
            return False

    def get_user(self, discord_user_id: int) -> dict | None:
        """
        Ambil data user dari database.
        
        Args:
            discord_user_id: Discord user ID.
            
        Returns:
            Dict {discord_user_id, nim, password, nama} atau None jika tidak ada.
            Password di-decrypt jika crypto tersedia.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT discord_user_id, nim, encrypted_password, nama 
                    FROM users WHERE discord_user_id = ?
                """, (discord_user_id,))
                row = cursor.fetchone()
            
            if not row:
                return None
            
            password = row["encrypted_password"]
            if self.crypto:
                try:
                    password = self.crypto.decrypt(password)
                except Exception as e:
                    logger.error(f"Database.get_user: Gagal decrypt password untuk {discord_user_id}: {e}")
                    return None
            
            return {
                "discord_user_id": row["discord_user_id"],
                "nim": row["nim"],
                "password": password,
                "nama": row["nama"] or ""
            }
        except sqlite3.Error as e:
            logger.error(f"Database.get_user: {e}")
            return None

    def delete_user(self, discord_user_id: int) -> bool:
        """
        Hapus data user dari database (privacy: delete_me command).
        
        Args:
            discord_user_id: Discord user ID.
            
        Returns:
            True jika berhasil.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM users WHERE discord_user_id = ?", (discord_user_id,))
                cursor.execute("DELETE FROM audit_log WHERE discord_user_id = ?", (discord_user_id,))
                conn.commit()
            
            logger.info(f"User {discord_user_id} deleted")
            return True
        except sqlite3.Error as e:
            logger.error(f"Database.delete_user: {e}")
            return False

    def user_exists(self, discord_user_id: int) -> bool:
        """
        Cek apakah user sudah terdaftar.
        
        Args:
            discord_user_id: Discord user ID.
            
        Returns:
            True jika user ada.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1 FROM users WHERE discord_user_id = ? LIMIT 1", (discord_user_id,))
                return cursor.fetchone() is not None
        except sqlite3.Error as e:
            logger.error(f"Database.user_exists: {e}")
            return False

    def _log_audit(self, discord_user_id: int, action: str):
        """Catat event audit (internal helper)."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO audit_log (discord_user_id, action)
                    VALUES (?, ?)
                """, (discord_user_id, action))
                conn.commit()
        except sqlite3.Error as e:
            logger.warning(f"Database._log_audit: {e}")
