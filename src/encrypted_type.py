import os
import base64
from sqlalchemy.types import TypeDecorator, String
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# --- Key Management ---
# In a real production system, you would use a more robust key management solution
# like HashiCorp Vault or AWS KMS. For this application, we will derive a key
# from a password stored in an environment variable.

# Load the database encryption password from an environment variable
DB_ENCRYPTION_PASSWORD = os.environ.get("DB_ENCRYPTION_KEY")
if not DB_ENCRYPTION_PASSWORD:
    raise ValueError("DB_ENCRYPTION_KEY environment variable not set. Please set it to a strong password.")

# Use a static salt. For higher security, you might store/generate this differently.
SALT = b'salt_for_the_arbitrage_bot'

# Derive a 32-byte key from the password using PBKDF2
kdf = PBKDF2HMAC(
    algorithm=hashes.SHA256(),
    length=32,
    salt=SALT,
    iterations=100000,
)
key = base64.urlsafe_b64encode(kdf.derive(DB_ENCRYPTION_PASSWORD.encode()))
fernet = Fernet(key)


# --- Custom Encrypted Type for SQLAlchemy ---

class EncryptedColumn(TypeDecorator):
    """
    A SQLAlchemy TypeDecorator that provides transparent encryption for a column.

    It encrypts data when writing to the database and decrypts it when reading.
    The underlying type in the database is a String (to store the encrypted bytes).
    """
    impl = String

    def process_bind_param(self, value, dialect):
        """Encrypts the value for storage in the database."""
        if value is None:
            return None
        # Convert the value to string, then encode to bytes for encryption
        value_str = str(value)
        encrypted_value = fernet.encrypt(value_str.encode())
        return encrypted_value.decode('utf-8')

    def process_result_value(self, value, dialect):
        """Decrypts the value when reading from the database."""
        if value is None:
            return None
        # The value from the DB is a string, needs to be encoded back to bytes
        encrypted_value = value.encode('utf-8')
        decrypted_value = fernet.decrypt(encrypted_value).decode('utf-8')
        # Here we assume the decrypted value should be a float, as we are encrypting prices/amounts.
        # A more robust implementation might store the original type.
        try:
            return float(decrypted_value)
        except ValueError:
            return decrypted_value
