from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from extensions import db
from models import Trade, Asset, Wallet
from decimal import Decimal

trades_bp = Blueprint('trades', __name__)

def _check_wallet(wallet_id, user_id):
    return Wallet.query.filter_by(wallet_id=wallet_id, user_id=user_id).first()

@trades_bp.route('/<int:wallet_id>', methods=['GET'])
@jwt_required()
def get_trades(wallet_id):
    user_id = get_jwt_identity()
    if not _check_wallet(wallet_id, user_id):
        return jsonify({'error': 'Wallet not found'}), 404
    trades = Trade.query.filter_by(wallet_id=wallet_id).order_by(Trade.trade_date.desc()).all()
    return jsonify([t.to_dict() for t in trades]), 200

@trades_bp.route('/<int:wallet_id>', methods=['POST'])
@jwt_required()
def record_trade(wallet_id):
    user_id = get_jwt_identity()
    if not _check_wallet(wallet_id, user_id):
        return jsonify({'error': 'Wallet not found'}), 404

    data = request.get_json()
    required = ('symbol','trade_type','quantity','price')
    if not data or not all(k in data for k in required):
        return jsonify({'error': f'{required} are required'}), 400
    if data['trade_type'] not in ('buy','sell'):
        return jsonify({'error': 'trade_type must be buy or sell'}), 400

    symbol   = data['symbol'].upper()
    qty      = Decimal(str(data['quantity']))
    price    = Decimal(str(data['price']))
    fee      = Decimal(str(data.get('fee', 0)))

    # Update or create asset holding
    asset = Asset.query.filter_by(wallet_id=wallet_id, symbol=symbol).first()
    if data['trade_type'] == 'buy':
        if asset:
            total_cost    = asset.avg_buy_price * asset.quantity + price * qty
            asset.quantity = asset.quantity + qty
            asset.avg_buy_price = total_cost / asset.quantity
        else:
            asset = Asset(wallet_id=wallet_id, symbol=symbol,
                          quantity=qty, avg_buy_price=price)
            db.session.add(asset)
    else:  # sell
        if not asset or asset.quantity < qty:
            return jsonify({'error': 'Insufficient holdings'}), 400
        asset.quantity -= qty
        if asset.quantity == 0:
            db.session.delete(asset)

    trade = Trade(wallet_id=wallet_id, symbol=symbol,
                  trade_type=data['trade_type'], quantity=qty,
                  price=price, fee=fee, notes=data.get('notes'))
    db.session.add(trade)
    db.session.commit()
    return jsonify(trade.to_dict()), 201
