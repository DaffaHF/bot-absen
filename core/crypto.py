"""
Cryptography utilities untuk enkripsi data sensitif (password, token) sebelum simpan ke database.
Menggunakan Fernet dari cryptography library untuk symmetric encryption.
"""

import logging
from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)


class CryptoManager:
    """Manager untuk enkripsi/dekripsi data sensitif."""

    def __init__(self, key: bytes | None = None):
        """
        Inisialisasi dengan Fernet key.
        
        Args:
            key: Fernet key (32 byte base64-encoded), atau None untuk generate baru.
        """
        if key is None:
            self.cipher = Fernet(Fernet.generate_key())
            logger.warning("CryptoManager: Kunci enkripsi baru dibuat (development only)")
        else:
            try:
                self.cipher = Fernet(key)
            except Exception as e:
                logger.error(f"CryptoManager: Gagal inisialisasi kunci enkripsi: {e}")
                raise ValueError("Invalid encryption key format") from e

    def encrypt(self, plaintext: str) -> str:
        """
        Enkripsi string plaintext menjadi token base64.
        
        Args:
            plaintext: String yang ingin dienkripsi.
            
        Returns:
            Base64-encoded token terenkripsi.
        """
        try:
            token = self.cipher.encrypt(plaintext.encode())
            return token.decode()
        except Exception as e:
            logger.error(f"CryptoManager.encrypt: {e}")
            raise

    def decrypt(self, ciphertext: str) -> str:
        """
        Dekripsi token terenkripsi menjadi plaintext.
        
        Args:
            ciphertext: Base64-encoded token terenkripsi.
            
        Returns:
            Plaintext original.
            
        Raises:
            InvalidToken: Jika ciphertext tidak valid atau rusak.
        """
        try:
            plaintext = self.cipher.decrypt(ciphertext.encode())
            return plaintext.decode()
        except InvalidToken as e:
            logger.error(f"CryptoManager.decrypt: Token tidak valid atau rusak: {e}")
            raise
        except Exception as e:
            logger.error(f"CryptoManager.decrypt: {e}")
            raise
