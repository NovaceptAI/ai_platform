#!/usr/bin/env python3
"""
WebSocket Server for Real-Time Collaboration Features

This is a separate server dedicated to handling WebSocket connections
using eventlet for async support. It runs independently from the main
Gunicorn API server.

The main Flask API (served by Gunicorn) handles REST API requests.
This server handles WebSocket connections for real-time features.
"""

import os
import sys
import logging
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Monkey patch for eventlet BEFORE importing Flask/SocketIO
import eventlet
eventlet.monkey_patch()

# Now import Flask and SocketIO components
from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from app.db import db
from app import models
from app.logging_setup import configure_logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_socketio_app():
    """Create Flask app specifically for WebSocket handling."""
    app = Flask(__name__)

    # Configuration - MUST match main.py exactly for JWT validation
    JWT_SECRET = os.getenv('JWT_SECRET', 'your_secret_key')
    app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET', 'dev_secret_key')
    app.config['JWT_SECRET_KEY'] = JWT_SECRET  # Match main app JWT secret
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_size': 5,
        'pool_recycle': 3600,
        'pool_pre_ping': True,
    }

    # Initialize extensions
    db.init_app(app)
    JWTManager(app)
    configure_logging(app)

    # CORS configuration for WebSocket
    cors_origins = [
        "http://172.178.120.199:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3000",
        "https://scoolish.com",
        "https://www.scoolish.com"
    ]
    CORS(app, origins=cors_origins, supports_credentials=True)

    # Initialize WebSocket with eventlet
    from app.services.websocket_service import init_socketio
    socketio = init_socketio(app)

    # Update SocketIO to use eventlet async mode
    socketio.async_mode = 'eventlet'

    logger.info("WebSocket server initialized with eventlet")
    logger.info(f"CORS origins: {cors_origins}")
    logger.info(f"Database: {app.config['SQLALCHEMY_DATABASE_URI'][:50]}...")

    return app, socketio


def main():
    """Run the WebSocket server."""
    app, socketio = create_socketio_app()

    # Get configuration from environment
    host = os.getenv('SOCKETIO_HOST', '0.0.0.0')
    port = int(os.getenv('SOCKETIO_PORT', '8001'))
    debug = os.getenv('FLASK_ENV', 'production') == 'development'

    logger.info(f"Starting WebSocket server on {host}:{port}")
    logger.info(f"Debug mode: {debug}")
    logger.info(f"Async mode: {socketio.async_mode}")

    # Run with eventlet
    socketio.run(
        app,
        host=host,
        port=port,
        debug=debug,
        use_reloader=False,  # Disable reloader in production
        log_output=True,
        allow_unsafe_werkzeug=True  # Required for production with eventlet
    )


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info("WebSocket server shutting down...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Failed to start WebSocket server: {e}", exc_info=True)
        sys.exit(1)
