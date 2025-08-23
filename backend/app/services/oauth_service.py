import os
from authlib.integrations.flask_client import OAuth
from flask import current_app, request


_oauth = None


def _get_oauth():
    global _oauth
    if _oauth is None:
        _oauth = OAuth(current_app)
        # Google
        _oauth.register(
            name='google',
            client_id=os.getenv('GOOGLE_CLIENT_ID', ''),
            client_secret=os.getenv('GOOGLE_CLIENT_SECRET', ''),
            server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
            client_kwargs={'scope': 'openid email profile'},
        )
        # Facebook
        _oauth.register(
            name='facebook',
            client_id=os.getenv('FACEBOOK_CLIENT_ID', ''),
            client_secret=os.getenv('FACEBOOK_CLIENT_SECRET', ''),
            access_token_url='https://graph.facebook.com/v12.0/oauth/access_token',
            authorize_url='https://www.facebook.com/v12.0/dialog/oauth',
            api_base_url='https://graph.facebook.com/',
            client_kwargs={'scope': 'email'},
        )
        # LinkedIn
        _oauth.register(
            name='linkedin',
            client_id=os.getenv('LINKEDIN_CLIENT_ID', ''),
            client_secret=os.getenv('LINKEDIN_CLIENT_SECRET', ''),
            access_token_url='https://www.linkedin.com/oauth/v2/accessToken',
            authorize_url='https://www.linkedin.com/oauth/v2/authorization',
            api_base_url='https://api.linkedin.com/v2/',
            client_kwargs={'scope': 'r_liteprofile r_emailaddress'},
        )
    return _oauth


def oauth_client(provider: str):
    oauth = _get_oauth()
    return getattr(oauth, provider, None)


def get_oauth_redirect_uri(provider: str):
    backend_base = os.getenv('BACKEND_BASE_URL', 'http://localhost:8000')
    return f"{backend_base}/api/auth/oauth/{provider}/callback"


def fetch_oauth_profile(provider: str, client):
    # Exchange and fetch profile per provider
    if provider == 'google':
        token = client.authorize_access_token()
        userinfo = token.get('userinfo')
        if not userinfo:
            userinfo = client.get('userinfo').json()
        return {
            'provider_user_id': userinfo.get('sub'),
            'email': userinfo.get('email'),
            'raw_profile': userinfo
        }
    elif provider == 'facebook':
        token = client.authorize_access_token()
        me = client.get('me?fields=id,name,email').json()
        return {
            'provider_user_id': me.get('id'),
            'email': me.get('email'),
            'raw_profile': me
        }
    elif provider == 'linkedin':
        token = client.authorize_access_token()
        me = client.get('me').json()
        email_res = client.get('emailAddress?q=members&projection=(elements*(handle~))').json()
        email = None
        try:
            email = email_res['elements'][0]['handle~']['emailAddress']
        except Exception:
            email = None
        return {
            'provider_user_id': me.get('id'),
            'email': email,
            'raw_profile': {'me': me, 'email': email_res}
        }
    else:
        raise ValueError('Unsupported provider')
