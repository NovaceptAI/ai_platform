# app/services/auth_service.py

# You can connect this to a real database later
USERS = {
    "admin": "password123",
    "user1": "mypassword"
}

def validate_credentials(username, password):
    """
    Validate if the username and password match.
    Replace this with DB logic in production.
    """
    return USERS.get(username) == password