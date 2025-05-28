# src/routes/auth.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from utils.db import db 
import bcrypt
from datetime import datetime
import time
from google.cloud import firestore # Explicitly import for FieldFilter and DELETE_FIELD

# Ensure this version identifier is present and reflects the latest changes
print("--- LOADING auth.py - VERSION: PW_UPGRADE_MAY_19_V6_DETAILED_REG_LOG ---") 

auth_bp = Blueprint('auth', __name__)

def _debug_log(message):
    """Helper for consistent debug logging."""
    # Using V6 to match the intended version with the fix
    print(f"[AUTH_DEBUG_V6_DETAILED_REG_LOG] {datetime.now()}: {message}")

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Enhanced login handler with better error handling."""
    if request.method == 'POST':
        print("[AUTH_DEBUG_V6_DETAILED_REG_LOG] --- Entered login() function - PW_UPGRADE_MAY_19_V6 ---")
        
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        email = request.form.get('email', '').strip()
        
        print(f"[AUTH_DEBUG_V6_DETAILED_REG_LOG] Login attempt with username: '{username}', email: '{email}'")
        
        try:
            # Look up user by username
            users_ref = db.collection('users')
            query = users_ref.where('username', '==', username)
            user_docs = query.stream()
            
            user_doc = None
            for doc in user_docs:
                user_doc = doc
                break
            
            if user_doc:
                print(f"[AUTH_DEBUG_V6_DETAILED_REG_LOG] User document found. ID: {user_doc.id}")
                user_data = user_doc.to_dict()
                
                # Debug print user data (excluding sensitive info)
                safe_user_data = {k:v for k,v in user_data.items() if k != 'password'}
                print(f"[AUTH_DEBUG_V6_DETAILED_REG_LOG] User data fetched: {safe_user_data}")
                
                if 'password_hash' in user_data:
                    if bcrypt.checkpw(password.encode('utf-8'), user_data['password_hash'].encode('utf-8')):
                        session.clear()
                        session['user_id'] = user_doc.id
                        session['username'] = username
                        
                        print(f"[AUTH_DEBUG_V6_DETAILED_REG_LOG] Login successful for user: '{username}'")
                        return redirect(url_for('user.dashboard'))
                    else:
                        print("[AUTH_DEBUG_V6_DETAILED_REG_LOG] Password verification failed")
                else:
                    print("[AUTH_DEBUG_V6_DETAILED_REG_LOG] No password hash found in user data")
            else:
                print(f"[AUTH_DEBUG_V6_DETAILED_REG_LOG] No user found with username: '{username}'")
            
            flash('Invalid username or password', 'error')
            
        except Exception as e:
            print(f"[AUTH_DEBUG_V6_DETAILED_REG_LOG] Error during login: {str(e)}")
            traceback.print_exc()
            flash('An error occurred during login. Please try again.', 'error')
        
        return redirect(url_for('auth.login'))
    
    return render_template('login.html.jinja2')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    _debug_log("--- Entered register() function ---")
    if request.method == 'POST':
        _debug_log("Register: POST request received.")
        _debug_log(f"Register: Raw form data received: {request.form}") 
        
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '') # Gets value or empty string if key exists but no value, or if key doesn't exist.
                                                    # .get('password') without a default would return None if key is missing.
                                                    # Using default '' is fine for checking if it's empty.

        _debug_log(f"Register: Value received for 'username': '{username}' (Is empty: {not username})")
        _debug_log(f"Register: Value received for 'email': '{email}' (Is empty: {not email})")
        _debug_log(f"Register: Value received for 'password': '{'*' * len(password) if password else ''}' (Is empty: {not password})") # Log password length or empty

        missing_fields = []
        if not username:
            missing_fields.append("Username")
            _debug_log("Register: Username field is empty.")
        if not email:
            missing_fields.append("Email")
            _debug_log("Register: Email field is empty.")
        if not password:
            missing_fields.append("Password")
            _debug_log("Register: Password field is empty.")

        if missing_fields:
            error_message = f"The following fields are required: {', '.join(missing_fields)}."
            flash(error_message, 'error')
            _debug_log(f"Registration failed: Missing fields - {', '.join(missing_fields)}. Redirecting to register page.")
            return redirect(url_for('auth.register'))
        
        _debug_log("Register: All required fields (username, email, password) appear to be present and non-empty.")

        if "@" not in email or "." not in email.split('@')[-1]:
            flash('Invalid email format.', 'error')
            _debug_log(f"Registration failed: Invalid email format for '{email}'. Redirecting to register page.")
            return redirect(url_for('auth.register'))
        
        _debug_log(f"Register: Email format for '{email}' is valid.")

        try:
            _debug_log("Register: Attempting database operations.")
            users_ref = db.collection('users')

            # Check if username exists
            _debug_log(f"Register: Checking if username '{username}' exists.")
            username_exists_query = users_ref.where(filter=firestore.FieldFilter('username', '==', username)).limit(1).stream()
            username_docs = list(username_exists_query)
            if len(username_docs) > 0:
                flash('Username already taken.', 'error')
                _debug_log(f"Registration failed: Username '{username}' already taken. Redirecting to register page.")
                return redirect(url_for('auth.register'))
            _debug_log(f"Register: Username '{username}' is available.")

            # Check if email exists
            _debug_log(f"Register: Checking if email '{email}' exists.")
            email_exists_query = users_ref.where(filter=firestore.FieldFilter('email', '==', email)).limit(1).stream()
            email_docs = list(email_exists_query)
            if len(list(email_docs)) > 0:
                flash('Email already registered.', 'error')
                _debug_log(f"Registration failed: Email '{email}' already registered. Redirecting to register page.")
                return redirect(url_for('auth.register'))
            _debug_log(f"Register: Email '{email}' is available.")
            
            # Hash the password
            _debug_log("Register: Attempting to hash password.")
            hashed_password_bytes = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            hashed_password_str = hashed_password_bytes.decode('utf-8')
            _debug_log("Register: Password hashed successfully.")
            
            # Create new user document
            new_user_data = {
                'username': username,
                'email': email,
                'password_hash': hashed_password_str, 
                'balance': 1000.0, # Default starting balance changed to 1000
                'created_at': datetime.utcnow(),
                'profile_picture': '/static/uploads/default.png', 
                'theme': 'dark', 
                'background_color': '#0a0a0a',
                'text_color': '#ffffff',
                'accent_color': '#64ffda',
                'hover_color': '#0891b2'
            }
            _debug_log(f"Register: New user data prepared: { {k: v for k, v in new_user_data.items() if k != 'password_hash'} }")
            
            _debug_log("Register: Attempting to add new user to Firestore.")
            update_time, user_ref = db.collection('users').add(new_user_data)
            _debug_log(f"User '{username}' registered successfully with ID: {user_ref.id}. Stored password_hash. Update time: {update_time}")
            
            flash('Registration successful! Please login.', 'success')
            _debug_log("Register: Registration complete. Redirecting to login page.")
            return redirect(url_for('auth.login'))

        except Exception as e:
            _debug_log(f"An unexpected error occurred during registration: {str(e)}")
            import traceback
            _debug_log(f"Traceback: {traceback.format_exc()}")
            flash('An error occurred during registration. Please try again.', 'error')
            _debug_log("Register: Error occurred. Redirecting to register page.")
            return redirect(url_for('auth.register'))
    else:
        _debug_log("Register: GET request received, rendering registration page.")
            
    return render_template('register.html.jinja2')

@auth_bp.route('/logout')
def logout():
    """Simple logout that clears session"""
    _debug_log(f"User '{session.get('username', 'Unknown')}' (ID: {session.get('user_id', 'Unknown')}) attempting to logout.")
    session.clear()
    flash('You have been logged out.', 'success')
    _debug_log("Session cleared. Redirecting to login.")
    return redirect(url_for('auth.login'))

@auth_bp.route('/documentation')
def documentation():
    return render_template('documentation.html.jinja2')