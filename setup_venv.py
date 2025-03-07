#!/usr/bin/env python3
import os
import subprocess
import sys

def setup_venv():
    """Set up a virtual environment and install dependencies."""
    venv_dir = "terraform_analyzer_venv"
    
    # Check if venv already exists
    if os.path.exists(venv_dir):
        print(f"Virtual environment '{venv_dir}' already exists.")
        activate_command = f"source {venv_dir}/bin/activate" if sys.platform != "win32" else f"{venv_dir}\\Scripts\\activate"
        print(f"To activate it, run: {activate_command}")
        return
    
    # Create virtual environment
    print(f"Creating virtual environment in '{venv_dir}'...")
    subprocess.run([sys.executable, "-m", "venv", venv_dir], check=True)
    
    # Determine the pip path in the virtual environment
    if sys.platform == "win32":
        pip_path = os.path.join(venv_dir, "Scripts", "pip")
    else:
        pip_path = os.path.join(venv_dir, "bin", "pip")
    
    # Upgrade pip
    print("Upgrading pip...")
    subprocess.run([pip_path, "install", "--upgrade", "pip"], check=True)
    
    # Install dependencies
    print("Installing dependencies from requirements.txt...")
    subprocess.run([pip_path, "install", "-r", "requirements.txt"], check=True)
    
    # Print activation instructions
    if sys.platform == "win32":
        activate_cmd = f"{venv_dir}\\Scripts\\activate"
    else:
        activate_cmd = f"source {venv_dir}/bin/activate"
    
    print("\nSetup complete!")
    print(f"To activate the virtual environment, run: {activate_cmd}")

if __name__ == "__main__":
    setup_venv() 