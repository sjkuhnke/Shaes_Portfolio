from django.db import models


class TrainerBattle(models.Model):
    trainer_name = models.CharField(max_length=200)
    player_name = models.CharField(max_length=200, default='Anonymous')
    game_version = models.CharField(max_length=50, default='Unknown')
    team_hash = models.CharField(max_length=64, db_index=True)  # SHA256 hash of team composition
    battle_fingerprint = models.CharField(max_length=64, unique=True, db_index=True)  # Unique identifier
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['battle_fingerprint']),
            models.Index(fields=['trainer_name', 'player_name']),
        ]


class BattlePokemon(models.Model):
    battle = models.ForeignKey(TrainerBattle, on_delete=models.CASCADE, related_name='team')
    position = models.IntegerField()  # 0-5 for team order

    # Basic info
    pokemon_id = models.IntegerField()
    name = models.CharField(max_length=100)
    nickname = models.CharField(max_length=100)
    level = models.IntegerField()
    shiny = models.BooleanField(default=False)

    # Stats
    stats = models.JSONField()  # Store as array
    ivs = models.JSONField()  # Store as array
    nature = models.CharField(max_length=20)
    current_hp = models.IntegerField()
    max_hp = models.IntegerField()

    # Types
    type1 = models.CharField(max_length=20)
    type2 = models.CharField(max_length=20, null=True, blank=True)

    # Ability
    ability = models.CharField(max_length=50)
    ability_slot = models.IntegerField()

    # Moves
    moveset = models.JSONField()  # Array of move objects

    # Item
    item = models.CharField(max_length=50, null=True, blank=True)
    ball = models.CharField(max_length=20, null=True, blank=True)

    # Status
    status = models.CharField(max_length=20)
    fainted = models.BooleanField(default=False)

    # Extra
    happiness = models.IntegerField()
    met_at = models.CharField(max_length=100, null=True, blank=True)
