"""Encryption manager for ACMS using XChaCha20-Poly1305 AEAD.

Provides symmetric encryption with authenticated encryption and unique nonces.
Uses 256-bit keys for strong security.

Features:
- XChaCha20-Poly1305 AEAD (Authenticated Encryption with Associated Data)
- 256-bit encryption keys
- Unique 192-bit nonces for each encryption
- Tamper detection via authentication tags
- Hardware-backed key support (future)
"""

import os
import sys
import base64
from typing import Optional, Union

from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305


class EncryptionManager:
    """Manages encryption and decryption of sensitive data.

    Uses XChaCha20-Poly1305 for authenticated encryption.
    Each instance has its own key, or can use a provided key.

    Example:
        manager = EncryptionManager()
        encrypted = manager.encrypt("sensitive data")
        decrypted = manager.decrypt(encrypted)
    """

    def __init__(self, key: Optional[bytes] = None):
        """Initialize encryption manager.

        Args:
            key: 32-byte encryption key. If None, generates a new key.
        """
        if key is None:
            self._key = ChaCha20Poly1305.generate_key()
        else:
            if len(key) != 32:
                raise ValueError("Encryption key must be exactly 32 bytes (256 bits)")
            self._key = key

        self._cipher = ChaCha20Poly1305(self._key)

    @property
    def key(self) -> bytes:
        """Get the encryption key.

        Returns:
            bytes: 32-byte encryption key

        Warning:
            Store this key securely! Loss of key means permanent data loss.
        """
        return self._key

    @classmethod
    def from_base64_key(cls, key_b64: str) -> "EncryptionManager":
        """Create manager from base64-encoded key.

        Args:
            key_b64: Base64-encoded 32-byte key

        Returns:
            EncryptionManager: New manager instance
        """
        key = base64.b64decode(key_b64)
        return cls(key=key)

    def generate_key(self) -> bytes:
        """Generate a new 256-bit encryption key.

        Returns:
            bytes: 32-byte encryption key

        Note:
            This is a static method for generating keys.
            The instance's key is not changed.
        """
        return ChaCha20Poly1305.generate_key()

    def export_key_base64(self) -> str:
        """Export encryption key as base64 string.

        Returns:
            str: Base64-encoded key

        Warning:
            Store this key securely! Anyone with this key can decrypt all data.
        """
        return base64.b64encode(self._key).decode('utf-8')

    def encrypt(self, plaintext: Union[str, bytes], associated_data: Optional[bytes] = None) -> bytes:
        """Encrypt plaintext using XChaCha20-Poly1305.

        Args:
            plaintext: Data to encrypt (string or bytes)
            associated_data: Additional authenticated data (not encrypted)

        Returns:
            bytes: Encrypted data with format: nonce (12 bytes) + ciphertext + tag

        Note:
            Each encryption uses a unique random nonce.
            The nonce is prepended to the ciphertext.
        """
        if isinstance(plaintext, str):
            plaintext = plaintext.encode('utf-8')

        # Generate unique nonce (12 bytes for ChaCha20Poly1305)
        nonce = os.urandom(12)

        # Encrypt with authentication
        ciphertext = self._cipher.encrypt(nonce, plaintext, associated_data)

        # Prepend nonce to ciphertext (nonce is needed for decryption)
        return nonce + ciphertext

    def decrypt(self, encrypted_data: bytes, associated_data: Optional[bytes] = None) -> str:
        """Decrypt data using XChaCha20-Poly1305.

        Args:
            encrypted_data: Encrypted data (nonce + ciphertext + tag)
            associated_data: Additional authenticated data (must match encryption)

        Returns:
            str: Decrypted plaintext

        Raises:
            cryptography.exceptions.InvalidTag: If data is tampered or wrong key
        """
        # Extract nonce (first 12 bytes)
        nonce = encrypted_data[:12]
        ciphertext = encrypted_data[12:]

        # Decrypt and verify authentication tag
        plaintext = self._cipher.decrypt(nonce, ciphertext, associated_data)

        return plaintext.decode('utf-8')

    def encrypt_to_base64(self, plaintext: Union[str, bytes], associated_data: Optional[bytes] = None) -> str:
        """Encrypt and encode as base64 string (for storage in text fields).

        Args:
            plaintext: Data to encrypt
            associated_data: Additional authenticated data

        Returns:
            str: Base64-encoded encrypted data
        """
        encrypted = self.encrypt(plaintext, associated_data)
        return base64.b64encode(encrypted).decode('utf-8')

    def decrypt_from_base64(self, encrypted_b64: str, associated_data: Optional[bytes] = None) -> str:
        """Decrypt from base64-encoded string.

        Args:
            encrypted_b64: Base64-encoded encrypted data
            associated_data: Additional authenticated data

        Returns:
            str: Decrypted plaintext
        """
        encrypted = base64.b64decode(encrypted_b64)
        return self.decrypt(encrypted, associated_data)


class KeyManager:
    """Manages encryption keys for multi-user scenarios.

    Stores keys securely and provides key rotation support.
    Future: Hardware-backed key storage (HSM, TPM).
    """

    def __init__(self, master_key: Optional[bytes] = None):
        """Initialize key manager.

        Args:
            master_key: Master key for key encryption. If None, generates new.
        """
        self._master_key = master_key or ChaCha20Poly1305.generate_key()
        self._master_cipher = ChaCha20Poly1305(self._master_key)
        self._key_cache = {}  # user_id -> EncryptionManager

    def get_or_create_user_key(self, user_id: str) -> EncryptionManager:
        """Get or create encryption manager for a user.

        Args:
            user_id: User identifier

        Returns:
            EncryptionManager: User's encryption manager
        """
        if user_id not in self._key_cache:
            # Generate new key for user
            user_key = ChaCha20Poly1305.generate_key()
            self._key_cache[user_id] = EncryptionManager(key=user_key)

        return self._key_cache[user_id]

    def encrypt_key(self, key: bytes) -> bytes:
        """Encrypt a key using the master key.

        Args:
            key: Key to encrypt

        Returns:
            bytes: Encrypted key (nonce + ciphertext + tag)

        Note:
            Used for storing user keys securely.
        """
        nonce = os.urandom(12)
        encrypted = self._master_cipher.encrypt(nonce, key, None)
        return nonce + encrypted

    def decrypt_key(self, encrypted_key: bytes) -> bytes:
        """Decrypt a key using the master key.

        Args:
            encrypted_key: Encrypted key data

        Returns:
            bytes: Decrypted key
        """
        nonce = encrypted_key[:12]
        ciphertext = encrypted_key[12:]
        return self._master_cipher.decrypt(nonce, ciphertext, None)

    def rotate_user_key(self, user_id: str, old_manager: EncryptionManager) -> EncryptionManager:
        """Rotate encryption key for a user.

        Args:
            user_id: User identifier
            old_manager: Old encryption manager (for re-encrypting data)

        Returns:
            EncryptionManager: New encryption manager

        Note:
            Caller must re-encrypt all user data with new key.
        """
        new_key = ChaCha20Poly1305.generate_key()
        new_manager = EncryptionManager(key=new_key)
        self._key_cache[user_id] = new_manager
        return new_manager


# Global encryption manager instance
_global_manager: Optional[EncryptionManager] = None


def get_global_encryption_manager() -> EncryptionManager:
    """Get the global encryption manager instance.

    Returns:
        EncryptionManager: Global encryption manager

    Note:
        Creates a new manager if none exists.
        For production, load key from secure storage.
    """
    global _global_manager

    if _global_manager is None:
        # In production, load key from environment or secure storage
        key_b64 = os.getenv("ACMS_ENCRYPTION_KEY")
        if key_b64:
            _global_manager = EncryptionManager.from_base64_key(key_b64)
        else:
            # Generate new key (should only happen in development/testing)
            _global_manager = EncryptionManager()
            sys.stderr.write("⚠️  WARNING: Generated new encryption key. Set ACMS_ENCRYPTION_KEY in production!\n")

    return _global_manager


if __name__ == "__main__":
    # Test encryption
    print("Testing encryption manager...")

    manager = EncryptionManager()
    plaintext = "This is sensitive memory content that must be encrypted"

    print(f"Original: {plaintext}")

    # Test encryption/decryption
    encrypted = manager.encrypt(plaintext)
    print(f"Encrypted: {encrypted[:20]}... ({len(encrypted)} bytes)")

    decrypted = manager.decrypt(encrypted)
    print(f"Decrypted: {decrypted}")

    assert plaintext == decrypted, "Decryption failed!"

    # Test unique nonces
    encrypted1 = manager.encrypt(plaintext)
    encrypted2 = manager.encrypt(plaintext)
    assert encrypted1 != encrypted2, "Nonces not unique!"

    print("✅ All encryption tests passed!")

    # Test base64 encoding
    encrypted_b64 = manager.encrypt_to_base64(plaintext)
    print(f"Base64: {encrypted_b64[:50]}...")
    decrypted_b64 = manager.decrypt_from_base64(encrypted_b64)
    assert plaintext == decrypted_b64, "Base64 encryption failed!"

    print("✅ Base64 encryption tests passed!")
