from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from extensions import db
from models import User, Wallet, Trade, LeveragePosition
from functools import wraps

admin_bp = Blueprint('admin', __name__)

def admin_required(fn):
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if not user or user.role != 'admin':
            return jsonify({'error': 'Admin access required'}), 403
        return fn(*args, **kwargs)
    return wrapper

# ── Users ────────────────────────────────────────────────────
@admin_bp.route('/users', methods=['GET'])
@admin_required
def list_users():
    users = User.query.all()
    return jsonify([u.to_dict() for u in users]), 200

@admin_bp.route('/users/<int:user_id>', methods=['DELETE'])
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    return jsonify({'message': f'User {user.username} deleted'}), 200

@admin_bp.route('/users/<int:user_id>/role', methods=['PATCH'])
@admin_required
def change_role(user_id):
    data = request.get_json()
    role = data.get('role')
    if role not in ('admin', 'trader'):
        return jsonify({'error': 'role must be admin or trader'}), 400
    user = User.query.get_or_404(user_id)
    user.role = role
    db.session.commit()
    return jsonify(user.to_dict()), 200

# ── Platform Stats ────────────────────────────────────────────
@admin_bp.route('/stats', methods=['GET'])
@admin_required
def platform_stats():
    total_users     = User.query.count()
    total_wallets   = Wallet.query.count()
    total_trades    = Trade.query.count()
    open_positions  = LeveragePosition.query.filter_by(status='open').count()
    closed_positions = LeveragePosition.query.filter_by(status='closed').count()

    buy_trades  = Trade.query.filter_by(trade_type='buy').count()
    sell_trades = Trade.query.filter_by(trade_type='sell').count()

    return jsonify({
        'total_users':       total_users,
        'total_wallets':     total_wallets,
        'total_trades':      total_trades,
        'buy_trades':        buy_trades,
        'sell_trades':       sell_trades,
        'open_positions':    open_positions,
        'closed_positions':  closed_positions,
    }), 200

# ── All Trades (across all users) ────────────────────────────
@admin_bp.route('/trades', methods=['GET'])
@admin_required
def all_trades():
    limit  = int(request.args.get('limit', 50))
    offset = int(request.args.get('offset', 0))
    trades = Trade.query.order_by(Trade.trade_date.desc()).limit(limit).offset(offset).all()
    return jsonify([t.to_dict() for t in trades]), 200

# ── All Positions ─────────────────────────────────────────────
@admin_bp.route('/positions', methods=['GET'])
@admin_required
def all_positions():
    status = request.args.get('status', 'open')
    positions = LeveragePosition.query.filter_by(status=status).all()
    return jsonify([p.to_dict() for p in positions]), 200
