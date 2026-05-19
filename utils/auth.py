"""
Authentication utilities for user management and security.
Handles password hashing, validation, and user sessions.
"""

from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from flask import session, redirect, url_for, flash
import re


class PasswordValidator:
    """Validate passwords for security requirements."""
    
    @staticmethod
    def validate(password: str) -> tuple[bool, str]:
        """
        Validate password strength.
        Requirements:
        - At least 8 characters
        - At least one uppercase letter
        - At least one lowercase letter
        - At least one digit
        - At least one special character
        """
        if len(password) < 8:
            return False, "Password must be at least 8 characters long"
        
        if not re.search(r"[A-Z]", password):
            return False, "Password must contain at least one uppercase letter"
        
        if not re.search(r"[a-z]", password):
            return False, "Password must contain at least one lowercase letter"
        
        if not re.search(r"\d", password):
            return False, "Password must contain at least one digit"
        
        if not re.search(r"[!@#$%^&*()_+=\-\[\]{};:,.<>?]", password):
            return False, "Password must contain at least one special character"
        
        return True, "Password is valid"


class AuthenticationManager:
    """Manage user authentication and sessions."""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using Werkzeug security."""
        return generate_password_hash(password, method="pbkdf2:sha256")
    
    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """Verify a password against its hash."""
        return check_password_hash(password_hash, password)
    
    @staticmethod
    def set_user_session(user_id: str, username: str, role: str):
        """Set user session after successful login."""
        session["user_id"] = user_id
        session["username"] = username
        session["role"] = role
        session.permanent = True
    
    @staticmethod
    def clear_user_session():
        """Clear user session on logout."""
        session.clear()
    
    @staticmethod
    def is_user_logged_in() -> bool:
        """Check if a user is currently logged in."""
        return "user_id" in session
    
    @staticmethod
    def get_current_user() -> dict:
        """Get the current logged-in user information."""
        return {
            "user_id": session.get("user_id"),
            "username": session.get("username"),
            "role": session.get("role"),
        }


def login_required(f):
    """Decorator to require login for a route."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not AuthenticationManager.is_user_logged_in():
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Decorator to require admin role for a route."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not AuthenticationManager.is_user_logged_in():
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("auth.login"))
        
        current_user = AuthenticationManager.get_current_user()
        if current_user.get("role") != "admin":
            flash("You do not have permission to access this page.", "danger")
            return redirect(url_for("dashboard.index"))
        
        return f(*args, **kwargs)
    return decorated_function


class EmailValidator:
    """Validate email addresses."""
    
    @staticmethod
    def validate(email: str) -> bool:
        """Validate email format."""
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        result = re.match(pattern, email) is not None
        return result
    
    @staticmethod
    def validate_with_reason(email: str) -> tuple[bool, str]:
        """Validate email and return reason if invalid."""
        if not email:
            return False, "Email is required"
        
        if len(email) > 255:
            return False, "Email is too long"
        
        if not EmailValidator.validate(email):
            return False, "Invalid email format"
        
        return True, "Email is valid"


class UsernameValidator:
    """Validate usernames."""
    
    @staticmethod
    def validate(username: str) -> bool:
        """
        Validate username format.
        - 3-20 characters
        - Only alphanumeric and underscores
        """
        if len(username) < 3 or len(username) > 20:
            return False
        
        return re.match(r"^[a-zA-Z0-9_]+$", username) is not None
    
    @staticmethod
    def validate_with_reason(username: str) -> tuple[bool, str]:
        """Validate username and return reason if invalid."""
        if not username:
            return False, "Username is required"
        
        if len(username) < 3:
            return False, "Username must be at least 3 characters"
        
        if len(username) > 20:
            return False, "Username must be at most 20 characters"
        
        if not re.match(r"^[a-zA-Z0-9_]+$", username):
            return False, "Username can only contain letters, numbers, and underscores"
        
        return True, "Username is valid"
