# Django Management Command to Recalculate Hashes
#
# File location: portfolioapp/management/commands/recalculate_hashes.py

from django.core.management.base import BaseCommand
from portfolioapp.models import TrainerBattle
from portfolioapp.hash_utils import (
    recalculate_team_hash_from_db,
    generate_battle_fingerprint
)


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
                # Recalculate hashes using the SAME logic as the upload
                old_team_hash = battle.team_hash
                old_fingerprint = battle.battle_fingerprint

                new_team_hash = recalculate_team_hash_from_db(battle)
                new_fingerprint = generate_battle_fingerprint(
                    battle.player_id,
                    battle.trainer_name,
                    new_team_hash,
                    battle.battle_start_time
                )

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
                import traceback
                traceback.print_exc()

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