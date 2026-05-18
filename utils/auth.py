import requests
import yaml
import json
from typing import Dict

def load_creds(creds_file: str = 'config/creds.yaml') -> Dict:
    """Load credentials from YAML file"""
    with open(creds_file, 'r') as f:
        return yaml.safe_load(f)

def get_token(creds_file: str = 'config/creds.yaml') -> Dict:
    """Get authentication token using credentials"""
    creds = load_creds(creds_file)
    
    url = f"{creds['org']['instance_url']}/services/oauth2/token"
    payload = {
        "grant_type": "password",
        "client_id": creds['org']['client_id'],
        "client_secret": creds['org']['client_secret'],
        "username": creds['org']['username'],
        "password": creds['org']['password']
    }
    
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    
    response = requests.post(url, headers=headers, data=payload)
    print("response", response.json())
    return response.json()

