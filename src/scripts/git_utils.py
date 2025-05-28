import subprocess
import os

def run_git_command(command):
    """Run a git command and return the output"""
    try:
        result = subprocess.run(command, 
                              shell=True, 
                              check=True,
                              capture_output=True,
                              text=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error executing git command: {e}")
        print(f"Error output: {e.stderr}")
        return None

def update_remote_url(new_url):
    """Update the remote URL for origin"""
    return run_git_command(f'git remote set-url origin {new_url}')

def force_push_main():
    """Force push to main branch"""
    return run_git_command('git push --force origin main')

def verify_remote():
    """Verify the current remote URL"""
    return run_git_command('git remote -v')

if __name__ == "__main__":
    # Update to new repository URL
    new_repo_url = "https://github.com/Buraisu-tiu/TouZi.git"
    
    print("Current remote configuration:")
    print(verify_remote())
    
    print("\nUpdating remote URL...")
    update_remote_url(new_repo_url)
    
    print("\nNew remote configuration:")
    print(verify_remote())
    
    print("\nForce pushing to main branch...")
    force_push_main()
