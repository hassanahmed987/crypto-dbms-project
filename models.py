from extensions import db
from datetime import datetime

class User(db.Model):
    __tablename__ = 'users'
    user_id       = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(50), unique=True, nullable=False)
    email         = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role          = db.Column(db.Enum('admin','trader'), default='trader')
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    wallets       = db.relationship('Wallet', backref='owner', lazy=True, cascade='all, delete')

    def to_dict(self):
        return {'user_id': self.user_id, 'username': self.username,
                'email': self.email, 'role': self.role}


class Wallet(db.Model):
    __tablename__ = 'wallets'
    wallet_id   = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    wallet_name = db.Column(db.String(100), nullable=False)
    wallet_type = db.Column(db.Enum('spot','margin','futures'), default='spot')
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    assets      = db.relationship('Asset', backref='wallet', lazy=True, cascade='all, delete')
    trades      = db.relationship('Trade', backref='wallet', lazy=True, cascade='all, delete')
    positions   = db.relationship('LeveragePosition', backref='wallet', lazy=True, cascade='all, delete')

    def to_dict(self):
        return {'wallet_id': self.wallet_id, 'user_id': self.user_id,
                'wallet_name': self.wallet_name, 'wallet_type': self.wallet_type}


class Asset(db.Model):
    __tablename__ = 'assets'
    asset_id      = db.Column(db.Integer, primary_key=True)
    wallet_id     = db.Column(db.Integer, db.ForeignKey('wallets.wallet_id'), nullable=False)
    symbol        = db.Column(db.String(20), nullable=False)
    quantity      = db.Column(db.Numeric(20,8), default=0)
    avg_buy_price = db.Column(db.Numeric(20,8), default=0)
    updated_at    = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {'asset_id': self.asset_id, 'wallet_id': self.wallet_id,
                'symbol': self.symbol, 'quantity': float(self.quantity),
                'avg_buy_price': float(self.avg_buy_price)}


class Trade(db.Model):
    __tablename__ = 'trades'
    trade_id   = db.Column(db.Integer, primary_key=True)
    wallet_id  = db.Column(db.Integer, db.ForeignKey('wallets.wallet_id'), nullable=False)
    symbol     = db.Column(db.String(20), nullable=False)
    trade_type = db.Column(db.Enum('buy','sell'), nullable=False)
    quantity   = db.Column(db.Numeric(20,8), nullable=False)
    price      = db.Column(db.Numeric(20,8), nullable=False)
    fee        = db.Column(db.Numeric(20,8), default=0)
    trade_date = db.Column(db.DateTime, default=datetime.utcnow)
    notes      = db.Column(db.Text)

    def to_dict(self):
        return {'trade_id': self.trade_id, 'wallet_id': self.wallet_id,
                'symbol': self.symbol, 'trade_type': self.trade_type,
                'quantity': float(self.quantity), 'price': float(self.price),
                'fee': float(self.fee), 'trade_date': self.trade_date.isoformat(),
                'notes': self.notes}


class LeveragePosition(db.Model):
    __tablename__ = 'leverage_positions'
    position_id       = db.Column(db.Integer, primary_key=True)
    wallet_id         = db.Column(db.Integer, db.ForeignKey('wallets.wallet_id'), nullable=False)
    symbol            = db.Column(db.String(20), nullable=False)
    direction         = db.Column(db.Enum('long','short'), nullable=False)
    leverage          = db.Column(db.Numeric(5,2), nullable=False)
    entry_price       = db.Column(db.Numeric(20,8), nullable=False)
    quantity          = db.Column(db.Numeric(20,8), nullable=False)
    margin_used       = db.Column(db.Numeric(20,8), nullable=False)
    liquidation_price = db.Column(db.Numeric(20,8))
    status            = db.Column(db.Enum('open','closed'), default='open')
    opened_at         = db.Column(db.DateTime, default=datetime.utcnow)
    closed_at         = db.Column(db.DateTime)
    close_price       = db.Column(db.Numeric(20,8))
    realized_pnl      = db.Column(db.Numeric(20,8))

    def to_dict(self):
        return {
            'position_id': self.position_id, 'wallet_id': self.wallet_id,
            'symbol': self.symbol, 'direction': self.direction,
            'leverage': float(self.leverage), 'entry_price': float(self.entry_price),
            'quantity': float(self.quantity), 'margin_used': float(self.margin_used),
            'liquidation_price': float(self.liquidation_price) if self.liquidation_price else None,
            'status': self.status,
            'opened_at': self.opened_at.isoformat(),
            'closed_at': self.closed_at.isoformat() if self.closed_at else None,
            'close_price': float(self.close_price) if self.close_price else None,
            'realized_pnl': float(self.realized_pnl) if self.realized_pnl else None,
        }


class PriceCache(db.Model):
    __tablename__ = 'price_cache'
    cache_id   = db.Column(db.Integer, primary_key=True)
    symbol     = db.Column(db.String(20), nullable=False)
    price_usd  = db.Column(db.Numeric(20,8), nullable=False)
    fetched_at = db.Column(db.DateTime, default=datetime.utcnow)
