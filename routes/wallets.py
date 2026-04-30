from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from extensions import db
from models import Wallet

wallets_bp = Blueprint('wallets', __name__)

@wallets_bp.route('/', methods=['GET'])
@jwt_required()
def get_wallets():
    user_id = get_jwt_identity()
    wallets = Wallet.query.filter_by(user_id=user_id).all()
    return jsonify([w.to_dict() for w in wallets]), 200

@wallets_bp.route('/', methods=['POST'])
@jwt_required()
def create_wallet():
    user_id = get_jwt_identity()
    data = request.get_json()
    if not data or 'wallet_name' not in data:
        return jsonify({'error': 'wallet_name is required'}), 400
    wallet = Wallet(user_id=user_id, wallet_name=data['wallet_name'],
                    wallet_type=data.get('wallet_type', 'spot'))
    db.session.add(wallet)
    db.session.commit()
    return jsonify(wallet.to_dict()), 201

@wallets_bp.route('/<int:wallet_id>', methods=['DELETE'])
@jwt_required()
def delete_wallet(wallet_id):
    user_id = get_jwt_identity()
    wallet = Wallet.query.filter_by(wallet_id=wallet_id, user_id=user_id).first_or_404()
    db.session.delete(wallet)
    db.session.commit()
    return jsonify({'message': 'Wallet deleted'}), 200
