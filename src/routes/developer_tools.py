# src/routes/developer_tools.py
from flask import Blueprint, render_template, session, redirect, url_for, request, jsonify, flash
from utils.db import db
from services.badge_services import award_badge, remove_duplicate_badges, fetch_user_badges

dev_tools_bp = Blueprint('dev_tools', __name__)

def is_developer(user_id):
    """Check if the user is authorized to access developer tools"""
    user = db.collection('users').document(user_id).get().to_dict()
    return user and user.get('username') == 'xiao'

@dev_tools_bp.route('/developer-tools')
def developer_tools():
    """Main developer tools page - restricted to username 'xiao'"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    user_id = session['user_id']
    
    if not is_developer(user_id):
        flash('Access denied. Developer tools are restricted.', 'error')
        return redirect(url_for('user.dashboard'))
    
    # If we got here, the user is authorized
    return render_template('developer_tools.html.jinja2')

@dev_tools_bp.route('/cleanup/badges', methods=['POST'])
def cleanup_badges():
    """API endpoint to clean up duplicate badges."""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    # Verify developer status
    user_id = session['user_id']
    if not is_developer(user_id):
        return jsonify({'error': 'Access denied'}), 403
    
    data = request.json
    target_user_id = data.get('user_id')  # Can be None to clean all users
    
    result = remove_duplicate_badges(target_user_id)
    return jsonify(result)

@dev_tools_bp.route('/debug/badges/<user_id>', methods=['GET'])
def debug_badges(user_id):
    """Get all badges for a specific user."""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
        
    # Verify developer status
    current_user_id = session['user_id']
    if not is_developer(current_user_id):
        return jsonify({'error': 'Access denied'}), 403
        
    badges = fetch_user_badges(user_id)
    return jsonify({
        'success': True,
        'badges': badges
    })

@dev_tools_bp.route('/debug/award_badge', methods=['POST'])
def debug_award_badge():
    """Developer endpoint to award badges to users."""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
        
    # Verify developer status
    current_user_id = session['user_id']
    if not is_developer(current_user_id):
        return jsonify({'error': 'Access denied'}), 403
        
    data = request.json
    target_user_id = data.get('user_id')
    badge_id = data.get('badge_id')
    
    if not target_user_id or not badge_id:
        return jsonify({
            'success': False,
            'error': 'Missing user_id or badge_id'
        })
        
    success = award_badge(target_user_id, badge_id)
    
    if success:
        return jsonify({
            'success': True,
            'message': f"Badge '{badge_id}' awarded to user '{target_user_id}'"
        })
    else:
        return jsonify({
            'success': False,
            'error': 'Failed to award badge or user already has this badge'
        })

@dev_tools_bp.route('/debug/constants')
def debug_constants():
    """Show all constants used in the application."""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
        
    # Verify developer status
    current_user_id = session['user_id']
    if not is_developer(current_user_id):
        return jsonify({'error': 'Access denied'}), 403
    
    from utils.constants import ACHIEVEMENTS, POPULAR_STOCKS, MARKET_INDICES
    
    return jsonify({
        'achievements': ACHIEVEMENTS,
        'popular_stocks': POPULAR_STOCKS,
        'market_indices': MARKET_INDICES
    })
