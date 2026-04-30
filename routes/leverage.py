from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from extensions import db
from models import LeveragePosition, Wallet
from decimal import Decimal
from datetime import datetime

leverage_bp = Blueprint('leverage', __name__)

def _check_wallet(wallet_id, user_id):
    return Wallet.query.filter_by(wallet_id=wallet_id, user_id=user_id).first()

def _calc_liquidation(direction, entry_price, leverage):
    """Simplified liquidation price (assumes 100% loss of margin)."""
    ep = Decimal(str(entry_price))
    lev = Decimal(str(leverage))
    if direction == 'long':
        return float(ep * (1 - 1/lev))
    else:
        return float(ep * (1 + 1/lev))

@leverage_bp.route('/<int:wallet_id>', methods=['GET'])
@jwt_required()
def get_positions(wallet_id):
    user_id = get_jwt_identity()
    if not _check_wallet(wallet_id, user_id):
        return jsonify({'error': 'Wallet not found'}), 404
    status = request.args.get('status', 'open')
    positions = LeveragePosition.query.filter_by(wallet_id=wallet_id, status=status).all()
    return jsonify([p.to_dict() for p in positions]), 200

@leverage_bp.route('/<int:wallet_id>', methods=['POST'])
@jwt_required()
def open_position(wallet_id):
    user_id = get_jwt_identity()
    if not _check_wallet(wallet_id, user_id):
        return jsonify({'error': 'Wallet not found'}), 404

    data = request.get_json()
    required = ('symbol','direction','leverage','entry_price','quantity','margin_used')
    if not data or not all(k in data for k in required):
        return jsonify({'error': f'{required} are required'}), 400

    liq_price = _calc_liquidation(data['direction'], data['entry_price'], data['leverage'])

    pos = LeveragePosition(
        wallet_id=wallet_id,
        symbol=data['symbol'].upper(),
        direction=data['direction'],
        leverage=data['leverage'],
        entry_price=data['entry_price'],
        quantity=data['quantity'],
        margin_used=data['margin_used'],
        liquidation_price=liq_price
    )
    db.session.add(pos)
    db.session.commit()
    return jsonify(pos.to_dict()), 201

@leverage_bp.route('/<int:wallet_id>/<int:position_id>/close', methods=['POST'])
@jwt_required()
def close_position(wallet_id, position_id):
    user_id = get_jwt_identity()
    if not _check_wallet(wallet_id, user_id):
        return jsonify({'error': 'Wallet not found'}), 404

    data = request.get_json()
    if not data or 'close_price' not in data:
        return jsonify({'error': 'close_price required'}), 400

    pos = LeveragePosition.query.filter_by(
        position_id=position_id, wallet_id=wallet_id, status='open').first_or_404()

    close_price = Decimal(str(data['close_price']))
    entry_price = Decimal(str(pos.entry_price))
    qty         = Decimal(str(pos.quantity))
    lev         = Decimal(str(pos.leverage))

    if pos.direction == 'long':
        pnl = (close_price - entry_price) * qty * lev
    else:
        pnl = (entry_price - close_price) * qty * lev

    pos.status       = 'closed'
    pos.close_price  = close_price
    pos.closed_at    = datetime.utcnow()
    pos.realized_pnl = pnl
    db.session.commit()
    return jsonify(pos.to_dict()), 200
