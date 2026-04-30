from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import Wallet, Trade, LeveragePosition, Asset
from extensions import db
from sqlalchemy import func
from datetime import datetime, timedelta
from decimal import Decimal

analytics_bp = Blueprint('analytics', __name__)

@analytics_bp.route('/trade_volume', methods=['GET'])
@jwt_required()
def trade_volume():
    """Daily trade volume (USD) for the last N days."""
    user_id = get_jwt_identity()
    days = int(request.args.get('days', 30))
    since = datetime.utcnow() - timedelta(days=days)

    wallet_ids = [w.wallet_id for w in Wallet.query.filter_by(user_id=user_id).all()]
    if not wallet_ids:
        return jsonify([]), 200

    trades = (Trade.query
              .filter(Trade.wallet_id.in_(wallet_ids), Trade.trade_date >= since)
              .order_by(Trade.trade_date).all())

    # Bucket by day
    buckets = {}
    for t in trades:
        day = t.trade_date.strftime('%Y-%m-%d')
        vol = float(t.quantity) * float(t.price)
        buckets[day] = buckets.get(day, 0) + vol

    result = [{'date': k, 'volume_usd': round(v, 2)} for k, v in sorted(buckets.items())]
    return jsonify(result), 200


@analytics_bp.route('/pnl_history', methods=['GET'])
@jwt_required()
def pnl_history():
    """Realized P&L from closed leverage positions over time."""
    user_id = get_jwt_identity()
    wallet_ids = [w.wallet_id for w in Wallet.query.filter_by(user_id=user_id).all()]
    if not wallet_ids:
        return jsonify([]), 200

    closed = (LeveragePosition.query
              .filter(LeveragePosition.wallet_id.in_(wallet_ids),
                      LeveragePosition.status == 'closed',
                      LeveragePosition.closed_at.isnot(None))
              .order_by(LeveragePosition.closed_at).all())

    running = 0.0
    result = []
    for p in closed:
        running += float(p.realized_pnl or 0)
        result.append({
            'date':         p.closed_at.strftime('%Y-%m-%d'),
            'realized_pnl': round(float(p.realized_pnl or 0), 2),
            'cumulative':   round(running, 2),
            'symbol':       p.symbol,
        })
    return jsonify(result), 200


@analytics_bp.route('/asset_allocation', methods=['GET'])
@jwt_required()
def asset_allocation():
    """Current asset allocation by symbol (quantity × avg_buy_price as proxy)."""
    user_id = get_jwt_identity()
    wallet_ids = [w.wallet_id for w in Wallet.query.filter_by(user_id=user_id).all()]
    if not wallet_ids:
        return jsonify([]), 200

    assets = Asset.query.filter(Asset.wallet_id.in_(wallet_ids)).all()

    # Aggregate by symbol
    totals = {}
    for a in assets:
        sym = a.symbol
        val = float(a.quantity) * float(a.avg_buy_price)
        totals[sym] = totals.get(sym, 0) + val

    grand = sum(totals.values()) or 1
    result = [
        {'symbol': sym, 'value_usd': round(val, 2), 'pct': round(val/grand*100, 2)}
        for sym, val in sorted(totals.items(), key=lambda x: -x[1])
    ]
    return jsonify(result), 200


@analytics_bp.route('/symbol_trades/<symbol>', methods=['GET'])
@jwt_required()
def symbol_trades(symbol):
    """All trades for a specific symbol with running avg cost."""
    user_id = get_jwt_identity()
    wallet_ids = [w.wallet_id for w in Wallet.query.filter_by(user_id=user_id).all()]
    trades = (Trade.query
              .filter(Trade.wallet_id.in_(wallet_ids),
                      Trade.symbol == symbol.upper())
              .order_by(Trade.trade_date).all())
    return jsonify([t.to_dict() for t in trades]), 200
