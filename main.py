"""
main.py — CDP Automation Tool

Two modes:
  1. Legacy interactive menu (original cdp_automation behaviour)
  2. NEW: `provision` command — multi-org, phase-based, resumable setup
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import click
import questionary
from rich.console import Console
from rich.table import Table

from utils.api import CDPAPI
from utils.auth import get_token
from utils.config_loader import ConfigLoader
from utils.org_picker import pick_orgs, get_token_for_org
from utils.state import StateStore
from utils.runner import Runner
from phases import all_phases

console = Console()

# ─── Legacy entity configs ────────────────────────────────────────────────────

ENTITY_CONFIGS = [
    {"type": "segments",    "endpoint": "segments",                  "description": "Segments for data export"},
    {"type": "connectors",  "endpoint": "connections?connectorType", "description": "Connectors"},
    {"type": "targets",     "endpoint": "activation-targets",        "description": "Activation targets"},
    {"type": "activations", "endpoint": "activations",               "description": "Data activations"},
]


def get_entity_config(entity_type):
    for config in ENTITY_CONFIGS:
        if config["type"] == entity_type:
            return config
    return None


# ─── Legacy core functions ────────────────────────────────────────────────────

def create_single_entity(entity_type, name):
    config = get_entity_config(entity_type)
    if not config:
        click.echo(f"Invalid entity type. Available: {', '.join(c['type'] for c in ENTITY_CONFIGS)}")
        return False
    click.echo(f"Creating {entity_type} '{name}'...")
    api = CDPAPI(get_token())
    result = api.create_entity(entity_type, name, config["endpoint"])
    click.echo(json.dumps(result, indent=2))
    return True


def create_all_entities_of_type(entity_type):
    config = get_entity_config(entity_type)
    if not config:
        click.echo(f"Invalid entity type. Available: {', '.join(c['type'] for c in ENTITY_CONFIGS)}")
        return False
    api = CDPAPI(get_token())
    loader = ConfigLoader()
    names = loader.get_all_entity_names(entity_type)
    if not names:
        click.echo(f"No {entity_type} defined in config.")
        return False
    click.echo(f"\nCreating {len(names)} {entity_type}...")
    for name in names:
        click.echo(f"\nCreating {entity_type} {name}...")
        result = api.create_entity(entity_type, name, config["endpoint"])
        click.echo(json.dumps(result, indent=2))
    return True


def setup_all_entities(interactive=False):
    api = CDPAPI(get_token())
    loader = ConfigLoader()
    for config in ENTITY_CONFIGS:
        entity_type = config["type"]
        names = loader.get_all_entity_names(entity_type)
        if not names:
            click.echo(f"\nNo {entity_type} defined in config, skipping...")
            continue
        click.echo(f"\nCreating {len(names)} {entity_type}...")
        for name in names:
            click.echo(f"\nCreating {entity_type} {name}...")
            result = api.create_entity(entity_type, name, config["endpoint"])
            click.echo(json.dumps(result, indent=2))
            if interactive and not click.confirm("\nContinue with next entity?", default=True):
                click.echo("\nSetup interrupted.")
                return False
    click.echo("\nAll entities created!")
    return True


def list_entity_types():
    click.echo("\nAvailable entity types (creation order):")
    for config in ENTITY_CONFIGS:
        click.echo(f"\n{config['type']}:")
        click.echo(f"   Description: {config['description']}")
        click.echo(f"   API Endpoint: {config['endpoint']}")


# ─── Legacy interactive menu ──────────────────────────────────────────────────

def interactive_menu():
    while True:
        click.clear()
        click.echo("=== CDP Automation Tool ===")
        click.echo("\nAvailable Actions:")
        click.echo("1. Create single entity")
        click.echo("2. Create all entities of a type")
        click.echo("3. Setup everything (legacy)")
        click.echo("4. List available entity types")
        click.echo("5. Provision orgs end-to-end (NEW)")
        click.echo("6. Exit")

        choice = click.prompt("\nSelect an option", type=int, default=1)

        if choice == 1:
            _create_single_entity_menu()
        elif choice == 2:
            _create_all_entities_menu()
        elif choice == 3:
            if click.confirm("\nThis will create all entities defined in your config. Continue?"):
                setup_all_entities(interactive=True)
            click.pause()
        elif choice == 4:
            list_entity_types()
            click.pause()
        elif choice == 5:
            _run_provision(
                state_dir=Path(".cdp-setup"),
                dry_run=False,
                force_phase=[],
                yes=False,
                verbose=False,
            )
        elif choice == 6:
            click.echo("\nGoodbye!")
            break
        else:
            click.echo("\nInvalid choice.")
            click.pause()


def _create_single_entity_menu():
    click.clear()
    click.echo("=== Create Single Entity ===\n")
    click.echo("Available entity types:")
    for idx, config in enumerate(ENTITY_CONFIGS, 1):
        click.echo(f"{idx}. {config['type']} - {config['description']}")
    type_choice = click.prompt("\nSelect entity type (number)", type=int, default=1)
    if not 1 <= type_choice <= len(ENTITY_CONFIGS):
        click.echo("Invalid choice!")
        click.pause()
        return
    entity_type = ENTITY_CONFIGS[type_choice - 1]["type"]
    loader = ConfigLoader()
    available = loader.get_all_entity_names(entity_type)
    if not available:
        click.echo(f"\nNo {entity_type} defined in override_config.yaml!")
        click.pause()
        return
    click.echo(f"\nAvailable {entity_type}:")
    for idx, name in enumerate(available, 1):
        click.echo(f"{idx}. {name}")
    entity_choice = click.prompt("\nSelect entity (number)", type=int, default=1)
    if not 1 <= entity_choice <= len(available):
        click.echo("Invalid choice!")
        click.pause()
        return
    name = available[entity_choice - 1]
    if click.confirm(f"\nCreate {entity_type} '{name}'?"):
        create_single_entity(entity_type, name)
        click.pause()


def _create_all_entities_menu():
    click.clear()
    click.echo("=== Create All Entities of Type ===\n")
    click.echo("Available entity types:")
    for idx, config in enumerate(ENTITY_CONFIGS, 1):
        click.echo(f"{idx}. {config['type']} - {config['description']}")
    type_choice = click.prompt("\nSelect entity type (number)", type=int, default=1)
    if not 1 <= type_choice <= len(ENTITY_CONFIGS):
        click.echo("Invalid choice!")
        click.pause()
        return
    entity_type = ENTITY_CONFIGS[type_choice - 1]["type"]
    if click.confirm(f"\nCreate all {entity_type} defined in config?"):
        create_all_entities_of_type(entity_type)
        click.pause()


# ─── NEW: Provision command ───────────────────────────────────────────────────

def _run_provision(state_dir: Path, dry_run: bool, force_phase: list, yes: bool, verbose: bool):
    """Core provision logic — shared by CLI command and interactive menu."""
    state_dir = Path(state_dir)
    store = StateStore(state_dir)
    phases = all_phases()

    if store.exists():
        console.print(f"\n[yellow]Resuming previous run from {state_dir}/state.json[/yellow]")
        store.load()
        orgs_to_run = list(store.state.orgs.values())
        dry_run = store.state.dry_run

        table = Table(show_header=True, header_style="bold cyan", title="Resuming provisioning")
        table.add_column("Username")
        table.add_column("Instance URL")
        table.add_column("Progress")
        for org in orgs_to_run:
            done = sum(1 for r in org.phases.values() if r.status.value == "done")
            table.add_row(org.username, org.instance_url, f"{done}/{len(phases)} phases done")
        console.print(table)
    else:
        # Fresh run — pick orgs interactively
        orgs_selected = pick_orgs()
        if not orgs_selected:
            console.print("[yellow]No orgs selected. Exiting.[/yellow]")
            return

        store.init(dry_run=dry_run)
        for o in orgs_selected:
            store.add_org(
                username=o.username,
                instance_url=o.instance_url,
                alias=o.alias,
                org_id=o.org_id,
            )
        orgs_to_run = list(store.state.orgs.values())

        # Show plan
        phase_table = Table(show_header=True, header_style="bold cyan", title="Provisioning plan")
        phase_table.add_column("#", width=3, justify="right")
        phase_table.add_column("Phase")
        phase_table.add_column("Description")
        for i, p in enumerate(phases):
            phase_table.add_row(str(i + 1), p.name, p.description)
        console.print(phase_table)

        org_table = Table(show_header=True, header_style="bold cyan", title="Target orgs")
        org_table.add_column("Username")
        org_table.add_column("Instance URL")
        for o in orgs_to_run:
            org_table.add_row(o.username, o.instance_url)
        console.print(org_table)

        if dry_run:
            console.print("[yellow]DRY RUN MODE — no changes will be made[/yellow]")

        if not yes:
            if not questionary.confirm("Proceed with provisioning?", default=True).ask():
                console.print("[yellow]Aborted.[/yellow]")
                return

    runner = Runner(store)
    force_set = set(force_phase) if force_phase else None
    results = {}

    for org in orgs_to_run:
        try:
            token_info = get_token_for_org(org)
        except Exception as e:
            console.print(f"[red]Could not get token for {org.username}: {e}[/red]")
            results[org.username] = False
            continue

        ok = runner.run_for_org(
            phases=phases,
            org=org,
            token_info=token_info,
            dry_run=dry_run,
            force_phases=force_set,
        )
        results[org.username] = ok

    # Final summary
    console.print()
    summary = Table(show_header=True, header_style="bold", title="Provisioning Summary")
    summary.add_column("Org")
    summary.add_column("Result")
    for username, ok in results.items():
        summary.add_row(username, "[green]✓ Complete[/green]" if ok else "[red]✗ Failed[/red]")
    console.print(summary)

    if all(results.values()):
        console.print("\n[green]✓ All orgs provisioned successfully![/green]")
    else:
        console.print("\n[yellow]Some orgs failed. Re-run to resume from failed phase.[/yellow]")


# ─── CLI entry points ─────────────────────────────────────────────────────────

@click.group()
def cli():
    """CDP Automation Tool — Data Cloud + Clean Room org provisioning."""
    pass


@cli.command()
def interactive():
    """Run the tool in interactive mode (legacy menu)."""
    interactive_menu()


@cli.command()
@click.argument("entity_type")
@click.option("--name", help="Specific entity name to create")
@click.option("--all", "create_all", is_flag=True, help="Create all entities of this type")
def create(entity_type, name, create_all):
    """Create CDP entities (targets, activations, segments etc.)"""
    if create_all:
        create_all_entities_of_type(entity_type)
    elif name:
        create_single_entity(entity_type, name)
    else:
        click.echo("Please specify either --name or --all")


@cli.command()
def setup_all():
    """Create all entities defined in config (legacy)."""
    setup_all_entities(interactive=False)


@cli.command()
def list_types():
    """List all available entity types and their descriptions."""
    list_entity_types()


@cli.command()
@click.option("--state-dir", default=".cdp-setup", show_default=True,
              help="Directory for run state (enables resume on failure)")
@click.option("--dry-run", is_flag=True,
              help="Show what would happen without making any changes")
@click.option("--force-phase", multiple=True,
              help="Re-run a specific phase even if already done")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
@click.option("--verbose", "-v", is_flag=True)
def provision(state_dir, dry_run, force_phase, yes, verbose):
    """
    End-to-end multi-org Data Cloud + Clean Room provisioning.

    \b
    Features:
      - Pick multiple orgs (shows real usernames + URLs, not aliases)
      - Add a new org via browser login
      - Runs 8 phases in order:
          auth → preflight → datastream → dmo →
          segment → target → activation → dcr_install
      - Automatically resumes from failed phase on re-run
      - Dry-run mode to preview without making changes

    \b
    Examples:
      python main.py provision
      python main.py provision --dry-run
      python main.py provision --force-phase segment
      python main.py provision --yes
    """
    _run_provision(
        state_dir=Path(state_dir),
        dry_run=dry_run,
        force_phase=list(force_phase),
        yes=yes,
        verbose=verbose,
    )


@cli.command()
@click.option("--state-dir", default=".cdp-setup", show_default=True)
def status(state_dir):
    """Show status of a previous or in-progress provision run."""
    store = StateStore(Path(state_dir))
    if not store.exists():
        console.print(f"[yellow]No state file found at {state_dir}/state.json[/yellow]")
        raise SystemExit(1)

    store.load()
    s = store.state

    for username, org in s.orgs.items():
        table = Table(
            title=f"{org.username}  ({org.instance_url})",
            show_header=True,
            header_style="bold cyan",
        )
        table.add_column("Phase")
        table.add_column("Status")
        table.add_column("Attempts", justify="right")
        table.add_column("Error")
        for name, rec in org.phases.items():
            table.add_row(
                name,
                rec.status.value,
                str(rec.attempt),
                (rec.last_error or "")[:60],
            )
        console.print(table)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        cli()
    else:
        interactive_menu()
