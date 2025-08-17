from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.orm import declarative_base
from .database import engine
from .encrypted_type import EncryptedColumn
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

Base = declarative_base()

from sqlalchemy import Boolean

class User(UserMixin, Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(128))
    otp_secret = Column(String(16), nullable=True)
    otp_enabled = Column(Boolean, default=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Trade(Base):
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, index=True)
    opportunity_type = Column(String) # e.g., "triangular" or "direct"

    # Non-sensitive identifiers can remain unencrypted
    exchange1 = Column(String)
    asset1_symbol = Column(String)

    # Encrypt all financial data
    asset1_price = Column(EncryptedColumn)
    asset1_amount = Column(EncryptedColumn)

    exchange2 = Column(String)
    asset2_symbol = Column(String)
    asset2_price = Column(EncryptedColumn)
    asset2_amount = Column(EncryptedColumn)

    exchange3 = Column(String, nullable=True)
    asset3_symbol = Column(String, nullable=True)
    asset3_price = Column(EncryptedColumn, nullable=True)
    asset3_amount = Column(EncryptedColumn, nullable=True)

    # Encrypt all profitability data
    initial_investment = Column(EncryptedColumn)
    final_return = Column(EncryptedColumn)
    profit_or_loss = Column(EncryptedColumn)
    profitability_pct = Column(EncryptedColumn)

def init_db():
    Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    init_db()
