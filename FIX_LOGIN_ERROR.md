# 🔧 Fix: Invalid Username or Password Error

## Problem
You're getting "Invalid username or password" error when trying to log in.

## Solution

### Step 1: Verify Admin User Exists
First, check if the admin account was created:
```bash
python setup_admin.py
```

This will either:
- ✅ Confirm admin user exists, or
- ✅ Create it if it doesn't exist

### Step 2: Use the Correct Credentials
After running the setup script, you should see:
```
LOGIN CREDENTIALS
==================
Username: admin
Password: Admin@12345!
==================
```

### Step 3: Log In
1. Go to http://127.0.0.1:5000/auth/login
2. Enter:
   - **Username:** `admin`
   - **Password:** `Admin@12345!` (with the exclamation mark!)
3. Click **Login**

### Step 4: Change Your Password (IMPORTANT!)
Once logged in:
1. Go to your profile/settings
2. Change the default password to something you prefer
3. Never share your credentials

---

## Troubleshooting

### Error: "Could not verify user in database"
**Solution:** MongoDB might not be running

```bash
# Windows - Start MongoDB
mongod

# Or check if MongoDB Service is running in Services
```

### Still can't log in after setup?
1. **Clear your browser cache:**
   - Press Ctrl+Shift+Delete
   - Clear cookies and cache
   - Refresh the page

2. **Check MongoDB is running:**
   ```bash
   # Test connection
   python
   >>> from pymongo import MongoClient
   >>> client = MongoClient('mongodb://localhost:27017')
   >>> client.admin.command('ping')
   ```

3. **Check database fallback:**
   - If MongoDB fails, the app uses `database/fallback_data.json`
   - Check if this file exists and contains the admin user

### Password not working?
Make sure you're using the EXACT password from setup_admin.py output:
- **Username:** `admin` (lowercase)
- **Password:** `Admin@12345!` (exact case and special characters)

---

## Password Requirements
Passwords must have:
- ✅ At least 8 characters
- ✅ At least one UPPERCASE letter (A-Z)
- ✅ At least one lowercase letter (a-z)
- ✅ At least one digit (0-9)
- ✅ At least one special character (!@#$%^&*() etc.)

Example valid passwords:
- `Admin@12345!`
- `Password@2024`
- `Secure#Pass123`

---

## Still Having Issues?

### Run this diagnostic:
```bash
python
>>> from database.models import User
>>> admin = User.find_by_username("admin")
>>> print(admin)
```

If it shows `None`, the user doesn't exist in the database. Run setup_admin.py again.

### Check logs:
Look for error messages in:
- Browser console (F12 → Console tab)
- Terminal output when you ran the app
- `logs/error.log` file in your project

---

## Default Credentials Reference
| Field | Value |
|-------|-------|
| Username | admin |
| Password | Admin@12345! |
| Role | admin |
| Email | admin@equipmentprediction.com |

**⚠️ Change the password after first login!**
