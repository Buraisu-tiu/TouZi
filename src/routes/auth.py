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
    """Handle user login."""
    # This route receives the redirection from trading.py
    _debug_log("--- Entered login() function - PW_UPGRADE_MAY_19_V6 ---")
    
    # Always clear session when accessing login page
    session.clear()
    
    if request.method == 'POST':
        username_form = request.form.get('username', '').strip()
        email_form = request.form.get('email', '').strip().lower()
        password_submitted = request.form.get('password', '')

        _debug_log(f"Login attempt with username: '{username_form}', email: '{email_form}'")

        if not (username_form or email_form) or not password_submitted:
            flash('Please provide Username or Email, and Password.', 'error')
            _debug_log("Login failed: Missing (username/email) or password.")
            return redirect(url_for('auth.login'))

        try:
            users_ref = db.collection('users')
            user_doc_snapshot = None
            
            # Attempt to find user by username or email
            if username_form:
                _debug_log(f"Attempting lookup by username: '{username_form}'")
                query_username = users_ref.where(filter=firestore.FieldFilter('username', '==', username_form)).limit(1).stream()
                for doc in query_username:
                    user_doc_snapshot = doc
                    break
            
            if not user_doc_snapshot and email_form:
                _debug_log(f"User not found by username or username not provided. Attempting lookup by email: '{email_form}'")
                query_email = users_ref.where(filter=firestore.FieldFilter('email', '==', email_form)).limit(1).stream()
                for doc in query_email:
                    user_doc_snapshot = doc
                    break
            
            if not user_doc_snapshot or not user_doc_snapshot.exists:
                identifier_used = username_form if username_form else email_form
                _debug_log(f"Login failed: No user found for identifier '{identifier_used}'.")
                flash('Invalid credentials. Please try again.', 'error')
                return redirect(url_for('auth.login'))

            _debug_log(f"User document found. ID: {user_doc_snapshot.id}. Document exists: {user_doc_snapshot.exists}")
            
            user_data = user_doc_snapshot.to_dict()
            if user_data is None:
                _debug_log(f"CRITICAL: user_data is None after .to_dict() for user ID '{user_doc_snapshot.id}'.")
                flash('Critical account data error. Please contact support.', 'error')
                return redirect(url_for('auth.login'))

            user_id = user_doc_snapshot.id
            _debug_log(f"User data fetched: ID='{user_id}', Keys='{list(user_data.keys())}'")
            
            # Log user_data content for debugging the missing password_hash issue
            user_data_log_safe = {k: v for k, v in user_data.items() if k != 'password'} # Avoid logging plain password if it exists
            _debug_log(f"Contents of user_data (excluding plain password if present): {user_data_log_safe}")


            login_successful = False
            password_upgraded = False

            # Check for hashed password first
            if 'password_hash' in user_data and user_data['password_hash']:
                _debug_log(f"Found 'password_hash' for user ID '{user_id}'. Verifying.")
                stored_password_hash_str = user_data['password_hash']
                if isinstance(stored_password_hash_str, str):
                    stored_password_hash_bytes = stored_password_hash_str.encode('utf-8')
                    if bcrypt.checkpw(password_submitted.encode('utf-8'), stored_password_hash_bytes):
                        login_successful = True
                    else:
                        _debug_log(f"Password mismatch (hashed) for user ID '{user_id}'.")
                else:
                    _debug_log(f"Data_Warning: password_hash for user ID '{user_id}' is not a string. Type: {type(stored_password_hash_str)}.")
            
            # If no hash, check for plain text password and upgrade
            elif 'password' in user_data and user_data['password']:
                _debug_log(f"Found plain text 'password' field for user ID '{user_id}'. Attempting upgrade.")
                stored_plain_password = user_data['password']
                if password_submitted == stored_plain_password:
                    _debug_log(f"Plain text password matches for user ID '{user_id}'. Upgrading password storage.")
                    login_successful = True
                    try:
                        new_hashed_password_bytes = bcrypt.hashpw(password_submitted.encode('utf-8'), bcrypt.gensalt())
                        new_hashed_password_str = new_hashed_password_bytes.decode('utf-8')
                        
                        # Get the document reference to update
                        user_doc_ref_to_update = users_ref.document(user_id)
                        user_doc_ref_to_update.update({
                            'password_hash': new_hashed_password_str,
                            'password': firestore.DELETE_FIELD # Delete the old plain text password field
                        })
                        password_upgraded = True
                        _debug_log(f"Password storage upgraded for user ID '{user_id}'. Plain text 'password' field deleted.")
                    except Exception as e_upgrade:
                        _debug_log(f"ERROR during password upgrade for user ID '{user_id}': {str(e_upgrade)}")
                        flash('Logged in, but failed to update password security. Please contact support.', 'warning')
                else:
                    _debug_log(f"Password mismatch (plain text) for user ID '{user_id}'.")
            
            # If neither hashed nor plain password field is found
            else:
                _debug_log(f"Login failed: Neither 'password_hash' nor 'password' field found or both are empty for user ID '{user_id}'. Account data issue.")
                flash('Account configuration error. Password not set. Please contact support or try re-registering.', 'error')
                return redirect(url_for('auth.login'))

            if login_successful:
                session['user_id'] = user_id
                session['username'] = user_data.get('username', 'N/A') # Ensure username is fetched for session
                _debug_log(f"Login successful for user: '{user_data.get('username', user_id)}'. Session set.")
                if password_upgraded:
                    flash('Login successful. Your account security has been updated.', 'success')
                else:
                    flash('Login successful!', 'success')
                return redirect(url_for('user.dashboard')) # Redirect to dashboard on success
            else:
                # This handles cases where password_hash was present but mismatched,
                # or plain password was present but mismatched.
                _debug_log(f"Login failed for user ID '{user_id}' due to password mismatch or other validation failure prior to this point.")
                flash('Invalid credentials. Please try again.', 'error')
                return redirect(url_for('auth.login'))

        except Exception as e:
            _debug_log(f"An unexpected error occurred during login: {str(e)}")
            import traceback
            _debug_log(traceback.format_exc())
            flash('An error occurred. Please try again later.', 'error')
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