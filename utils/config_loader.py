import yaml
from typing import Dict, Any, List
from copy import deepcopy

class ConfigLoader:
    def __init__(self, base_config_path: str = 'config/base_config.yaml', 
                 override_config_path: str = 'config/override_config.yaml'):
        self.base_config = self._load_yaml(base_config_path)
        self.override_config = self._load_yaml(override_config_path)
        
    def _load_yaml(self, path: str) -> Dict:
        """Load YAML file"""
        with open(path, 'r') as f:
            return yaml.safe_load(f)
    
    def _deep_merge(self, base: Dict, override: Dict) -> Dict:
        """Recursively merge two dictionaries, with override taking precedence"""
        result = deepcopy(base)
        
        for key, value in override.items():
            if isinstance(value, dict) and key in result and isinstance(result[key], dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = deepcopy(value)
                
        return result
    
    def get_entity_config(self, entity_type: str, entity_name: str) -> Dict[str, Any]:
        """
        Get merged config for any entity type
        
        Args:
            entity_type: Type of entity (e.g., 'targets', 'activations', 'segments')
            entity_name: Name of the specific entity
            
        Returns:
            Dict containing merged configuration
        """
        if entity_type not in self.base_config:
            raise ValueError(f"Entity type {entity_type} not found in base config")
            
        if 'base' not in self.base_config[entity_type]:
            raise ValueError(f"Base template not found for entity type {entity_type}")
            
        base_entity = deepcopy(self.base_config[entity_type]['base'])
        
        if entity_type not in self.override_config:
            raise ValueError(f"Entity type {entity_type} not found in override config")
            
        if entity_name not in self.override_config[entity_type]:
            raise ValueError(f"{entity_type} {entity_name} not found in override config")
            
        override_entity = self.override_config[entity_type][entity_name]
        return self._deep_merge(base_entity, override_entity)
    
    def get_all_entity_names(self, entity_type: str) -> List[str]:
        """
        Get all entity names of a specific type from override config
        
        Args:
            entity_type: Type of entity (e.g., 'targets', 'activations', 'segments')
            
        Returns:
            List of entity names
        """
        if entity_type not in self.override_config:
            return []
        return list(self.override_config[entity_type].keys())
    
    def get_available_entity_types(self) -> List[str]:
        """Get all available entity types from base config"""
        return [key for key in self.base_config.keys() if key != 'defaults']
