# src/routes/user.py
from flask import Blueprint, render_template, session, redirect, url_for, request
from utils.db import db
from utils.auth import allowed_file
from werkzeug.utils import secure_filename
import os
from google.cloud import firestore  # Ensure this import is at the top




user_bp = Blueprint('user', __name__)

@user_bp.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    user = db.collection('users').document(user_id).get().to_dict()
    transactions_ref = db.collection('transactions')\
        .where('user_id', '==', user_id)\
        .where('transaction_type', '==', 'SELL')\
        .where('profit_loss', '!=', 0)\
        .order_by('timestamp', direction=firestore.Query.DESCENDING)\
        .limit(5)
    
    transactions = transactions_ref.stream()
    history = []
    for t in transactions:
        t_data = t.to_dict()
        history.append({
            'date': t_data['timestamp'].strftime('%Y-%m-%d %H:%M:%S'),
            'type': t_data['transaction_type'],
            'symbol': t_data['symbol'],
            'shares': t_data['shares'],
            'price': t_data['price'],
            'total': t_data['total_amount'],
            'profit_loss': round(t_data.get('profit_loss', 0.0), 2)
        })
    
    success = request.args.get('success')
    return render_template('dashboard.html.jinja2', 
                         user=user, 
                         transactions=history, 
                         success=success)

@user_bp.route('/settings', methods=['GET', 'POST'])
def settings():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    user_ref = db.collection('users').document(user_id)
    
    if request.method == 'POST':
        # Handle profile picture upload
        if 'profile_picture' in request.files:
            file = request.files['profile_picture']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = os.path.join(user_bp.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                
                # Update Firestore with the profile picture path
                user_ref.update({'profile_picture': url_for('static', filename=f'uploads/{filename}')})

        # Update other user settings
        user_ref.update({
            'background_color': request.form.get('background_color', '#ffffff'),
            'text_color': request.form.get('text_color', '#000000'),
            'accent_color': request.form.get('accent_color', '#007bff'),
            'gradient_color': request.form.get('gradient_color', "#000000")
        })
        return redirect(url_for('user.dashboard'))
    
    user = user_ref.get().to_dict()
    return render_template('settings.html.jinja2', user=user)


@user_bp.route('/delete_account', methods=['POST'])
def delete_account():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    user_ref = db.collection('users').document(user_id)

    # Delete user's portfolio
    portfolio_query = db.collection('portfolios').where('user_id', '==', user_id)
    for doc in portfolio_query.stream():
        doc.reference.delete()

    # Delete user's transactions
    transaction_query = db.collection('transactions').where('user_id', '==', user_id)
    for doc in transaction_query.stream():
        doc.reference.delete()

    # Delete user's badges
    user_badges_query = db.collection('user_badges').where('user_id', '==', user_id)
    for doc in user_badges_query.stream():
        doc.reference.delete()

    # Delete the user document
    user_ref.delete()

    # Clear the session
    session.clear()

    return redirect(url_for('home'))