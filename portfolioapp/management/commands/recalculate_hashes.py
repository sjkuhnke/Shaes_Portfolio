# Django Management Command to Recalculate Hashes
#
# File location: portfolioapp/management/commands/recalculate_hashes.py
#
# Create this directory structure if it doesn't exist:
# portfolioapp/
#   management/
#     __init__.py  (empty file)
#     commands/
#       __init__.py  (empty file)
#       recalculate_hashes.py  (this file)

import hashlib
from django.core.management.base import BaseCommand
from portfolioapp.models import TrainerBattle, BattlePokemon


def normalize_move_name_for_hashing(move_name):
    """
    Normalize move names for consistent hashing.
    Strips type suffixes from Hidden Power and Return.
    """
    if move_name.startswith('Hidden Power '):
        return 'Hidden Power'
    if move_name.startswith('Return '):
        return 'Return'
    return move_name


def recalculate_team_hash(battle):
    """
    Recalculate team hash for a battle using Pokemon from database.
    Normalizes Hidden Power and Return move names.
    """
    team_data = []

    # Get all Pokemon for this battle, ordered by their original position
    for pokemon in battle.team.all().order_by('position'):
        # Get moveset from the database (it's stored as JSONB)
        moveset = pokemon.moveset

        # Normalize move names
        if isinstance(moveset, list):
            normalized_moves = [normalize_move_name_for_hashing(move) for move in moveset]
        else:
            normalized_moves = []

        # Build the signature exactly like generate_team_hash does
        team_signature_parts = [
            str(pokemon.pokemon_id),
            str(pokemon.uuid),
            str(pokemon.level),
            pokemon.name,
            pokemon.nickname or '',
            '|'.join(sorted(normalized_moves)),  # Use normalized move names
            pokemon.item or '',
            pokemon.nature,
            str(pokemon.shiny),
            str(pokemon.ability_slot),
        ]
        team_data.append('::'.join(team_signature_parts))

    # Join all Pokemon signatures and hash
    full_signature = '||'.join(team_data)
    return hashlib.sha256(full_signature.encode()).hexdigest()


def recalculate_battle_fingerprint(battle, team_hash):
    """
    Recalculate battle fingerprint using new team hash.
    """
    fingerprint = f"{battle.player_id}::{battle.trainer_name}::{team_hash}::{battle.battle_start_time}"
    return hashlib.sha256(fingerprint.encode()).hexdigest()


class Command(BaseCommand):
    help = 'Recalculate team hashes and battle fingerprints for existing battles'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without actually updating',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        battles = TrainerBattle.objects.all()
        total_battles = battles.count()
        updated_count = 0
        error_count = 0

        self.stdout.write(f'Processing {total_battles} battles...')
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be saved'))

        for battle in battles:
            try:
                # Recalculate hashes
                old_team_hash = battle.team_hash
                old_fingerprint = battle.battle_fingerprint

                new_team_hash = recalculate_team_hash(battle)
                new_fingerprint = recalculate_battle_fingerprint(battle, new_team_hash)

                # Check if anything changed
                if old_team_hash != new_team_hash or old_fingerprint != new_fingerprint:
                    if dry_run:
                        self.stdout.write(
                            f'Would update battle {battle.id} ({battle.trainer_name})'
                        )
                        self.stdout.write(f'  Old hash: {old_team_hash[:16]}...')
                        self.stdout.write(f'  New hash: {new_team_hash[:16]}...')
                    else:
                        battle.team_hash = new_team_hash
                        battle.battle_fingerprint = new_fingerprint
                        battle.save()
                        self.stdout.write(
                            self.style.SUCCESS(f'✓ Updated battle {battle.id} ({battle.trainer_name})')
                        )

                    updated_count += 1

            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(f'✗ Error processing battle {battle.id}: {e}')
                )

        # Summary
        self.stdout.write('')
        self.stdout.write('=' * 60)
        self.stdout.write(f'Total battles processed: {total_battles}')
        self.stdout.write(f'Battles that {"would be " if dry_run else ""}updated: {updated_count}')
        self.stdout.write(f'Battles unchanged: {total_battles - updated_count - error_count}')
        if error_count > 0:
            self.stdout.write(self.style.ERROR(f'Errors: {error_count}'))

        if dry_run:
            self.stdout.write('')
            self.stdout.write(self.style.WARNING('DRY RUN - No changes were saved'))
            self.stdout.write('Run without --dry-run to apply changes')
        else:
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS('✓ Hash recalculation complete!'))