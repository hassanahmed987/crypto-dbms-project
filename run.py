"""
run.py — Start the CryptoTrack Flask server.

Usage:
    python run.py
    python run.py --port 8000
"""
import argparse
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv is optional

from app import create_app
from extensions import db

app = create_app()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=5000)
    parser.add_argument('--host', default='0.0.0.0')
    args = parser.parse_args()

    with app.app_context():
        db.create_all()
        print("✓ Database tables verified / created")

    print(f"✓ CryptoTrack API running → http://localhost:{args.port}")
    print(f"  Docs: see README.md for all endpoints\n")
    app.run(host=args.host, port=args.port, debug=os.environ.get('FLASK_DEBUG', '1') == '1')
