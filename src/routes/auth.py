# src/routes/auth.py
from flask import Blueprint, request, session, redirect, url_for, render_template, flash
from utils.db import db
from google.cloud import firestore
from services.badge_services import check_and_award_badges
import bcrypt

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if password != confirm_password:
            flash('Passwords do not match!', 'error')
            return redirect(url_for('auth.register'))

        # Check if username or email already exists
        users_ref = db.collection('users')
        username_exists = users_ref.where(filter=firestore.FieldFilter('username', '==', username)).limit(1).get()
        email_exists = users_ref.where(filter=firestore.FieldFilter('email', '==', email)).limit(1).get()

        if username_exists:
            flash('Username already taken.', 'error')
            return redirect(url_for('auth.register'))
        if email_exists:
            flash('Email already registered.', 'error')
            return redirect(url_for('auth.register'))
            
        # Hash password
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        db.collection('users').add({
            'username': username,
            'email': email,  # Store email in database
            'password_hash': password_hash.decode('utf-8'),  # Store hashed password
            'balance': 990.00,
            'background_color': '#000000',
            'text_color': '#ffffff',
            'accent_color': '#007bff',
            'gradient_color': "#000000"
        })
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('register.html.jinja2')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        print(f"Login attempt: Username: {username}, Email: {email}, Password: {password}")

        # Query for user by username or email
        users_ref = db.collection('users')
        if username:
            query = users_ref.where(filter=firestore.FieldFilter('username', '==', username))
        elif email:
            query = users_ref.where(filter=firestore.FieldFilter('email', '==', email))
        else:
            flash('Please provide username or email.', 'error')
            return redirect(url_for('auth.login'))

        user_docs = query.limit(1).stream()
        user_data = None
        user_id = None

        for doc in user_docs:
            user_data = doc.to_dict()
            user_id = doc.id
            break 
            
        if user_data and bcrypt.checkpw(password.encode('utf-8'), user_data['password_hash'].encode('utf-8')):
            session['user_id'] = user_id
            session['username'] = user_data['username']
            print(f"User {user_data['username']} authenticated successfully.")

            # Check for first_login badge
            check_and_award_badges(user_id)

            flash('Login successful!', 'success')
            return redirect(url_for('user.dashboard'))
        else:
            flash('Invalid credentials. Please try again.', 'error')
            print("Authentication failed.")
            
    return render_template('login.html.jinja2')


@auth_bp.route('/documentation')
def documentation():
    return render_template('documentation.html.jinja2')

@auth_bp.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('auth.login'))
