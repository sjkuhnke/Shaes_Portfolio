# portfolioapp/hash_utils.py
# Shared hash calculation logic to avoid duplication

import hashlib


def generate_team_hash(team_data):
    """
    Generate a hash based on the team composition.
    This includes Pokemon IDs, levels, and movesets to uniquely identify a team.

    IMPORTANT: Normalizes Hidden Power and Return move names to ensure
    "Hidden Power Fire" and "Hidden Power" generate the same hash.

    Args:
        team_data: List of Pokemon data dictionaries (from JSON upload)

    Returns:
        SHA256 hash as hexadecimal string
    """
    # Create a deterministic string representation of the team
    team_signature = []

    for pokemon in sorted(team_data, key=lambda p: p['id']):
        # Get and normalize moveset
        moveset = pokemon.get('moveset', [])

        if moveset and isinstance(moveset[0], dict):  # If moveset is list of move objects
            moves = [move['name'] for move in moveset]
        elif moveset:  # If moveset is list of strings
            moves = [move for move in moveset]
        else:
            moves = []

        # Include key identifying features
        signature_parts = [
            str(pokemon['id']),
            str(pokemon['uuid']),
            str(pokemon['level']),
            pokemon['name'],
            pokemon.get('nickname', ''),
            '|'.join(sorted(moves)),  # Use normalized move names
            pokemon.get('item', ''),
            pokemon['nature'],
            str(pokemon.get('shiny', False)),
            str(pokemon['abilitySlot']),
        ]
        team_signature.append('::'.join(signature_parts))

    # Join all Pokemon signatures and hash
    full_signature = '||'.join(team_signature)
    return hashlib.sha256(full_signature.encode()).hexdigest()


def recalculate_team_hash_from_db(battle):
    """
    Recalculate team hash for a battle using Pokemon from database.
    This reconstructs the original team_data format from BattlePokemon objects.

    Args:
        battle: TrainerBattle instance

    Returns:
        SHA256 hash as hexadecimal string (same format as generate_team_hash)
    """
    # Reconstruct team_data in the same format as the JSON upload
    team_data = []

    for pokemon in battle.team.all().order_by('pokemon_id'):  # CRITICAL: Sort by pokemon_id, not position!
        team_data.append({
            'id': pokemon.pokemon_id,
            'uuid': str(pokemon.uuid),
            'level': pokemon.level,
            'name': pokemon.name,
            'nickname': pokemon.nickname or '',
            'moveset': pokemon.moveset,  # This is already a list of strings in the DB
            'item': pokemon.item or '',
            'nature': pokemon.nature,
            'shiny': pokemon.shiny,
            'abilitySlot': pokemon.ability_slot,
        })

    # Now use the SAME function to calculate the hash
    return generate_team_hash(team_data)


def generate_battle_fingerprint(player_id, trainer_name, team_hash, battle_start_time):
    """
    Generate a unique fingerprint for a battle that includes:
    - Player ID
    - Trainer name
    - Team composition hash
    - Battle start time

    Args:
        player_id: Player's ID
        trainer_name: Name of the trainer being fought
        team_hash: Team hash from generate_team_hash
        battle_start_time: Timestamp when battle started

    Returns:
        SHA256 hash as hexadecimal string
    """
    fingerprint = f"{player_id}::{trainer_name}::{team_hash}::{battle_start_time}"
    return hashlib.sha256(fingerprint.encode()).hexdigest()