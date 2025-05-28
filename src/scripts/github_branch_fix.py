import subprocess
import sys
import os

def run_git_command(cmd):
    """Run a git command and return output"""
    try:
        print(f"\nExecuting: {cmd}")
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"Output: {result.stdout}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error: {e.stderr}")
        return False

def fix_branches():
    """Fix GitHub branch issues"""
    commands = [
        "git fetch origin",
        "git checkout master",
        "git branch backup_master",
        "git checkout main",
        "git branch -m main current_main",
        "git branch -m master main",
        "git push -f origin main",
        "git branch -d backup_master",
        "git branch -d current_main"
    ]
    
    for cmd in commands:
        if not run_git_command(cmd):
            print("\nError occurred during branch fix.")
            print("Please ensure you've changed the default branch on GitHub first:")
            print("1. Go to https://github.com/Buraisu-tiu/TouZi/settings/branches")
            print("2. Change default branch from 'master' to 'main'")
            print("3. Run this script again")
            sys.exit(1)

if __name__ == "__main__":
    # Ensure we're in the correct directory
    repo_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(repo_path)
    print(f"Working directory: {os.getcwd()}")
    
    fix_branches()
