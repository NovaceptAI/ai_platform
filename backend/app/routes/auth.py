from flask import Blueprint, request, jsonify
import jwt as pyjwt
import datetime, os
from functools import wraps
from app.services.auth_service import validate_credentials
from app.services.logging_service import log_endpoint
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt

# Load secret key from environment variables or set a default
SECRET_KEY = os.getenv("SECRET_KEY", "your_secret_key")

auth_bp = Blueprint('auth', __name__)

# In-memory user store (for demonstration purposes)
# Replace this with a database or secure user management system in production
USERS = {
    "admin": "password123",  # Example username and password
    "user1": "mypassword"
}

def token_required(f):
    """
    Decorator to protect routes and require a valid Bearer token.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({"error": "Token is missing!"}), 401

        try:
            token = token.split(" ")[1]  # Extract the token from "Bearer <token>"
            pyjwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        except pyjwt.ExpiredSignatureError:
            return jsonify({"error": "Token has expired!"}), 401
        except pyjwt.InvalidTokenError:
            return jsonify({"error": "Invalid token!"}), 401

        return f(*args, **kwargs)
    return decorated

@auth_bp.route('/login', methods=['POST'])
def login():
    print("✅ Login route hit")
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({"error": "Username and password are required!"}), 400

    if not validate_credentials(username, password):
        return jsonify({"error": "Invalid username or password!"}), 401

    token = pyjwt.encode({
        "sub": username,  # required for Flask-JWT-Extended
        "username": username,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)
    }, SECRET_KEY, algorithm="HS256")

    log_endpoint(username, '/auth/login', 'POST', request.remote_addr)

    return jsonify({"token": token})

@auth_bp.route('/protected', methods=['GET'])
@token_required
def protected():
    """
    Example of a protected route.
    """
    return jsonify({"message": "This is a protected route!"})


@auth_bp.route("/debug_token", methods=["GET"])
@jwt_required()
def debug_token():
    identity = get_jwt_identity()
    jwt_data = get_jwt()  # includes iat, exp, etc.

    return jsonify({
        "user_id": identity,
        "token_payload": jwt_data
    }), 200