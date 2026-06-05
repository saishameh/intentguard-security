#!/usr/bin/env python3
"""
IntentGuard Setup Script

This script guides you through the initial setup process.
"""

import os
import sys
import subprocess


def print_banner():
    """Print welcome banner"""
    print("""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║                     INTENTGUARD SETUP                        ║
║   AI-Powered Smart Home Automation Framework                ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
    """)


def check_python_version():
    """Ensure Python 3.9+"""
    print("🔍 Checking Python version...")
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 9):
        print(f"❌ Python 3.9+ required. You have {version.major}.{version.minor}")
        return False
    print(f"✓ Python {version.major}.{version.minor}.{version.micro}")
    return True


def install_dependencies():
    """Install required packages"""
    print("\n📦 Installing dependencies...")
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
            check=True,
            capture_output=True
        )
        print("✓ Dependencies installed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False


def setup_env_file():
    """Create .env file from template"""
    print("\n🔑 Setting up environment variables...")
    
    if os.path.exists(".env"):
        response = input(".env file already exists. Overwrite? (y/n): ").strip().lower()
        if response != 'y':
            print("✓ Keeping existing .env file")
            return True
    
    # Copy template
    if not os.path.exists(".env.template"):
        print("❌ .env.template not found")
        return False
    
    with open(".env.template", "r") as f:
        template = f.read()
    
    print("\nYou'll need API keys from:")
    print("  • Google AI: https://makersuite.google.com/app/apikey")
    print("  • Pinecone: https://app.pinecone.io/")
    
    google_key = input("\nEnter your Google AI API key: ").strip()
    pinecone_key = input("Enter your Pinecone API key: ").strip()
    
    if not google_key or not pinecone_key:
        print("❌ Both API keys are required")
        return False
    
    # Create .env file
    env_content = f"""# API Keys Configuration
GOOGLE_API_KEY={google_key}
PINECONE_API_KEY={pinecone_key}
PINECONE_INDEX_NAME=flowise
PINECONE_ENVIRONMENT=us-east-1
"""
    
    with open(".env", "w") as f:
        f.write(env_content)
    
    print("✓ .env file created")
    return True


def check_data_files():
    """Check if required data files exist"""
    print("\n📄 Checking data files...")
    
    required_files = [
        "smartthings_data.txt",
        "test_rules.json"
    ]
    
    missing = []
    for file in required_files:
        if os.path.exists(file):
            print(f"✓ {file} found")
        else:
            print(f"❌ {file} missing")
            missing.append(file)
    
    if missing:
        print(f"\n⚠️  Missing files: {', '.join(missing)}")
        print("Please ensure these files are in the current directory")
        return False
    
    return True


def run_data_ingestion():
    """Run the data ingestion script"""
    print("\n🔄 Running data ingestion...")
    response = input("This will create a Pinecone index and upload data. Continue? (y/n): ").strip().lower()
    
    if response != 'y':
        print("⏭️  Skipping data ingestion (you can run it later with: python ingest_data.py)")
        return True
    
    try:
        subprocess.run([sys.executable, "ingest_data.py"], check=True)
        print("✓ Data ingestion complete")
        return True
    except subprocess.CalledProcessError:
        print("❌ Data ingestion failed")
        return False


def print_next_steps():
    """Print next steps"""
    print("""
╔══════════════════════════════════════════════════════════════╗
║                    SETUP COMPLETE! 🎉                        ║
╚══════════════════════════════════════════════════════════════╝

Next steps:

1. Try the CLI:
   python cli.py create "Turn off lights when motion stops"

2. Interactive mode:
   python cli.py interactive

3. Run tests:
   python test_suite.py

4. View saved rules:
   python cli.py list

For help:
   python cli.py --help

Documentation: See README.md

Happy automating! 🏠🤖
    """)


def main():
    """Main setup flow"""
    print_banner()
    
    # Step 1: Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Step 2: Install dependencies
    if not install_dependencies():
        print("\n⚠️  Setup incomplete. Please install dependencies manually:")
        print("   pip install -r requirements.txt")
        sys.exit(1)
    
    # Step 3: Setup .env file
    if not setup_env_file():
        print("\n⚠️  Setup incomplete. Please create .env file manually")
        sys.exit(1)
    
    # Step 4: Check data files
    if not check_data_files():
        print("\n⚠️  Setup incomplete. Please add required data files")
        sys.exit(1)
    
    # Step 5: Run data ingestion
    if not run_data_ingestion():
        print("\n⚠️  Data ingestion incomplete. Run manually:")
        print("   python ingest_data.py")
    
    # Done!
    print_next_steps()


if __name__ == "__main__":
    main()