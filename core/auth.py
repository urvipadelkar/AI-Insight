"""
Authentication utilities for AI-Insight
Handles password hashing, encryption, and session management
"""

from werkzeug.security import generate_password_hash, check_password_hash
from cryptography.fernet import Fernet
import os
import secrets


class PasswordManager:
    """Handle password hashing and verification"""

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password using werkzeug's Bcrypt"""
        return generate_password_hash(password, method='pbkdf2:sha256')

    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """Verify password against hash"""
        return check_password_hash(password_hash, password)


class EncryptionManager:
    """Handle encryption/decryption of sensitive data (DB passwords, credentials)"""

    def __init__(self):
        """Initialize encryption key from environment"""
        key = os.environ.get('ENCRYPTION_KEY')
        if not key:
            # Generate new key if not exists (should be stored in .env for production)
            key = Fernet.generate_key().decode()
            print(f"[WARN] No ENCRYPTION_KEY in .env. Generated temporary key: {key}")
            print("[WARN] Store this in your .env file for consistency")
        self.cipher = Fernet(key.encode() if isinstance(key, str) else key)

    def encrypt(self, plaintext: str) -> str:
        """Encrypt string"""
        if not plaintext:
            return ""
        return self.cipher.encrypt(plaintext.encode()).decode()

    def decrypt(self, encrypted_text: str) -> str:
        """Decrypt string"""
        if not encrypted_text:
            return ""
        try:
            return self.cipher.decrypt(encrypted_text.encode()).decode()
        except Exception as e:
            print(f"[ERROR] Decryption failed: {e}")
            return ""

    @staticmethod
    def generate_key() -> str:
        """Generate new encryption key"""
        return Fernet.generate_key().decode()


class SessionValidator:
    """Validate user sessions and tokens"""

    @staticmethod
    def generate_session_token() -> str:
        """Generate secure random session token"""
        return secrets.token_urlsafe(32)

    @staticmethod
    def is_valid_email(email: str) -> bool:
        """Basic email validation"""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None

    @staticmethod
    def is_strong_password(password: str) -> tuple:
        """
        Validate password strength
        Returns: (is_valid: bool, feedback: str)
        """
        if len(password) < 8:
            return False, "Password must be at least 8 characters long"
        
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)

        if not (has_upper and has_lower and has_digit):
            return False, "Password must contain uppercase, lowercase, and numbers"
        
        return True, "Password is strong"

    @staticmethod
    def validate_username(username: str) -> tuple:
        """
        Validate username format
        Returns: (is_valid: bool, feedback: str)
        """
        if len(username) < 5:
            return False, "Username must be at least 5 characters"
        
        if len(username) > 80:
            return False, "Username must be less than 80 characters"
        
        import re
        if not re.match(r'^[a-zA-Z0-9._-]+$', username):
            return False, "Username can only contain letters, numbers, dots, dashes, and underscores"
        
        return True, "Username is valid"


# ═════════════════════════════════════════════════════════════════════════
# FLASK-LOGIN INTEGRATION
# ═════════════════════════════════════════════════════════════════════════

from flask_login import UserMixin


class UserLogin(UserMixin):
    """Flask-Login user wrapper"""

    def __init__(self, user_id, username, email, is_admin=False):
        self.id = user_id
        self.username = username
        self.email = email
        self.is_admin = is_admin

    def __repr__(self):
        return f"<UserLogin(id={self.id}, username={self.username})>"


# ═════════════════════════════════════════════════════════════════════════
# DECORATOR FOR PROTECTING ROUTES
# ═════════════════════════════════════════════════════════════════════════

from functools import wraps
from flask import redirect, session, url_for
import dash
from dash.exceptions import PreventUpdate


def login_required(f):
    """Dash callback decorator to require login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if user session exists
        if 'user_id' not in session:
            # Redirect to login page
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Dash callback decorator to require admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect('/login')
        
        if session.get('is_admin') != True:
            return redirect('/')  # Unauthorized
        
        return f(*args, **kwargs)
    return decorated_function
