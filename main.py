# main.py
import click
import json
import sys
from utils.api import CDPAPI
from utils.auth import get_token
from utils.config_loader import ConfigLoader

# Define entity configurations as an ordered list
ENTITY_CONFIGS = [
    {
        'type': 'segments',
        'endpoint': 'segments',
        'description': 'Segments for data export'
    },
    {
        'type': 'connectors',
        'endpoint': 'connections?connectorType',
        'description': 'Connectors'
    },
    {
        'type': 'targets',
        'endpoint': 'activation-targets',
        'description': 'Activation targets for data export'
    },
    {
        'type': 'activations',
        'endpoint': 'activations',
        'description': 'Data activations'
    }
]

def get_entity_config(entity_type):
    """Helper function to get entity config by type"""
    for config in ENTITY_CONFIGS:
        if config['type'] == entity_type:
            return config
    return None

# Core functions that will be used by both CLI and interactive mode
def create_single_entity(entity_type, name):
    """Core function to create a single entity"""
    config = get_entity_config(entity_type)
    if not config:
        available_types = ', '.join(conf['type'] for conf in ENTITY_CONFIGS)
        click.echo(f"Invalid entity type. Available types: {available_types}")
        return False

    click.echo(f"Creating {entity_type} '{name}'...")
    api = CDPAPI(get_token())
    result = api.create_entity(entity_type, name, config['endpoint'])
    click.echo(json.dumps(result, indent=2))
    return True

def create_all_entities_of_type(entity_type):
    """Core function to create all entities of a specific type"""
    config = get_entity_config(entity_type)
    if not config:
        available_types = ', '.join(conf['type'] for conf in ENTITY_CONFIGS)
        click.echo(f"Invalid entity type. Available types: {available_types}")
        return False

    api = CDPAPI(get_token())
    config_loader = ConfigLoader()
    entity_names = config_loader.get_all_entity_names(entity_type)
    
    if not entity_names:
        click.echo(f"No {entity_type} defined in config.")
        return False

    click.echo(f"\nCreating {len(entity_names)} {entity_type}...")
    for entity_name in entity_names:
        click.echo(f"\nCreating {entity_type} {entity_name}...")
        result = api.create_entity(entity_type, entity_name, config['endpoint'])
        click.echo(json.dumps(result, indent=2))
    return True

def setup_all_entities(interactive=False):
    """Core function to set up all entities"""
    api = CDPAPI(get_token())
    config_loader = ConfigLoader()
    
    for config in ENTITY_CONFIGS:
        entity_type = config['type']
        entity_names = config_loader.get_all_entity_names(entity_type)
        
        if not entity_names:
            click.echo(f"\nNo {entity_type} defined in config, skipping...")
            continue
        
        click.echo(f"\nCreating {len(entity_names)} {entity_type}...")
        
        for entity_name in entity_names:
            click.echo(f"\nCreating {entity_type} {entity_name}...")
            result = api.create_entity(entity_type, entity_name, config['endpoint'])
            click.echo(json.dumps(result, indent=2))
            
            if interactive and not click.confirm("\nContinue with next entity?", default=True):
                click.echo("\nSetup interrupted by user.")
                return False
    
    click.echo("\nAll entities have been created!")
    return True

def list_entity_types():
    """Core function to list entity types"""
    click.echo("\nAvailable entity types in creation order:")
    for config in ENTITY_CONFIGS:
        click.echo(f"\n{config['type']}:")
        click.echo(f"   Description: {config['description']}")
        click.echo(f"   API Endpoint: {config['endpoint']}")

# Interactive mode functions that use core functions
def interactive_menu():
    """Display interactive menu and handle user choices"""
    while True:
        click.clear()
        click.echo("=== CDP Automation Tool ===")
        click.echo("\nAvailable Actions:")
        click.echo("1. Create single entity")
        click.echo("2. Create all entities of a type")
        click.echo("3. Setup everything")
        click.echo("4. List available entity types")
        click.echo("5. Exit")
        
        choice = click.prompt("\nSelect an option", type=int, default=1)
        
        if choice == 1:
            create_single_entity_menu()
        elif choice == 2:
            create_all_entities_menu()
        elif choice == 3:
            if click.confirm("\nThis will create all entities defined in your config. Continue?"):
                setup_all_entities(interactive=True)
            click.pause()
        elif choice == 4:
            list_entity_types()
            click.pause()
        elif choice == 5:
            click.echo("\nGoodbye!")
            break
        else:
            click.echo("\nInvalid choice. Please try again.")
            click.pause()

def create_single_entity_menu():
    """Interactive menu for creating a single entity"""
    click.clear()
    click.echo("=== Create Single Entity ===\n")
    
    # Display available entity types
    click.echo("Available entity types:")
    for idx, config in enumerate(ENTITY_CONFIGS, 1):
        click.echo(f"{idx}. {config['type']} - {config['description']}")
    
    # Get entity type choice
    type_choice = click.prompt("\nSelect entity type (number)", type=int, default=1)
    if not 1 <= type_choice <= len(ENTITY_CONFIGS):
        click.echo("Invalid choice!")
        click.pause()
        return
    
    entity_type = ENTITY_CONFIGS[type_choice-1]['type']
    
    # Get available entities of selected type from config
    config_loader = ConfigLoader()
    available_entities = config_loader.get_all_entity_names(entity_type)
    
    if not available_entities:
        click.echo(f"\nNo {entity_type} defined in override_config.yaml!")
        click.pause()
        return
    
    # Display available entities
    click.echo(f"\nAvailable {entity_type}:")
    for idx, entity_name in enumerate(available_entities, 1):
        click.echo(f"{idx}. {entity_name}")
    
    # Get entity choice
    entity_choice = click.prompt("\nSelect entity (number)", type=int, default=1)
    if not 1 <= entity_choice <= len(available_entities):
        click.echo("Invalid choice!")
        click.pause()
        return
    
    name = available_entities[entity_choice-1]
    
    if click.confirm(f"\nCreate {entity_type} '{name}'?"):
        create_single_entity(entity_type, name)
        click.pause()

def create_all_entities_menu():
    """Interactive menu for creating all entities of a type"""
    click.clear()
    click.echo("=== Create All Entities of Type ===\n")
    
    # Display available entity types
    click.echo("Available entity types:")
    for idx, config in enumerate(ENTITY_CONFIGS, 1):
        click.echo(f"{idx}. {config['type']} - {config['description']}")
    
    # Get entity type choice
    type_choice = click.prompt("\nSelect entity type (number)", type=int, default=1)
    if not 1 <= type_choice <= len(ENTITY_CONFIGS):
        click.echo("Invalid choice!")
        click.pause()
        return
    
    entity_type = ENTITY_CONFIGS[type_choice-1]['type']
    
    if click.confirm(f"\nCreate all {entity_type} defined in config?"):
        create_all_entities_of_type(entity_type)
        click.pause()

# CLI commands that use core functions
@click.group()
def cli():
    """CDP Automation Tool"""
    pass

@cli.command()
def interactive():
    """Run the tool in interactive mode"""
    interactive_menu()

@cli.command()
@click.argument('entity_type')
@click.option('--name', help='Specific entity name to create')
@click.option('--all', 'create_all', is_flag=True, help='Create all entities of this type')
def create(entity_type, name, create_all):
    """Create CDP entities (targets, activations, etc.)"""
    if create_all:
        create_all_entities_of_type(entity_type)
    elif name:
        create_single_entity(entity_type, name)
    else:
        click.echo("Please specify either --name or --all")

@cli.command()
def setup_all():
    """Create all entities defined in config"""
    setup_all_entities(interactive=False)

@cli.command()
def list_types():
    """List all available entity types and their descriptions"""
    list_entity_types()

if __name__ == '__main__':
    if len(sys.argv) > 1:
        cli()
    else:
        interactive_menu()