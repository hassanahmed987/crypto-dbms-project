from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import Wallet, Asset, LeveragePosition
from routes.prices import get_coingecko_prices, get_price_with_cache
from decimal import Decimal

portfolio_bp = Blueprint('portfolio', __name__)

@portfolio_bp.route('/summary', methods=['GET'])
@jwt_required()
def portfolio_summary():
    user_id = get_jwt_identity()
    wallets = Wallet.query.filter_by(user_id=user_id).all()

    all_assets   = []
    all_positions = []
    symbols_needed = set()

    for wallet in wallets:
        for asset in wallet.assets:
            symbols_needed.add(asset.symbol)
            all_assets.append(asset)
        for pos in wallet.positions:
            if pos.status == 'open':
                symbols_needed.add(pos.symbol)
                all_positions.append(pos)

    # Fetch live prices for all symbols at once
    live_prices = get_coingecko_prices(list(symbols_needed)) if symbols_needed else {}

    # --- Spot holdings summary ---
    spot_total_value   = Decimal('0')
    spot_total_cost    = Decimal('0')
    holdings = []

    for asset in all_assets:
        price      = Decimal(str(live_prices.get(asset.symbol, 0)))
        value      = price * asset.quantity
        cost       = asset.avg_buy_price * asset.quantity
        pnl        = value - cost
        pnl_pct    = (pnl / cost * 100) if cost else Decimal('0')

        spot_total_value += value
        spot_total_cost  += cost

        holdings.append({
            'asset_id':      asset.asset_id,
            'wallet_id':     asset.wallet_id,
            'symbol':        asset.symbol,
            'quantity':      float(asset.quantity),
            'avg_buy_price': float(asset.avg_buy_price),
            'current_price': float(price),
            'current_value': float(value),
            'pnl':           float(pnl),
            'pnl_pct':       float(pnl_pct),
        })

    spot_pnl     = spot_total_value - spot_total_cost
    spot_pnl_pct = (spot_pnl / spot_total_cost * 100) if spot_total_cost else Decimal('0')

    # --- Open leverage positions summary ---
    open_positions = []
    unrealized_lev_pnl = Decimal('0')

    for pos in all_positions:
        price = Decimal(str(live_prices.get(pos.symbol, 0)))
        ep    = Decimal(str(pos.entry_price))
        qty   = Decimal(str(pos.quantity))
        lev   = Decimal(str(pos.leverage))

        if pos.direction == 'long':
            upnl = (price - ep) * qty * lev
        else:
            upnl = (ep - price) * qty * lev

        unrealized_lev_pnl += upnl

        open_positions.append({
            **pos.to_dict(),
            'current_price':    float(price),
            'unrealized_pnl':   float(upnl),
        })

    return jsonify({
        'spot': {
            'total_value':   float(spot_total_value),
            'total_cost':    float(spot_total_cost),
            'total_pnl':     float(spot_pnl),
            'total_pnl_pct': float(spot_pnl_pct),
            'holdings':      holdings,
        },
        'leverage': {
            'open_positions':     open_positions,
            'unrealized_pnl':     float(unrealized_lev_pnl),
        },
        'combined_portfolio_value': float(spot_total_value),
    }), 200
