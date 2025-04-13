import os
import json
import pathlib
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Ensure storage directory exists first
pathlib.Path('storage').mkdir(exist_ok=True)

# Configure panels directory
PANELS_DIRECTORY = 'storage/panels'
pathlib.Path(PANELS_DIRECTORY).mkdir(exist_ok=True)
PANELS_FILE = os.path.join(PANELS_DIRECTORY, 'panels.json')

def load_panels():
    """Load saved panels from JSON file"""
    if not os.path.exists(PANELS_FILE):
        return {}
    
    try:
        with open(PANELS_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading panels: {str(e)}")
        return {}

def save_panels(panels):
    """Save panels to JSON file"""
    try:
        with open(PANELS_FILE, 'w') as f:
            json.dump(panels, f, indent=4)
        return True
    except Exception as e:
        print(f"Error saving panels: {str(e)}")
        return False 