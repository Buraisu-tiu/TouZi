# src/routes/developer_tools.py
from flask import Blueprint, render_template, session, redirect, url_for, request, jsonify, flash
from utils.db import db
from services.badge_services import award_badge, remove_duplicate_badges, fetch_user_badges
import json

dev_tools_bp = Blueprint('dev_tools', __name__)

@dev_tools_bp.route('/cleanup/badges', methods=['POST'])
def cleanup_badges():
    """Clean up duplicate badges for users."""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
    user_id = session['user_id']
    user = db.collection('users').document(user_id).get().to_dict()
    
    if user.get('username') != 'xiao':  # Only allow admin user
        return jsonify({'success': False, 'error': 'Access denied'}), 403
        
    try:
        data = request.json
        target_user_id = data.get('user_id')
        
        removed = remove_duplicate_badges(target_user_id)
        
        if removed:
            return jsonify({
                'success': True, 
                'message': f"Removed duplicate badges for {'specific user' if target_user_id else 'all users'}"
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to remove duplicates'
            })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@dev_tools_bp.route('/debug/badges/<user_id>', methods=['GET'])
def debug_user_badges(user_id):
    """Debug endpoint to see all badge records for a user."""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
        
    current_user_id = session['user_id']
    current_user = db.collection('users').document(current_user_id).get().to_dict()
    
    if current_user.get('username') != 'xiao':  # Only allow admin user
        return jsonify({'error': 'Access denied'}), 403
        
    try:
        # Get all raw badge records
        badge_records = db.collection('user_badges').where('user_id', '==', user_id).stream()
        raw_badges = [{'id': doc.id, 'data': doc.to_dict()} for doc in badge_records]
        
        # Get processed badges
        processed_badges = fetch_user_badges(user_id)
        
        # Get user info
        user = db.collection('users').document(user_id).get().to_dict()
        user_info = {
            'username': user.get('username', 'Unknown'),
            'email': user.get('email', 'Unknown')
        }
        
        return jsonify({
            'user_info': user_info,
            'raw_badge_records': raw_badges,
            'processed_badges': processed_badges,
            'record_count': len(raw_badges),
            'processed_count': len(processed_badges)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@dev_tools_bp.route('/debug/award_badge', methods=['POST'])
def debug_award_badge():
    """Debug endpoint to manually award a badge and see the result."""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
        
    current_user_id = session['user_id']
    current_user = db.collection('users').document(current_user_id).get().to_dict()
    
    if current_user.get('username') != 'xiao':  # Only allow admin user
        return jsonify({'error': 'Access denied'}), 403
        
    try:
        data = request.json
        target_user_id = data.get('user_id')
        badge_id = data.get('badge_id')
        
        if not target_user_id or not badge_id:
            return jsonify({'error': 'Missing user_id or badge_id'}), 400
            
        # Award the badge
        result = award_badge(target_user_id, badge_id)
        
        # Get the updated badges
        updated_badges = fetch_user_badges(target_user_id)
        
        return jsonify({
            'success': result,
            'message': 'Badge awarded successfully' if result else 'Failed to award badge',
            'updated_badges': updated_badges
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@dev_tools_bp.route('/debug/constants')
def debug_constants():
    """Debug endpoint to check available constants."""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
        
    current_user_id = session['user_id']
    current_user = db.collection('users').document(current_user_id).get().to_dict()
    
    if current_user.get('username') != 'xiao':  # Only allow admin user
        return jsonify({'error': 'Access denied'}), 403
        
    try:
        from utils.constants import ACHIEVEMENTS
        
        return jsonify({
            'achievements': {k: v for k, v in ACHIEVEMENTS.items()}
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
