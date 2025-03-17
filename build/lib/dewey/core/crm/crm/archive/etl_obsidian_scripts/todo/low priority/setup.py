import subprocess
import sys

def setup_environment():
    """Setup the Python environment with required packages"""
    required_packages = [
        'pandas',
        'duckdb',
        'python-dotenv',
        'mimetypes-magic'
    ]
    
    print("Checking and installing required packages...")
    
    for package in required_packages:
        try:
            subprocess.check_call([
                sys.executable, 
                '-m', 
                'pip', 
                'install', 
                package
            ])
            print(f"✓ {package} installed/verified")
        except subprocess.CalledProcessError:
            print(f"✗ Error installing {package}")
            return False
    
    print("\nAll required packages installed!")
    return True

if __name__ == "__main__":
    setup_environment() 