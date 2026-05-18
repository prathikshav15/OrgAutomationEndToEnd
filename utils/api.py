import requests
import json
from typing import Dict, Any
from .config_loader import ConfigLoader

class CDPAPI:
    def __init__(self, token_info: Dict):
        self.token_info = token_info
        self.config_loader = ConfigLoader()
        
    def get_headers(self) -> Dict[str, str]:
        return {
            'Authorization': f"Bearer {self.token_info['access_token']}",
            'Content-Type': 'application/json'
        }
    
    def create_entity(self, entity_type: str, entity_name: str, endpoint: str) -> Dict[str, Any]:
        """
        Generic method to create any type of entity
        """
        entity_config = self.config_loader.get_entity_config(entity_type, entity_name)
        url = f"{self.token_info['instance_url']}/services/data/v61.0/ssot/{endpoint}"
        
        print(f"\nRequest URL: {url}")
        print(f"Request payload:")
        print(json.dumps(entity_config, indent=2))
        
        try:
            response = requests.post(url, headers=self.get_headers(), json=entity_config)
            response_json = response.json()
            
            if response.status_code >= 400:
                print(f"\nError Response (Status {response.status_code}):")
                print(json.dumps(response_json, indent=2))
                print("\nRequest Headers:")
                print(json.dumps(self.get_headers(), indent=2))
            
            return response_json
            
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {str(e)}")
            raise