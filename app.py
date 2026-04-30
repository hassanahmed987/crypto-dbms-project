"""
Crypto Portfolio & Leverage Tracker — Flask Application
"""
from dotenv import load_dotenv
load_dotenv()
from flask import Flask
from flask_cors import CORS
from config import Config
from extensions import db, jwt
from flask_cors import CORS

def create_app(config_class=Config):
    app = Flask(__name__)
    # This allows any website (including your forwarded link) to talk to the API
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Extensions
    # Extensions
    CORS(app, supports_credentials=True)
    db.init_app(app)
    jwt.init_app(app)

    # Register blueprints
    from routes.admin import admin_bp
    from routes.analytics import analytics_bp
    from routes.auth    import auth_bp
    from routes.wallets import wallets_bp
    from routes.assets  import assets_bp
    from routes.trades  import trades_bp
    from routes.leverage import leverage_bp
    from routes.prices  import prices_bp
    from routes.portfolio import portfolio_bp

    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    app.register_blueprint(analytics_bp, url_prefix='/api/analytics')
    app.register_blueprint(auth_bp,      url_prefix='/api/auth')
    app.register_blueprint(wallets_bp,   url_prefix='/api/wallets')
    app.register_blueprint(assets_bp,    url_prefix='/api/assets')
    app.register_blueprint(trades_bp,    url_prefix='/api/trades')
    app.register_blueprint(leverage_bp,  url_prefix='/api/leverage')
    app.register_blueprint(prices_bp,    url_prefix='/api/prices')
    app.register_blueprint(portfolio_bp, url_prefix='/api/portfolio')

    return app

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000)
