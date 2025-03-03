# src/routes/auth.py
from flask import Blueprint, request, session, redirect, url_for, render_template
from utils.db import db

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db.collection('users').add({
            'username': username,
            'password': password,
            'balance': 990.00,
            'background_color': '#000000',
            'text_color': '#ffffff',
            'accent_color': '#007bff',
            'gradient_color': "#000000"
        
        })
        return redirect(url_for('login'))
    return render_template('register.html.jinja2')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        print(f"Login attempt: Username: {username}, Password: {password}")

        try:
            print("Attempting to test firestore test query")
            test_query = db.collection('users').limit(1).get()
            print(f"Firestore test query succeeded. Found {len(test_query)} document(s).")
        except Exception as e:
            print(f"Firestore test query failed: {e}")


        try:
            # Query Firestore for the username
            print("Attempting to query Firestore...")
            users_ref = db.collection('users').where('username', '==', username).get()
            print(f"Query executed. Retrieved {len(users_ref)} document(s).")

            if not users_ref:
                print(f"No user found with username: {username}")
                return 'Invalid credentials'

            # Validate the password
            for user in users_ref:
                user_data = user.to_dict()
                print(f"User data: {user_data}")
                if user_data.get('password') == password:
                    print(f"User {username} authenticated successfully.")
                    session['user_id'] = user.id
                    return redirect(url_for('user.dashboard'))
                else:
                    print(f"Invalid password for username: {username}")
                    return 'Invalid credentials'
        except Exception as e:
            print(f"Error during login: {e}")
            return 'An error occurred'
    
    return render_template('login.html.jinja2')


@auth_bp.route('/documentation')
def documentation():
    return render_template('documentation.html.jinja2')

@auth_bp.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))
