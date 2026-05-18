# CDP Automation Tool

A command-line tool for automating CDP entity creation and setup. This tool supports creating various CDP entities like data streams, segments, targets, and activations either individually or in batch.

## Features
- Interactive CLI interface
- Batch creation of entities
- Configurable using YAML files
- Ordered entity creation respecting dependencies
- Both interactive and command-line modes

## Project Structure
```
cdp_automation/
├── config/
│   ├── base_config.yaml    # Default configurations
│   ├── my_config.yaml      # Your specific configurations
│   └── creds.yaml          # Credentials
├── utils/
│   ├── __init__.py
│   ├── auth.py            # Authentication handling
│   ├── api.py             # API client
│   └── config_loader.py   # Configuration management
└── main.py                # Main CLI script
```

## Setup

1. Clone the repository:
```bash
git clone 
cd cdp_automation
```

2. Install required packages:
```bash
pip install -r requirements.txt
```

3. Initialize configuration files:
```bash
python setup.py
```
This will create:
- `config/creds.yaml` from `creds_example.yaml`
- `config/override_config.yaml` from `override_config_example.yaml`

4. Update the configuration files with your actual values:
   - Edit `config/creds.yaml` with your credentials
   - Edit `config/override_config.yaml` with your entity configurations

Note: The actual configuration files (`creds.yaml` and `override_config.yaml`) are git-ignored to prevent accidental commits of sensitive information.

## Configuration Files

### Example Files
- `creds_example.yaml`: Template for credentials configuration
- `override_config_example.yaml`: Template for entity configurations

These example files:
- Serve as documentation
- Show the required structure
- Provide sample values
- Are version controlled

### Actual Configuration Files
- `creds.yaml`: Your actual credentials
- `override_config.yaml`: Your actual entity configurations

These files:
- Are created by copying the example files
- Contain your actual configurations
- Are git-ignored
- Should never be committed to version control

## Usage

### Interactive Mode
Simply run:
```bash
python main.py
```
This will show an interactive menu where you can:
- Create single entities
- Create all entities of a specific type
- Setup everything
- List available entity types

### Command Line Mode
1. List available entity types:
```bash
python main.py list-types
```

2. Create a specific entity:
```bash
python main.py create targets --name target1
```

3. Create all entities of a type:
```bash
python main.py create targets --all
```

4. Create everything:
```bash
python main.py setup-all
```

## Extending the Tool

### Adding a New Entity Type

1. Add the base configuration in `config/base_config.yaml`:
```yaml
new_entity:
  base:
    field1: "default_value"
    field2: "default_value"
```

2. Add your specific configurations in `config/my_config.yaml`:
```yaml
new_entity:
  entity1:
    name: "Entity1"
    field1: "custom_value"
```

3. Add the entity type to `ENTITY_CONFIGS` in `main.py`:
```python
ENTITY_CONFIGS = [
    # Existing configs...
    {
        'type': 'new_entity',
        'endpoint': 'new-entity-endpoint',
        'description': 'Description of new entity',
        'order': 5  # Order in which it should be created
    }
]
```

### Modifying Entity Configuration

1. Base Configuration (`base_config.yaml`):
   - Contains default values for all fields
   - Modify this to change default behavior

2. Override Configuration (`my_config.yaml`):
   - Contains your specific instances
   - Only need to specify fields that differ from base config

### Adding New Features

1. Add new API functionality:
   - Extend the `CDPAPI` class in `utils/api.py`
   - Add new methods for specific API calls

2. Add new CLI commands:
   - Add new functions with `@cli.command()` decorator in `main.py`
   - Add new options to interactive menu if needed

3. Add new configuration options:
   - Add new fields to configuration files
   - Update config loader if needed

## File Descriptions

### Configuration Files

1. `base_config.yaml`:
   - Contains default configurations for all entity types
   - Serves as a template and documentation

2. `my_config.yaml`:
   - Contains your specific entity configurations
   - Override default values from base config

3. `creds.yaml`:
   - Contains all required credentials
   - Never commit this file to version control

### Python Files

1. `main.py`:
   - Main entry point
   - Contains CLI logic and interactive menu
   - Defines entity types and their order

2. `utils/api.py`:
   - Handles API communication
   - Contains generic entity creation logic

3. `utils/auth.py`:
   - Handles authentication
   - Manages credentials and tokens

4. `utils/config_loader.py`:
   - Loads and merges configurations
   - Handles base and override configs