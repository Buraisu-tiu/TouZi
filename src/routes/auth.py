# src/routes/auth.py
from flask import Blueprint, request, session, redirect, url_for, render_template, flash
from utils.db import db

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']  # Add email field
        password = request.form['password']
        
        # Check if username or email already exists
        existing_user = db.collection('users').where('username', '==', username).get()
        existing_email = db.collection('users').where('email', '==', email).get()
        
        if existing_user:
            flash('Username already exists', 'error')
            return redirect(url_for('auth.register'))
        if existing_email:
            flash('Email already registered', 'error')
            return redirect(url_for('auth.register'))

        db.collection('users').add({
            'username': username,
            'email': email,  # Store email in database
            'password': password,
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
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        print(f"Login attempt: Username: {username}, Email: {email}, Password: {password}")

        try:
            # Query Firestore for both username AND email
            users_ref = db.collection('users')\
                .where('username', '==', username)\
                .where('email', '==', email)\
                .get()

            if not users_ref:
                print(f"No user found with username: {username} and email: {email}")
                flash('Invalid credentials', 'error')
                return redirect(url_for('auth.login'))

            # Validate the password
            for user in users_ref:
                user_data = user.to_dict()
                if user_data.get('password') == password:
                    print(f"User {username} authenticated successfully.")
                    session['user_id'] = user.id
                    flash('Login successful!', 'success')
                    return redirect(url_for('user.dashboard'))
                else:
                    print(f"Invalid password for username: {username}")
                    flash('Invalid credentials', 'error')
                    return redirect(url_for('auth.login'))

        except Exception as e:
            print(f"Error during login: {e}")
            flash('An error occurred', 'error')
            return redirect(url_for('auth.login'))
    
    return render_template('login.html.jinja2')


@auth_bp.route('/documentation')
def documentation():
    return render_template('documentation.html.jinja2')

@auth_bp.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('auth.login'))
