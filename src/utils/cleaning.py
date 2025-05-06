from utils.db import db
from flask import Flask
from services.badge_services import remove_duplicate_badges

def clean_duplicate_badges():
    """Run a one-time operation to clean up duplicate badges for all users."""
    print("Starting duplicate badge cleanup...")
    
    # Remove duplicate badges for all users
    count = remove_duplicate_badges()
    
    print(f"Duplicate badge cleanup completed.")
    return count

def run_cleanup():
    """Run all cleanup operations."""
    print("Starting database cleanup...")
    clean_duplicate_badges()
    print("Database cleanup completed.")

if __name__ == "__main__":
    # This allows running this script directly
    run_cleanup()
