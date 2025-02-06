# routes/auth.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, session
from flask_login import login_user, logout_user, login_required, current_user
from oauthlib.oauth2 import WebApplicationClient
import requests
import json
from urllib.parse import urlparse
from db.manager import user_manager
from db.models import User
from functools import cached_property

auth = Blueprint('auth', __name__)

class GoogleAuth:
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        self.app = app

    @cached_property
    def client(self):
        return WebApplicationClient(current_app.config['GOOGLE_CLIENT_ID'])

# Create a global instance that will be initialized with the app
google_auth = GoogleAuth()

def get_google_provider_cfg():
    """Get Google's OAuth 2.0 provider configuration"""
    try:
        return requests.get(
            "https://accounts.google.com/.well-known/openid-configuration"
        ).json()
    except Exception as e:
        current_app.logger.error(f"Error fetching Google provider config: {e}")
        return None

def is_safe_url(target):
    """Validates if a URL is safe to redirect to"""
    ref_url = urlparse(request.host_url)
    test_url = urlparse(target)
    return (not test_url.scheme and not test_url.netloc) or \
           (test_url.scheme == ref_url.scheme and test_url.netloc == ref_url.netloc)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    """Handle both regular and Google login"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        if request.form.get('login_type') == 'google':
            # Handle Google login
            google_provider_cfg = get_google_provider_cfg()
            if not google_provider_cfg:
                flash('Error connecting to Google')
                return redirect(url_for('auth.login'))
            
            authorization_endpoint = google_provider_cfg["authorization_endpoint"]
            request_uri = google_auth.client.prepare_request_uri(
                authorization_endpoint,
                redirect_uri=request.base_url + "/callback",
                scope=["openid", "email", "profile"],
            )
            return redirect(request_uri)
        else:
            # Handle regular login
            email = request.form.get('email')
            password = request.form.get('password')
            remember = bool(request.form.get('remember'))

            user_doc = user_manager.get_user_by_email(email)
            
            if user_doc and user_manager.verify_password(user_doc, password):
                user = User(user_doc)
                login_user(user, remember=remember)
                
                next_page = request.args.get('next')
                if next_page and is_safe_url(next_page):
                    return redirect(next_page)
                
                return redirect(url_for('index'))
            
            flash('Invalid email or password')

    return render_template('auth/login.html')

@auth.route('/login/callback')
def google_callback():
    """Handle the Google OAuth 2.0 callback"""
    code = request.args.get("code")
    if not code:
        flash('Error during Google login')
        return redirect(url_for('auth.login'))

    try:
        google_provider_cfg = get_google_provider_cfg()
        token_endpoint = google_provider_cfg["token_endpoint"]

        token_url, headers, body = google_auth.client.prepare_token_request(
            token_endpoint,
            authorization_response=request.url,
            redirect_url=request.base_url,
            code=code
        )
        token_response = requests.post(
            token_url,
            headers=headers,
            data=body,
            auth=(current_app.config['GOOGLE_CLIENT_ID'], 
                  current_app.config['GOOGLE_CLIENT_SECRET']),
        )

        google_auth.client.parse_request_body_response(json.dumps(token_response.json()))

        userinfo_endpoint = google_provider_cfg["userinfo_endpoint"]
        uri, headers, body = google_auth.client.add_token(userinfo_endpoint)
        userinfo_response = requests.get(uri, headers=headers, data=body)

        if userinfo_response.json().get("email_verified"):
            google_email = userinfo_response.json()["email"]
            google_name = userinfo_response.json()["given_name"]

            user_doc = user_manager.get_user_by_email(google_email)
            if not user_doc:
                user_doc = user_manager.create_user(
                    username=google_name,
                    email=google_email,
                    password=None,
                    google_id=userinfo_response.json()["sub"]
                )

            if user_doc:
                user = User(user_doc)
                login_user(user)
                return redirect(url_for('index'))

        flash('Google login failed')
        return redirect(url_for('auth.login'))

    except Exception as e:
        current_app.logger.error(f"Error in Google callback: {e}")
        flash('Error during Google login')
        return redirect(url_for('auth.login'))

@auth.route('/register', methods=['GET', 'POST'])
def register():
    """Handle user registration"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        email = request.form.get('email')
        username = request.form.get('username')
        password = request.form.get('password')

        if user_manager.get_user_by_email(email):
            flash('Email already registered')
            return redirect(url_for('auth.register'))

        user_doc = user_manager.create_user(
            username=username,
            email=email,
            password=password
        )

        if user_doc:
            user = User(user_doc)
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Registration failed. Please try again.')

    return render_template('auth/register.html')

@auth.route('/logout')
@login_required
def logout():
    """Handle user logout"""
    if current_user.is_authenticated:
        email = current_user.email
        logout_user()
        current_app.logger.info(f"User {email} logged out")
    return redirect(url_for('index'))