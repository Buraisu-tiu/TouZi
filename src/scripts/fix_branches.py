import subprocess
import sys

def run_command(cmd):
    """Run a git command and return output"""
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"✓ {cmd}")
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"✗ Error running '{cmd}': {e.stderr}")
        return None

def fix_branches():
    """Fix branch issues by consolidating to main"""
    commands = [
        "git checkout main",
        "git branch temp_main",
        "git checkout temp_main",
        "git branch -D main",
        "git branch -m main",
        "git push -f origin main",
        "git branch -D temp_main",
        "git remote prune origin",
        "git fetch --prune"
    ]
    
    for cmd in commands:
        if not run_command(cmd):
            print("Error occurred, stopping.")
            sys.exit(1)

if __name__ == "__main__":
    fix_branches()
