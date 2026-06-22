"""
Quick setup to create admin user with custom password
"""

import os
from dotenv import load_dotenv

load_dotenv()

from database.models import User, db
from utils.auth import AuthenticationManager, PasswordValidator

def create_custom_admin():
    """Create admin with custom credentials."""
    
    username = "admin"
    password = "Admin@123"
    email = "admin@equipmentprediction.com"
    
    # Validate password
    is_valid, message = PasswordValidator.validate(password)
    if not is_valid:
        print(f"✗ Password validation failed: {message}")
        print("\nPassword must have:")
        print("  • At least 8 characters (you provided: {})".format(len(password)))
        print("  • Uppercase letter (A-Z)")
        print("  • Lowercase letter (a-z)")
        print("  • Digit (0-9)")
        print("  • Special character (!@#$%^&*() etc.)")
        return False
    
    # Check if user exists
    existing_user = User.find_by_username(username)
    if existing_user:
        print(f"✓ User '{username}' already exists!")
        print(f"  Try logging in with your password")
        return True
    
    # Create user
    try:
        password_hash = AuthenticationManager.hash_password(password)
        user_id = User.create_user(
            username=username,
            email=email,
            password_hash=password_hash,
            role="admin"
        )
        
        print("✓ Admin user created successfully!")
        print(f"\nLogin Details:")
        print(f"  Username: {username}")
        print(f"  Password: {password}")
        print(f"\nURL: http://127.0.0.1:5000/auth/login")
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

if __name__ == "__main__":
    create_custom_admin()
