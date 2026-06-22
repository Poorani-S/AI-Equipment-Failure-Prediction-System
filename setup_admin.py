"""
Setup script to create a default admin user for the application.
Run this script once to initialize the admin account.
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import after loading env
from database.models import User, db
from utils.auth import AuthenticationManager

def setup_admin():
    """Create a default admin user if it doesn't exist."""
    
    print("=" * 60)
    print("AI Equipment Failure Prediction - Admin Setup")
    print("=" * 60)
    
    # Check database connection
    if db is None:
        print("\n⚠️  WARNING: MongoDB is not connected!")
        print("  The system will use local fallback storage.")
        print("  Make sure MongoDB is running on localhost:27017")
        print("  Or configure MONGODB_URI in your .env file\n")
    else:
        print("\n[OK] MongoDB is connected!")
    
    # Check if admin already exists
    print("\nChecking for existing admin user...")
    admin_user = User.find_by_username("admin")
    
    if admin_user:
        print("[OK] Admin user already exists!")
        print(f"  Username: admin")
        print(f"  Email: {admin_user.get('email', 'N/A')}")
        print(f"  Role: {admin_user.get('role', 'N/A')}")
        print("\n[OK] You can log in with the credentials provided during setup.")
        return
    
    # Create admin account
    print("\nCreating default admin account...")
    
    try:
        admin_username = "admin"
        admin_email = "admin@equipmentprediction.com"
        admin_password = "Admin@12345!"  # Meets validation: 8+ chars, uppercase, lowercase, digit, special char
        
        # Hash the password
        password_hash = AuthenticationManager.hash_password(admin_password)
        print(f"  Password hashed: {password_hash[:30]}...")
        
        # Create the user
        user_id = User.create_user(
            username=admin_username,
            email=admin_email,
            password_hash=password_hash,
            role="admin"
        )
        
        print(f"  User ID: {user_id}")
        print("[OK] Admin account created successfully!")
        
        # Verify the user was created
        verify_user = User.find_by_username(admin_username)
        if verify_user:
            print("[OK] User verified in database!")
        else:
            print("⚠️  Warning: Could not verify user immediately (might be a delay)")
        
        print("\n" + "=" * 60)
        print("LOGIN CREDENTIALS")
        print("=" * 60)
        print(f"Username: {admin_username}")
        print(f"Password: {admin_password}")
        print("=" * 60)
        print("\n⚠️  IMPORTANT:")
        print("  1. Change the admin password immediately after first login!")
        print("  2. Never share these credentials with unauthorized users.")
        print("  3. Store credentials securely.")
        print("\n[OK] You can now log in to the application.")
        print("  URL: http://127.0.0.1:5000/auth/login")
        
    except Exception as e:
        print(f"✗ Error creating admin user: {e}")
        import traceback
        traceback.print_exc()
        print("\nTroubleshooting:")
        print("  1. Make sure MongoDB is running:")
        print("     - Windows: mongod (from MongoDB bin folder)")
        print("     - Mac: brew services start mongodb-community")
        print("     - Linux: sudo systemctl start mongod")
        print("  2. Check your .env file for correct database connection")
        print("  3. Verify MONGODB_URI is properly configured")
        print("  4. If using local fallback, check fallback_data.json in database/ folder")
        sys.exit(1)

if __name__ == "__main__":
    setup_admin()
