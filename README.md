# CryptoTrack — Crypto Portfolio & Leverage Tracker
**DBMS Project | Team: Muhammad Aazmeer, Abdullah, Hassan Ahmed Siddiqui**

---

## Project Structure

```
crypto_tracker/
├── app.py                  ← Flask app factory & entry point
├── config.py               ← Configuration (DB URL, JWT secret, CoinGecko)
├── extensions.py           ← SQLAlchemy & JWT instances
├── models.py               ← All database models
├── requirements.txt        ← Python dependencies
├── schema.sql              ← MySQL schema + seed data
├── routes/
│   ├── auth.py             ← Register / Login / Me
│   ├── wallets.py          ← Wallet CRUD
│   ├── assets.py           ← Asset holdings CRUD
│   ├── trades.py           ← Trade recording + auto asset update
│   ├── leverage.py         ← Open / close leveraged positions
│   ├── prices.py           ← CoinGecko live prices + cache
│   └── portfolio.py        ← Full P&L summary
└── frontend/
    └── index.html          ← Full single-page dashboard (no framework)
```

---

## Setup Instructions

### 1. Install MySQL and create the database

```sql
-- In MySQL shell:
mysql -u root -p
source /path/to/crypto_tracker/schema.sql
```

### 2. Set up Python environment

```bash
cd crypto_tracker
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure your environment

Edit `config.py` and update the database URL:

```python
SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://YOUR_USER:YOUR_PASSWORD@localhost/crypto_tracker'
```

Or set environment variables:
```bash
export DATABASE_URL="mysql+pymysql://root:password@localhost/crypto_tracker"
export SECRET_KEY="your-secret-key"
export JWT_SECRET_KEY="your-jwt-secret"
```

### 4. Run the Flask backend

```bash
python app.py
# Server starts at: http://localhost:5000
```

### 5. Open the frontend

Open `frontend/index.html` in your browser directly, OR serve it:
```bash
cd frontend
python -m http.server 8080
# Open: http://localhost:8080
```

---

## Demo Credentials

After running `schema.sql`:

| Username | Password | Role    |
|----------|----------|---------|
| admin    | *(set manually via /api/auth/register)* | admin |
| trader1  | *(set manually)* | trader |

Use the Register tab in the UI to create your account.

---

## API Endpoints

### Auth
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Register new user |
| POST | `/api/auth/login` | Login, returns JWT token |
| GET  | `/api/auth/me` | Get current user info |

### Wallets
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET  | `/api/wallets/` | List user's wallets |
| POST | `/api/wallets/` | Create wallet |
| DELETE | `/api/wallets/<id>` | Delete wallet |

### Assets
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET  | `/api/assets/<wallet_id>` | Get holdings |
| POST | `/api/assets/<wallet_id>` | Add/update asset |
| DELETE | `/api/assets/<wallet_id>/<asset_id>` | Remove asset |

### Trades
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET  | `/api/trades/<wallet_id>` | Trade history |
| POST | `/api/trades/<wallet_id>` | Record buy/sell trade |

### Leverage
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET  | `/api/leverage/<wallet_id>?status=open` | List positions |
| POST | `/api/leverage/<wallet_id>` | Open position |
| POST | `/api/leverage/<wallet_id>/<id>/close` | Close position |

### Prices (CoinGecko)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET  | `/api/prices/<symbol>` | Live price for one symbol |
| POST | `/api/prices/batch` | Prices for multiple symbols |
| GET  | `/api/prices/supported` | List supported symbols |

### Portfolio
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET  | `/api/portfolio/summary` | Full P&L summary |

---

## Features Implemented

- ✅ JWT Authentication (register, login, protected routes)
- ✅ Multiple wallets per user (spot, margin, futures)
- ✅ Asset tracking with average buy price
- ✅ Buy/Sell trade recording with automatic asset update
- ✅ Leverage position management (open/close with P&L)
- ✅ Liquidation price calculation
- ✅ Live prices via CoinGecko API (5-min cache in DB)
- ✅ Full portfolio P&L summary with unrealized gains
- ✅ Admin and Trader roles
- ✅ Full frontend dashboard (no framework, pure HTML/CSS/JS)

---

## Supported Cryptocurrencies

BTC, ETH, SOL, BNB, XRP, ADA, DOGE, AVAX, DOT, MATIC, LINK, UNI, LTC, ATOM, NEAR

*(More can be added in `routes/prices.py` → SYMBOL_MAP)*
