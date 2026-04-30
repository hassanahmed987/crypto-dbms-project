from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from extensions import db
from models import Asset, Wallet

assets_bp = Blueprint('assets', __name__)

def _check_wallet(wallet_id, user_id):
    return Wallet.query.filter_by(wallet_id=wallet_id, user_id=user_id).first()

@assets_bp.route('/<int:wallet_id>', methods=['GET'])
@jwt_required()
def get_assets(wallet_id):
    user_id = get_jwt_identity()
    if not _check_wallet(wallet_id, user_id):
        return jsonify({'error': 'Wallet not found'}), 404
    assets = Asset.query.filter_by(wallet_id=wallet_id).all()
    return jsonify([a.to_dict() for a in assets]), 200

@assets_bp.route('/<int:wallet_id>', methods=['POST'])
@jwt_required()
def add_asset(wallet_id):
    user_id = get_jwt_identity()
    if not _check_wallet(wallet_id, user_id):
        return jsonify({'error': 'Wallet not found'}), 404
    data = request.get_json()
    if not data or not all(k in data for k in ('symbol','quantity','avg_buy_price')):
        return jsonify({'error': 'symbol, quantity and avg_buy_price required'}), 400

    # Upsert: update if symbol already exists in wallet
    existing = Asset.query.filter_by(wallet_id=wallet_id, symbol=data['symbol'].upper()).first()
    if existing:
        existing.quantity = data['quantity']
        existing.avg_buy_price = data['avg_buy_price']
        db.session.commit()
        return jsonify(existing.to_dict()), 200

    asset = Asset(wallet_id=wallet_id, symbol=data['symbol'].upper(),
                  quantity=data['quantity'], avg_buy_price=data['avg_buy_price'])
    db.session.add(asset)
    db.session.commit()
    return jsonify(asset.to_dict()), 201

@assets_bp.route('/<int:wallet_id>/<int:asset_id>', methods=['DELETE'])
@jwt_required()
def delete_asset(wallet_id, asset_id):
    user_id = get_jwt_identity()
    if not _check_wallet(wallet_id, user_id):
        return jsonify({'error': 'Wallet not found'}), 404
    asset = Asset.query.filter_by(asset_id=asset_id, wallet_id=wallet_id).first_or_404()
    db.session.delete(asset)
    db.session.commit()
    return jsonify({'message': 'Asset removed'}), 200
