# setup.py
import os
import shutil
from pathlib import Path

def setup_config_files():
    """Setup configuration files from examples if they don't exist"""
    config_dir = Path("config")
    
    # List of config files to set up
    config_files = [
        ("creds_example.yaml", "creds.yaml"),
        ("override_config_example.yaml", "override_config.yaml")
    ]
    
    for example_file, target_file in config_files:
        example_path = config_dir / example_file
        target_path = config_dir / target_file
        
        if not target_path.exists() and example_path.exists():
            shutil.copy2(example_path, target_path)
            print(f"Created {target_file} from example file")
            print(f"Please update {target_file} with your actual configuration")
        elif target_path.exists():
            print(f"{target_file} already exists, skipping...")
        else:
            print(f"Warning: Example file {example_file} not found!")

def install_requirements():
    """Installing the required packages from requirements.txt"""
    print("Installing the required packages from requirements.txt")
    os.system("pip install -r requirements.txt")
    print("Insalled requireements successfully.")
    

if __name__ == "__main__":
    install_requirements()
    setup_config_files()