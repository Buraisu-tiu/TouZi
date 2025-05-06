"""
Badge Award Testing Utility

Run this script to test awarding badges to users without going through the web interface.

Usage:
python -m utils.badge_test
"""

import sys
import os

# Add the src directory to the Python path to make local imports work
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.badge_services import award_badge, fetch_user_badges
from utils.db import db

def test_award_badge(user_id, badge_id):
    """Test function to award a badge directly."""
    print(f"Attempting to award badge '{badge_id}' to user '{user_id}'...")
    
    # Get user details
    user = db.collection('users').document(user_id).get()
    if user.exists:
        user_data = user.to_dict()
        print(f"Found user: {user_data.get('username')} (ID: {user_id})")
    else:
        print(f"ERROR: User with ID {user_id} not found")
        return
    
    # Award the badge directly
    result = award_badge(user_id, badge_id)
    
    if result:
        print(f"SUCCESS: Badge '{badge_id}' was awarded to user")
    else:
        print(f"FAILURE: Badge '{badge_id}' could not be awarded (user may already have it)")

def list_users():
    """List all users in the database."""
    print("\n=== Available Users ===")
    users = db.collection('users').stream()
    for user in users:
        user_data = user.to_dict()
        print(f"ID: {user.id}, Username: {user_data.get('username')}")

def list_badges():
    """List all available badge types."""
    from utils.constants import ACHIEVEMENTS
    
    print("\n=== Available Badges ===")
    for badge_id, badge_info in ACHIEVEMENTS.items():
        print(f"ID: {badge_id}, Name: {badge_info['name']}")

def get_user_badges(user_id):
    """List all badges for a specific user."""
    print(f"\n=== Badges for User ID: {user_id} ===")
    badges = fetch_user_badges(user_id)
    if badges:
        for badge in badges:
            print(f"- {badge['name']} ({badge['badge_id']}): {badge['description']}")
    else:
        print("No badges found for this user.")

if __name__ == "__main__":
    print("Badge Award Testing Utility")
    print("==========================")
    
    # List all users
    list_users()
    
    # List all available badges
    list_badges()
    
    # Get user ID
    user_id = input("\nEnter User ID to award badge to: ")
    
    # Show current badges for this user
    get_user_badges(user_id)
    
    # Get badge ID
    badge_id = input("\nEnter Badge ID to award: ")
    
    # Award badge
    test_award_badge(user_id, badge_id)
    
    # Show updated badges
    get_user_badges(user_id)
    
    print("\nDone!")
