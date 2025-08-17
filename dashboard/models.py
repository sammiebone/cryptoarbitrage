from flask_sqlalchemy import SQLAlchemy
import datetime

# Initialize the SQLAlchemy object.
# This will be linked to the Flask app in app.py to avoid circular imports.
db = SQLAlchemy()

class Trade(db.Model):
    """
    Represents a single executed trade in the database.
    """
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)
    trade_type = db.Column(db.String(20), nullable=False) # "triangular" or "direct"
    symbol = db.Column(db.String(20), nullable=False)

    # For direct arbitrage
    buy_exchange = db.Column(db.String(50))
    sell_exchange = db.Column(db.String(50))

    # For triangular, the exchange is stored in one field
    exchange = db.Column(db.String(50))

    trade_size_quote = db.Column(db.Float, nullable=False)
    profit_amount = db.Column(db.Float, nullable=False) # In quote currency
    profit_percentage = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), nullable=False) # e.g., "completed", "failed"

    def to_dict(self):
        """Serializes the object to a dictionary."""
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat(),
            'trade_type': self.trade_type,
            'symbol': self.symbol,
            'buy_exchange': self.buy_exchange,
            'sell_exchange': self.sell_exchange,
            'exchange': self.exchange,
            'trade_size_quote': self.trade_size_quote,
            'profit_amount': self.profit_amount,
            'profit_percentage': self.profit_percentage,
            'status': self.status,
        }

    def __repr__(self):
        return f'<Trade {self.id} {self.symbol} {self.profit_percentage:.4f}%>'
