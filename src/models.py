from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.orm import declarative_base
from .database import engine

Base = declarative_base()

class Trade(Base):
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, index=True)
    opportunity_type = Column(String) # e.g., "triangular" or "direct"

    # Trade 1
    exchange1 = Column(String)
    asset1_symbol = Column(String)
    asset1_price = Column(Float)
    asset1_amount = Column(Float)

    # Trade 2
    exchange2 = Column(String)
    asset2_symbol = Column(String)
    asset2_price = Column(Float)
    asset2_amount = Column(Float)

    # Trade 3 (for triangular)
    exchange3 = Column(String, nullable=True)
    asset3_symbol = Column(String, nullable=True)
    asset3_price = Column(Float, nullable=True)
    asset3_amount = Column(Float, nullable=True)

    # Profitability
    initial_investment = Column(Float)
    final_return = Column(Float)
    profit_or_loss = Column(Float)
    profitability_pct = Column(Float)

def init_db():
    Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    init_db()
