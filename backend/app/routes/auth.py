from flask import Blueprint, request, jsonify
import jwt as pyjwt
import datetime, os
from functools import wraps
from app.services.auth_service import validate_credentials
from app.services.logging_service import log_endpoint
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt, create_access_token, verify_jwt_in_request

# Load secret key from environment variables or set a default
# SECRET_KEY = os.getenv("SECRET_KEY", "your_secret_key")

auth_bp = Blueprint('auth', __name__)

# In-memory user store (for demonstration purposes)
# Replace this with a database or secure user management system in production
# USERS = {
#     "admin": "password123",  # Example username and password
#     "user1": "mypassword"
# }

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        verify_jwt_in_request()  # validates Authorization: Bearer <token> using JWT_SECRET_KEY
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
    
    access_token = create_access_token(identity=username, additional_claims={"username": username})
    log_endpoint(username, '/auth/login', 'POST', request.remote_addr)
    return jsonify({"token": access_token}), 200

    # token = pyjwt.encode({
    #     "sub": username,  # required for Flask-JWT-Extended
    #     "username": username,
    #     "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)
    # }, SECRET_KEY, algorithm="HS256")

    # log_endpoint(username, '/auth/login', 'POST', request.remote_addr)

    # return jsonify({"token": token})

@auth_bp.route('/protected', methods=['GET'])
@jwt_required()
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