import requests
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required
from extensions import db
from models import PriceCache
from datetime import datetime, timedelta

prices_bp = Blueprint('prices', __name__)

# Map common ticker → CoinGecko ID
SYMBOL_MAP = {
    'BTC': 'bitcoin', 'ETH': 'ethereum', 'SOL': 'solana',
    'BNB': 'binancecoin', 'XRP': 'ripple', 'ADA': 'cardano',
    'DOGE': 'dogecoin', 'AVAX': 'avalanche-2', 'DOT': 'polkadot',
    'MATIC': 'matic-network', 'LINK': 'chainlink', 'UNI': 'uniswap',
    'LTC': 'litecoin', 'ATOM': 'cosmos', 'NEAR': 'near',
}

def get_coingecko_prices(symbols):
    """Fetch USD prices from CoinGecko for a list of symbols."""
    ids = [SYMBOL_MAP.get(s.upper()) for s in symbols if SYMBOL_MAP.get(s.upper())]
    if not ids:
        return {}
    url = f"{current_app.config['COINGECKO_BASE_URL']}/simple/price"
    params = {'ids': ','.join(ids), 'vs_currencies': 'usd'}
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        result = {}
        for sym in symbols:
            cg_id = SYMBOL_MAP.get(sym.upper())
            if cg_id and cg_id in data:
                result[sym.upper()] = data[cg_id]['usd']
        return result
    except Exception as e:
        current_app.logger.error(f'CoinGecko error: {e}')
        return {}

def get_price_with_cache(symbol, max_age_minutes=5):
    """Return cached price if fresh, otherwise fetch from CoinGecko."""
    cutoff = datetime.utcnow() - timedelta(minutes=max_age_minutes)
    cached = (PriceCache.query
              .filter(PriceCache.symbol == symbol.upper(),
                      PriceCache.fetched_at >= cutoff)
              .order_by(PriceCache.fetched_at.desc())
              .first())
    if cached:
        return float(cached.price_usd)

    prices = get_coingecko_prices([symbol])
    price = prices.get(symbol.upper())
    if price:
        entry = PriceCache(symbol=symbol.upper(), price_usd=price)
        db.session.add(entry)
        db.session.commit()
    return price

@prices_bp.route('/<symbol>', methods=['GET'])
@jwt_required()
def get_price(symbol):
    price = get_price_with_cache(symbol)
    if price is None:
        return jsonify({'error': f'Price not available for {symbol}'}), 404
    return jsonify({'symbol': symbol.upper(), 'price_usd': price}), 200

@prices_bp.route('/batch', methods=['POST'])
@jwt_required()
def batch_prices():
    data = request.get_json()
    symbols = data.get('symbols', [])
    if not symbols:
        return jsonify({'error': 'symbols list required'}), 400
    prices = get_coingecko_prices(symbols)
    return jsonify(prices), 200

@prices_bp.route('/supported', methods=['GET'])
def supported_symbols():
    return jsonify(list(SYMBOL_MAP.keys())), 200
