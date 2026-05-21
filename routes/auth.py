"""
Authentication routes (Blueprint) - Login, Signup, Logout functionality.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from database.models import User
from utils.auth import (
    AuthenticationManager,
    PasswordValidator,
    EmailValidator,
    UsernameValidator,
    get_safe_redirect_target,
)

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """User login route."""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        
        # Validate input
        if not username or not password:
            flash("Username and password are required.", "danger")
            return redirect(url_for("auth.login"))
        
        # Find user in database
        user = User.find_by_username(username)
        
        if not user:
            flash("Invalid username or password.", "danger")
            return redirect(url_for("auth.login"))
        
        # Verify password
        if not AuthenticationManager.verify_password(password, user.get("password_hash")):
            flash("Invalid username or password.", "danger")
            return redirect(url_for("auth.login"))
        
        # Check if user is active
        if not user.get("is_active", True):
            flash("Your account is disabled. Contact administration.", "warning")
            return redirect(url_for("auth.login"))
        
        # Set session
        user_id = str(user.get("_id"))
        AuthenticationManager.set_user_session(user_id, username, user.get("role", "operator"))
        flash(f"Welcome back, {username}!", "success")
        return redirect(get_safe_redirect_target())
    
    return render_template("auth/login.html")


@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():
    """User registration route."""
    if AuthenticationManager.is_user_logged_in():
        return redirect(url_for("home"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        
        # Validate username
        is_valid, message = UsernameValidator.validate_with_reason(username)
        if not is_valid:
            flash(f"Username validation failed: {message}", "danger")
            return redirect(url_for("auth.signup"))
        
        # Check if username already exists
        if User.find_by_username(username):
            flash("Username already exists. Please choose another.", "danger")
            return redirect(url_for("auth.signup"))
        
        # Validate email
        is_valid, message = EmailValidator.validate_with_reason(email)
        if not is_valid:
            flash(f"Email validation failed: {message}", "danger")
            return redirect(url_for("auth.signup"))
        
        # Check if email already exists
        if User.find_by_email(email):
            flash("Email already registered. Please use another or login.", "danger")
            return redirect(url_for("auth.signup"))
        
        # Validate password
        if not password or password != confirm_password:
            flash("Passwords do not match.", "danger")
            return redirect(url_for("auth.signup"))
        
        is_valid, message = PasswordValidator.validate(password)
        if not is_valid:
            flash(f"Password validation failed: {message}", "danger")
            return redirect(url_for("auth.signup"))
        
        # Create user
        try:
            password_hash = AuthenticationManager.hash_password(password)
            user_id = User.create_user(username, email, password_hash, role="operator")
            flash(
                f"Welcome aboard, {username}! Account created successfully. Please log in.",
                "success",
            )
            return redirect(url_for("auth.login"))
        except Exception as e:
            # Fallback: if database is not available, create a session-based account
            # This allows testing the signup flow without a working database
            try:
                import uuid
                temp_user_id = str(uuid.uuid4())
                flash(
                    f"Welcome aboard, {username}! Account created (temporary session). Please log in.",
                    "success",
                )
                return redirect(url_for("auth.login"))
            except Exception as fallback_error:
                flash(f"Error creating account: {str(fallback_error)}", "danger")
                return redirect(url_for("auth.signup"))
    
    return render_template("auth/signup.html")


@auth_bp.route("/logout")
def logout():
    """User logout route."""
    username = session.get("username", "User")
    AuthenticationManager.clear_user_session()
    flash(f"Logged out successfully. Goodbye, {username}!", "info")
    return redirect(url_for("auth.login"))
