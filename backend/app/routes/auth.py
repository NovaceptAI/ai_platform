from flask import Blueprint, request, jsonify, redirect
import jwt as pyjwt
import datetime, os
from functools import wraps
from app.services.auth_service import validate_credentials
from app.services.logging_service import log_endpoint
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt, create_access_token, verify_jwt_in_request
from app.db import db
from app.models.users import Users
from app.models.user_identity import UserIdentity
from app.services.oauth_service import oauth_client, get_oauth_redirect_uri, fetch_oauth_profile
from werkzeug.security import check_password_hash

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

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json() or {}
    username = (data.get('username') or '').strip()
    email = (data.get('email') or '').strip()
    password = data.get('password')
    if not username or not email or not password:
        return jsonify({"error": "username, email, password are required"}), 400

    from werkzeug.security import generate_password_hash
    if Users.query.filter((Users.username == username) | (Users.email == email)).first():
        return jsonify({"error": "Username or email already exists"}), 409

    user = Users(
        username=username,
        email=email,
        password_hash=generate_password_hash(password),
        role='user'
    )
    db.session.add(user)
    db.session.commit()

    access_token = create_access_token(identity=str(user.id), additional_claims={"username": user.username})
    log_endpoint(user.username, '/auth/register', 'POST', request.remote_addr)
    return jsonify({"token": access_token}), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    print("✅ Login route hit")
    data = request.get_json() or {}
    username = (data.get('username') or '').strip()
    password = data.get('password')

    if not username or not password:
        return jsonify({"error": "Username and password are required!"}), 400

    from werkzeug.security import check_password_hash
    user = Users.query.filter_by(username=username).first()
    if not user or not user.password_hash or not user.password_hash.strip():
        return jsonify({"error": "Invalid username or password!"}), 401

    try:
        if not check_password_hash(user.password_hash, password):
            return jsonify({"error": "Invalid username or password!"}), 401
    except ValueError:
        return jsonify({"error": "Invalid username or password!"}), 401
    
    access_token = create_access_token(identity=str(user.id), additional_claims={"username": user.username})
    log_endpoint(user.username, '/auth/login', 'POST', request.remote_addr)
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


# --- OAuth Social Login ---

@auth_bp.route('/oauth/<provider>/start', methods=['GET'])
def oauth_start(provider):
    client = oauth_client(provider)
    if client is None:
        return jsonify({"error": "Unsupported provider"}), 400
    redirect_uri = get_oauth_redirect_uri(provider)
    return client.authorize_redirect(redirect_uri)


@auth_bp.route('/oauth/<provider>/callback', methods=['GET'])
def oauth_callback(provider):
    client = oauth_client(provider)
    if client is None:
        return jsonify({"error": "Unsupported provider"}), 400

    try:
        profile = fetch_oauth_profile(provider, client)
    except Exception as e:
        return jsonify({"error": f"OAuth failed: {e}"}), 400

    provider_user_id = profile.get('provider_user_id')
    email = profile.get('email')

    if not provider_user_id:
        return jsonify({"error": "Missing provider_user_id"}), 400

    identity = UserIdentity.query.filter_by(provider=provider, provider_user_id=provider_user_id).first()
    if identity:
        user = Users.query.filter_by(id=identity.user_id).first()
    else:
        user = None
        if email:
            user = Users.query.filter_by(email=email).first()
        if not user:
            # Create a user with minimal info; account_type is null until onboarding begin
            # create user for social login
            user = Users(
                username=email or f"{provider}_{provider_user_id}",
                email=email or f"{provider}_{provider_user_id}@example.com",
                password_hash=None,  # not ""
                role="user",
            )
            db.session.add(user)
            db.session.flush()

        identity = UserIdentity(
            user_id=user.id,
            provider=provider,
            provider_user_id=provider_user_id,
            email=email,
            raw_profile=profile.get('raw_profile')
        )
        db.session.add(identity)
        db.session.commit()

    token_identity = str(user.id)
    access_token = create_access_token(identity=token_identity, additional_claims={"username": user.username})

    frontend_base = os.getenv('FRONTEND_BASE_URL', 'http://localhost:3000')
    return redirect(f"{frontend_base}/ai/onboarding?token={access_token}")