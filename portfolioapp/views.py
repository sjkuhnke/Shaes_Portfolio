import json
import os
import random
import re
from datetime import datetime
from pathlib import Path

import markdown
import requests
import hashlib
from django.core.mail import EmailMessage
from django.http import Http404, JsonResponse
from django.template.loader import render_to_string
from django.conf import settings
from django.shortcuts import render
from django.utils.safestring import mark_safe
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q, Count, Max
from markdown.extensions.nl2br import Nl2BrExtension
from datetime import datetime
from collections import defaultdict, Counter
from django.db import transaction

from portfolioapp.models import TrainerBattle, BattlePokemon


def about(request):
    json_path = os.path.join(settings.BASE_DIR, 'portfolioapp/static', 'data', 'testimonials.json')
    with open(json_path, 'r', encoding='utf-8') as file:
        testimonials = json.load(file)

    return render(request, 'about.html', {'testimonials': testimonials})


def resume(request):
    return render(request, 'resume.html')


def portfolio(request):
    json_path = os.path.join(settings.BASE_DIR, 'portfolioapp/static', 'data', 'projects.json')
    with open(json_path, 'r', encoding='utf-8') as f:
        projects = json.load(f)
    return render(request, 'portfolio.html', {'projects': projects})


def project(request, pk):
    json_path = os.path.join(settings.BASE_DIR, 'portfolioapp/static', 'data', 'projects.json')
    with open(json_path, 'r', encoding='utf-8') as f:
        projects = json.load(f)
    proj = next((p for p in projects if p['id'] == int(pk)), None)
    if not proj:
        raise Http404("Project not found")

    proj = normalize_github_links(proj)

    return render(request, 'project.html', {'project': proj})


def contact(request):
    recaptcha_site_key = settings.GOOGLE_RECAPTCHA_SITE_KEY
    recaptcha_secret_key = settings.GOOGLE_RECAPTCHA_SECRET_KEY

    if request.method == 'POST':
        name = request.POST.get('fullname')
        email = request.POST.get('email')
        company = request.POST.get('company')
        message = request.POST.get('message')
        recaptcha_response = request.POST.get('g-recaptcha-response')

        if not name or not email or not message or not recaptcha_response:
            return render(request, 'contact.html', {
                'error': 'All fields are required.',
                'recaptcha_site_key': recaptcha_site_key
            })

        recaptcha_verify_url = 'https://www.google.com/recaptcha/api/siteverify'
        recaptcha_data = {
            'secret': recaptcha_secret_key,
            'response': recaptcha_response
        }
        recaptcha_result = requests.post(recaptcha_verify_url, data=recaptcha_data)
        recaptcha_result_json = recaptcha_result.json()

        recaptcha_score = recaptcha_result_json.get('score', 0)

        if not recaptcha_result_json.get('success') or recaptcha_score < 0.5:
            return render(request, 'contact.html', {
                'error': 'reCAPTCHA verification failed. Please try again.',
                'recaptcha_site_key': recaptcha_site_key
            })

        email_subject = 'New Contact Submission'
        email_body = render_to_string('contact_email.txt', {
            'name': name,
            'email': email,
            'company': company,
            'message': message,
        })

        email_message = EmailMessage(
            email_subject,
            email_body,
            settings.DEFAULT_FROM_EMAIL,
            ['shaejk29@gmail.com']
        )

        try:
            email_message.send()
            return render(request, 'contact.html', {
                'success': 'Thank you for reaching out! I will get back to you shortly!',
                'recaptcha_site_key': recaptcha_site_key
            })
        except Exception as e:
            return render(request, 'contact.html', {
                'error': f'An error occurred: {str(e)}',
                'recaptcha_site_key': recaptcha_site_key
            })

    return render(request, 'contact.html', {
        'recaptcha_site_key': recaptcha_site_key
    })


def xhenos(request):
    """Main download page for Pokemon Xhenos"""
    versions_path = os.path.join(settings.BASE_DIR, 'content', 'versions', 'versions.json')
    with open(versions_path, 'r', encoding='utf-8') as f:
        version_data = json.load(f)

    latest = version_data['latest'].copy()
    latest.update({
        'download_windows': latest['downloads']['windows'],
        'download_mac': latest['downloads']['mac'],
        'download_jar': latest['downloads']['jar'],
    })

    previous_versions = []
    for version in version_data.get('previous', []):
        version_copy = version.copy()
        version_copy.update({
            'download_windows': version['downloads']['windows'],
            'download_mac': version['downloads']['mac'],
            'download_jar': version['downloads']['jar'],
        })
        previous_versions.append(version_copy)

    context = {
        "latest": latest,
        "previous_versions": previous_versions,
        "categories": {title: icon for title, icon in CATEGORY_ICONS.items()}
    }

    return render(request, "xhenos_downloads.html", context)


def changelog_page(request, version):
    """Full view for changelog"""
    try:
        changelog_html, toc_html = read_changelog(version)
        if changelog_html:
            context = {
                'content': mark_safe(changelog_html),
                'toc': mark_safe(toc_html) if toc_html else None,
                'title': f'Changelog - PokÃ©mon Xhenos v{version}',
                'back_url': '/xhenos/',
                'back_text': 'Back to Downloads'
            }
            return render(request, 'markdown_page.html', context)
        else:
            raise Http404("Changelog not found")
    except Exception as e:
        print(e)
        raise Http404("Error loading changelog")


CATEGORY_ICONS = {
    "New Features": '<i class="fa-solid fa-star"></i>',
    "Feature Updates": '<i class="fa-solid fa-wrench"></i>',
    "Bug Fixes": '<i class="fa-solid fa-bug"></i>',
    "Move Changes": '<i class="fa-solid fa-bolt"></i>',
    "Pokemon Changes": '<i class="fa-solid fa-dragon"></i>',
    "Trainer Changes": '<i class="fa-solid fa-user"></i>',
}


def ai_guide(request):
    """Serve the AI trainer guide"""
    try:
        guide_path = os.path.join(settings.BASE_DIR, 'content', 'guides', 'comprehensive_trainer_ai_guide.md')

        with open(guide_path, 'r', encoding='utf-8') as f:
            content = f.read()

        html, toc_html = process_markdown_content(content)

        context = {
            'content': mark_safe(html),
            'toc': mark_safe(toc_html) if toc_html else None,
            'title': 'Trainer AI Guide - PokÃ©mon Xhenos',
            'back_url': '/xhenos/',
            'back_text': 'Back to Downloads'
        }

        return render(request, 'markdown_page.html', context)

    except FileNotFoundError:
        raise Http404("No AI guide found")
    except Exception as e:
        print(e)
        raise Http404("Error loading AI Guide")


def generate_team_hash(team_data):
    """
    Generate a hash based on the team composition.
    This includes Pokemon IDs, levels, and movesets to uniquely identify a team.
    """
    # Create a deterministic string representation of the team
    team_signature = []
    for pokemon in sorted(team_data, key=lambda p: p['id']):
        # Include key identifying features
        signature_parts = [
            str(pokemon['id']),
            str(pokemon['uuid']),
            str(pokemon['level']),
            pokemon['name'],
            pokemon.get('nickname', ''),
            '|'.join(sorted([move['name'] for move in pokemon.get('moveset', [])])),
            pokemon.get('item', ''),
            pokemon['nature'],
            str(pokemon.get('shiny', False)),
            str(pokemon['abilitySlot']),
        ]
        team_signature.append('::'.join(signature_parts))

    # Join all Pokemon signatures and hash
    full_signature = '||'.join(team_signature)
    return hashlib.sha256(full_signature.encode()).hexdigest()


def generate_battle_fingerprint(player_id, trainer_name, team_hash, battle_start_time):
    """
    Generate a unique fingerprint for a battle that includes:
    - Player name (to allow different players to have same trainer/team)
    - Trainer name
    - Team composition hash
    """
    fingerprint = f"{player_id}::{trainer_name}::{team_hash}::{battle_start_time}"
    return hashlib.sha256(fingerprint.encode()).hexdigest()


@csrf_exempt
def upload_battle_history(request):
    if request.method == 'POST':
        try:
            # Handle file upload
            if 'battle_history' in request.FILES:
                file = request.FILES['battle_history']
                data = json.loads(file.read().decode('utf-8'))
            else:
                data = json.loads(request.body)

            player_name = data.get('player_name', 'Anonymous')
            player_id = data.get('player_id', 0)

            battles_uploaded = 0
            battles_skipped = 0

            # Process each battle
            for battle_data in data['battles']:
                # Generate team hash and battle fingerprint
                team_hash = generate_team_hash(battle_data['team'])
                battle_fingerprint = generate_battle_fingerprint(
                    player_id,
                    battle_data['trainer'],
                    team_hash,
                    battle_data.get('battleStartTime')
                )

                # Check if this exact battle already exists
                if TrainerBattle.objects.filter(battle_fingerprint=battle_fingerprint).exists():
                    battles_skipped += 1
                    continue

                # Use transaction to ensure atomicity
                with transaction.atomic():
                    battle = TrainerBattle.objects.create(
                        trainer_name=battle_data['trainer'],
                        player_name=player_name,
                        player_id=player_id,
                        game_version=battle_data['gameVersion'],
                        difficulty=battle_data['difficulty'],
                        team_hash=team_hash,
                        battle_fingerprint=battle_fingerprint,
                        victory=battle_data.get('victory', True),
                        battle_start_time=battle_data.get('battleStartTime'),
                        battle_end_time=battle_data.get('battleEndTime'),
                        lead=battle_data['lead']
                    )

                    # Add each Pokemon
                    for idx, pokemon_data in enumerate(battle_data['team']):
                        moveset_data = pokemon_data.get('moveset', [])
                        moveset = [move['name'] for move in pokemon_data.get('moveset', [])]

                        BattlePokemon.objects.create(
                            battle=battle,
                            position=idx,
                            pokemon_id=pokemon_data['id'],
                            uuid=pokemon_data['uuid'],
                            name=pokemon_data['name'],
                            nickname=pokemon_data.get('nickname', pokemon_data['name']),
                            level=pokemon_data['level'],
                            shiny=pokemon_data.get('shiny', False),
                            base=pokemon_data['base'],
                            stats=pokemon_data.get('stats', []),
                            ivs=pokemon_data.get('ivs', []),
                            nature=pokemon_data['nature'],
                            current_hp=pokemon_data['currentHP'],
                            max_hp=pokemon_data['maxHP'],
                            type1=pokemon_data['type1'],
                            type2=pokemon_data.get('type2'),
                            ability=pokemon_data['ability'],
                            ability_slot=pokemon_data['abilitySlot'],
                            moveset=moveset,
                            moveset_details=moveset_data,
                            item=pokemon_data.get('item'),
                            ball=pokemon_data.get('ball'),
                            status=pokemon_data.get('status', 'Healthy'),
                            fainted=pokemon_data.get('fainted', False),
                            happiness=pokemon_data.get('happiness', 0),
                            met_at=pokemon_data.get('metAt'),

                            kills=pokemon_data.get('kills', 0),
                            kill_list=pokemon_data.get('killList'),
                            died=pokemon_data.get('died', False),
                            killer=pokemon_data.get('killer'),
                            evolved=pokemon_data.get('evolved', False),
                            evo_id=pokemon_data.get('evoID'),
                            evo_name=pokemon_data.get('evoName'),
                            switch_ins=pokemon_data.get('switchIns'),
                            turns=pokemon_data.get('turns'),

                            damage_dealt=pokemon_data.get('damageDealt', 0),
                            damage_taken=pokemon_data.get('damageTaken', 0),
                            pp_used=pokemon_data.get('ppUsed'),
                        )

                    battles_uploaded += 1

            return JsonResponse({
                'status': 'success',
                'battles_uploaded': battles_uploaded,
                'battles_skipped': battles_skipped,
                'message': f'Uploaded {battles_uploaded} new battle(s), skipped {battles_skipped} duplicate(s)'
            })

        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    # Return error for non-POST requests
    return JsonResponse({'status': 'error', 'message': 'Only POST requests allowed'}, status=405)


def trainer_database(request):
    return render(request, 'xhenos_trainers_page.html')


def trainer_lookup(request, trainer_name):
    battles = TrainerBattle.objects.filter(
        trainer_name=trainer_name
    ).prefetch_related('team').order_by('-created_at')[:50]

    pokemon_usage = {}

    # Calculate participation stats for each battle
    total_battles = battles.count()
    wins = 0
    battles_with_deaths = 0
    battles_data = []
    for battle in battles:
        pokemon_list = list(battle.team.all())

        if battle.victory:
            wins += 1

        if any(p.died for p in pokemon_list):
            battles_with_deaths += 1

        # Calculate total turns for this battle
        total_turns = sum(p.turns for p in pokemon_list if p.turns is not None)

        # Find MVP using comprehensive scoring
        # MVP Score = (kills * 3) + (damage_dealt * 0.02) + (turns * 0.5) + (switch_ins * 0.25) + (survived bonus: 2) - (died penalty: 3)
        mvp_pokemon = None
        max_mvp_score = 0

        # Find best pivot (most switch-ins with meaningful activity)
        pivot_pokemon = None
        max_switches = 0

        # Find tank (most damage taken while surviving)
        tank_pokemon = None
        max_damage_taken = 0

        # Find damage dealer (most damage dealt)
        damage_dealer = None
        max_damage_dealt = 0

        for pokemon in pokemon_list:
            if pokemon.pokemon_id not in pokemon_usage:
                pokemon_usage[pokemon.pokemon_id] = {
                    "id": pokemon.pokemon_id,
                    "name": pokemon.name,
                    "count": 0,
                }

            pokemon_usage[pokemon.pokemon_id]["count"] += 1

            # Calculate MVP score
            mvp_score = 0
            if pokemon.kills is not None:
                mvp_score += pokemon.kills * 3
            if pokemon.damage_dealt is not None:
                mvp_score += pokemon.damage_dealt * 0.02
            if pokemon.turns is not None:
                mvp_score += pokemon.turns * 0.5
            if pokemon.switch_ins is not None:
                mvp_score += pokemon.switch_ins * 0.25

            # Bonus for survival
            if not pokemon.died:
                mvp_score += 2
            else:
                mvp_score -= 3  # Penalty for dying

            if mvp_score > max_mvp_score:
                max_mvp_score = mvp_score
                mvp_pokemon = pokemon

            # Check for pivot (3+ switch-ins)
            if pokemon.switch_ins is not None and pokemon.switch_ins >= max_switches and pokemon.switch_ins >= 3:
                max_switches = pokemon.switch_ins
                pivot_pokemon = pokemon

            # Check for tank (most damage taken, but didn't die and participated)
            if (pokemon.damage_taken is not None and pokemon.damage_taken > max_damage_taken
                    and not pokemon.died and pokemon.turns is not None and pokemon.turns > 0):
                max_damage_taken = pokemon.damage_taken
                tank_pokemon = pokemon

            # Check for damage dealer
            if pokemon.damage_dealt is not None and pokemon.damage_dealt > max_damage_dealt:
                max_damage_dealt = pokemon.damage_dealt
                damage_dealer = pokemon

        # Annotate each pokemon with badges and stats
        for pokemon in pokemon_list:
            pokemon.is_mvp = (pokemon == mvp_pokemon and max_mvp_score >= 5)
            pokemon.is_pivot = (pokemon == pivot_pokemon and max_switches >= 3)
            pokemon.is_tank = (pokemon == tank_pokemon and max_damage_taken >= 100)  # At least 100% damage taken
            pokemon.is_damage_dealer = (
                        pokemon == damage_dealer and max_damage_dealt >= 200)  # At least 200% damage dealt
            pokemon.is_benched = (pokemon.turns or 0) == 0 and (pokemon.switch_ins or 0) == 0
            pokemon.is_lead = (pokemon.position == battle.lead)
            pokemon.turn_percentage = round((pokemon.turns / total_turns * 100),
                                            1) if total_turns > 0 and pokemon.turns is not None else 0
            pokemon.total_turns = total_turns

        battles_data.append({
            'battle': battle,
            'total_turns': total_turns
        })

    win_percentage = round((wins / total_battles) * 100, 1) if total_battles else 0
    death_percentage = round((battles_with_deaths / total_battles) * 100, 1) if total_battles else 0

    TOP_N = 15

    TOP_N = 15

    most_used_pokemon = sorted(
        pokemon_usage.values(),
        key=lambda p: p["count"],
        reverse=True
    )[:TOP_N]

    max_pokemon_usage = max(
        (p["count"] for p in most_used_pokemon),
        default=1
    )

    return render(request, 'xhenos_trainer.html', {
        'trainer_name': trainer_name,
        'battles': battles,
        'battles_data': battles_data,
        'most_used_pokemon': most_used_pokemon,
        'max_pokemon_usage': max_pokemon_usage,
        'win_percentage': win_percentage,
        'death_percentage': death_percentage
    })


def trainer_autocomplete(request):
    """API endpoint for trainer and player name autocomplete"""
    query = request.GET.get('q', '').strip()
    show_top = request.GET.get('top', None)

    # Return empty if no query and no show_top
    if not query and not show_top:
        return JsonResponse({'results': []})

    # Determine limits based on whether we're searching or showing top
    if show_top and not query:
        trainer_limit = player_limit = int(show_top)
        final_limit = int(show_top)
    else:
        trainer_limit = player_limit = 15
        final_limit = 20

    # Build queries
    trainer_filter = Q(trainer_name__icontains=query) if query else Q()
    player_filter = Q(player_name__icontains=query) if query else Q()

    # Fetch trainers
    trainers = TrainerBattle.objects.filter(trainer_filter).values('trainer_name').annotate(
        battle_count=Count('id')
    ).order_by('-battle_count', 'trainer_name')[:trainer_limit]

    # Fetch players
    players = TrainerBattle.objects.filter(player_filter).values('player_name').annotate(
        battle_count=Count('id'),
        trainer_count=Count('trainer_name', distinct=True)
    ).order_by('-battle_count', 'player_name')[:player_limit]

    # Combine results
    results = []

    for trainer in trainers:
        results.append({
            'type': 'trainer',
            'name': trainer['trainer_name'],
            'battle_count': trainer['battle_count']
        })

    for player in players:
        results.append({
            'type': 'player',
            'name': player['player_name'],
            'battle_count': player['battle_count'],
            'trainer_count': player['trainer_count']
        })

    # Sort and limit
    results.sort(key=lambda x: x['battle_count'], reverse=True)
    results = results[:final_limit]

    return JsonResponse({'results': results})


def player_lookup(request, player_name):
    """Show all trainers battled by a specific player"""
    sort = request.GET.get('sort', 'date')

    trainers = TrainerBattle.objects.filter(
        player_name=player_name
    ).prefetch_related('team').values('trainer_name').annotate(
        battle_count=Count('id'),
        last_battle_timestamp=Max('battle_start_time')
    ).order_by('-battle_count', 'trainer_name')

    # Calculate stats
    total_battles = 0
    last_battle = None
    last_battle_timestamp = 0

    # Get all battles for this player to calculate win% and death%
    all_battles = TrainerBattle.objects.filter(player_name=player_name).prefetch_related('team')
    total_wins = all_battles.filter(victory=True).count()

    # Count battles where at least one Pokemon died
    total_deaths = 0
    for battle in all_battles:
        if battle.team.filter(died=True).exists():
            total_deaths += 1

    total_battle_count = all_battles.count()
    win_percentage = round((total_wins / total_battle_count * 100), 1) if total_battle_count > 0 else 0
    death_percentage = round((total_deaths / total_battle_count * 100), 1) if total_battle_count > 0 else 0

    # Track Pokemon by UUID for kill stats
    pokemon_kills = defaultdict(lambda: {'kills': 0, 'evolutions': [], 'base': None})

    # Track Pokemon usage by base species
    pokemon_usage = defaultdict(int)

    # Track deaths by base species
    pokemon_deaths = defaultdict(int)

    # Track activity by base species (turns + switch-ins for a combined metric)
    pokemon_activity = defaultdict(lambda: {'turns': 0, 'switch_ins': 0, 'battles': 0})

    # NEW: Track move usage across all battles
    move_usage = defaultdict(int)

    # NEW: Track damage dealt by individual Pokemon (by UUID)
    pokemon_damage_dealt = defaultdict(lambda: {'damage': 0, 'evolutions': [], 'base': None})

    # NEW: Track damage taken by individual Pokemon (by UUID) - only for Pokemon that participated
    pokemon_damage_taken = defaultdict(lambda: {'damage': 0, 'evolutions': [], 'base': None, 'participated': False})

    pokemon_latest_nickname = {}
    pokemon_latest_timestamp = {}

    for battle in all_battles:
        battle_time = battle.battle_start_time or 0

        for pokemon in battle.team.all():
            uuid = str(pokemon.uuid)

            if pokemon.nickname and pokemon.nickname.strip():
                if (
                    uuid not in pokemon_latest_timestamp or
                    battle_time > pokemon_latest_timestamp[uuid]
                ):
                    pokemon_latest_timestamp[uuid] = battle_time
                    pokemon_latest_nickname[uuid] = pokemon.nickname.strip()

            # Track kills by UUID (specific Pokemon across evolutions)
            if pokemon.kills > 0:
                pokemon_kills[str(pokemon.uuid)]['kills'] += pokemon.kills
                pokemon_kills[str(pokemon.uuid)]['evolutions'].append({
                    'name': pokemon.name,
                    'level': pokemon.level,
                    'id': pokemon.pokemon_id
                })
                pokemon_kills[str(pokemon.uuid)]['base'] = pokemon.base

            # Track usage by base species
            pokemon_usage[pokemon.base] += 1

            # Track deaths by base species
            if pokemon.died:
                pokemon_deaths[pokemon.base] += 1

            # Track activity by base species
            if pokemon.turns is not None and pokemon.switch_ins is not None:
                pokemon_activity[pokemon.base]['turns'] += pokemon.turns
                pokemon_activity[pokemon.base]['switch_ins'] += pokemon.switch_ins
                pokemon_activity[pokemon.base]['battles'] += 1

            # NEW: Track move usage
            if pokemon.pp_used:
                for move_name, pp_count in pokemon.pp_used.items():
                    move_usage[move_name] += pp_count

            # NEW: Track damage dealt by specific Pokemon
            if pokemon.damage_dealt is not None and pokemon.damage_dealt > 0:
                pokemon_damage_dealt[str(pokemon.uuid)]['damage'] += pokemon.damage_dealt
                pokemon_damage_dealt[str(pokemon.uuid)]['evolutions'].append({
                    'name': pokemon.name,
                    'level': pokemon.level,
                    'id': pokemon.pokemon_id
                })
                pokemon_damage_dealt[str(pokemon.uuid)]['base'] = pokemon.base

            # NEW: Track damage taken by specific Pokemon (only if they participated)
            participated = (pokemon.turns is not None and pokemon.turns > 0) or (
                        pokemon.switch_ins is not None and pokemon.switch_ins > 0)
            if participated:
                pokemon_damage_taken[str(pokemon.uuid)]['participated'] = True
                if pokemon.damage_taken is not None:
                    pokemon_damage_taken[str(pokemon.uuid)]['damage'] += pokemon.damage_taken
                    pokemon_damage_taken[str(pokemon.uuid)]['evolutions'].append({
                        'name': pokemon.name,
                        'level': pokemon.level,
                        'id': pokemon.pokemon_id
                    })
                    pokemon_damage_taken[str(pokemon.uuid)]['base'] = pokemon.base

    # Helper function to format Pokemon display names
    def format_pokemon_name(evolutions):
        if not evolutions:
            return 'Unknown'

        evolutions_sorted = sorted(evolutions, key=lambda x: (x['id'], x['level']))
        unique_names = []
        seen_names = set()
        for evo in evolutions_sorted:
            if evo['name'] not in seen_names:
                unique_names.append(evo['name'])
                seen_names.add(evo['name'])

        if len(unique_names) == 1:
            return unique_names[0]
        else:
            return ' \u2192 '.join(unique_names)

    # Process top killers (by specific Pokemon UUID)
    top_killers = []
    for uuid, data in pokemon_kills.items():
        top_killers.append({
            'name': format_pokemon_name(data['evolutions']),
            'nickname': pokemon_latest_nickname.get(uuid),
            'kills': data['kills'],
            'base': data['base']
        })
    top_killers = sorted(top_killers, key=lambda x: x['kills'], reverse=True)[:10]

    # Process most used Pokemon (by base species)
    most_used = sorted(
        [{'name': base, 'count': count} for base, count in pokemon_usage.items()],
        key=lambda x: x['count'],
        reverse=True
    )[:10]

    # Process most killed species (by base species)
    most_killed = sorted(
        [{'name': base, 'count': count} for base, count in pokemon_deaths.items()],
        key=lambda x: x['count'],
        reverse=True
    )[:10]

    # Process most active Pokemon (by base species)
    most_active = []
    for base, data in pokemon_activity.items():
        if data['battles'] > 0:
            most_active.append({
                'name': base,
                'turns': data['turns'],
                'switch_ins': data['switch_ins'],
                'battles': data['battles'],
                'avg_turns': round(data['turns'] / data['battles'], 1),
                'avg_switches': round(data['switch_ins'] / data['battles'], 1)
            })
    most_active = sorted(most_active, key=lambda x: (x['turns'], x['switch_ins']), reverse=True)[:10]

    # NEW: Process most used moves
    most_used_moves = sorted(
        [{'name': move, 'count': count} for move, count in move_usage.items()],
        key=lambda x: x['count'],
        reverse=True
    )[:10]

    # NEW: Process most damage dealt
    most_damage_dealt = []
    for uuid, data in pokemon_damage_dealt.items():
        if data['damage'] > 0:
            most_damage_dealt.append({
                'name': format_pokemon_name(data['evolutions']),
                'nickname': pokemon_latest_nickname.get(uuid),
                'damage': round(data['damage'], 1),
                'base': data['base']
            })
    most_damage_dealt = sorted(most_damage_dealt, key=lambda x: x['damage'], reverse=True)[:10]

    # NEW: Process least damage taken (only Pokemon that participated)
    least_damage_taken = []
    for uuid, data in pokemon_damage_taken.items():
        if data['participated']:
            least_damage_taken.append({
                'name': format_pokemon_name(data['evolutions']),
                'nickname': pokemon_latest_nickname.get(uuid),
                'damage': round(data['damage'], 1),
                'base': data['base']
            })
    least_damage_taken = sorted(least_damage_taken, key=lambda x: x['damage'])[:10]

    # NEW: Process most damage taken (sponges)
    most_damage_taken = []
    for uuid, data in pokemon_damage_taken.items():
        if data['participated'] and data['damage'] > 0:
            most_damage_taken.append({
                'name': format_pokemon_name(data['evolutions']),
                'nickname': pokemon_latest_nickname.get(uuid),
                'damage': round(data['damage'], 1),
                'base': data['base']
            })
    most_damage_taken = sorted(most_damage_taken, key=lambda x: x['damage'], reverse=True)[:10]

    # Calculate max values for bar chart scaling
    max_kills = top_killers[0]['kills'] if top_killers else 1
    max_usage = most_used[0]['count'] if most_used else 1
    max_deaths = most_killed[0]['count'] if most_killed else 1
    if most_active:
        max_turns = max(p['turns'] for p in most_active)
        max_switches = max(p['switch_ins'] for p in most_active)
    else:
        max_turns = 1
        max_switches = 1

    # NEW: Max values for new charts
    max_move_usage = most_used_moves[0]['count'] if most_used_moves else 1
    max_damage_dealt = most_damage_dealt[0]['damage'] if most_damage_dealt else 1
    max_damage_taken_least = least_damage_taken[-1]['damage'] if least_damage_taken else 1
    max_damage_taken_most = most_damage_taken[0]['damage'] if most_damage_taken else 1

    # Process trainers and add death/difficulty info
    trainer_list = []
    for trainer in trainers:
        total_battles += trainer['battle_count']

        # Get battles for this trainer
        trainer_battles = TrainerBattle.objects.filter(
            player_name=player_name,
            trainer_name=trainer['trainer_name']
        ).prefetch_related('team')

        # Check if any battle had deaths
        has_deaths = trainer_battles.filter(team__died=True).exists()
        has_wipe = trainer_battles.filter(victory=False).exists()

        # Find highest difficulty
        difficulty_order = {'1': 1, '2': 2, '3': 3}
        highest_difficulty = '1'
        highest_difficulty_num = 1

        for battle in trainer_battles:
            diff_num = difficulty_order.get(battle.difficulty, 2)
            if diff_num > highest_difficulty_num:
                highest_difficulty_num = diff_num
                highest_difficulty = battle.difficulty

        # Convert timestamp
        if trainer['last_battle_timestamp']:
            trainer['last_battle'] = datetime.fromtimestamp(trainer['last_battle_timestamp'] / 1000)

            if trainer['last_battle_timestamp'] > last_battle_timestamp:
                last_battle_timestamp = trainer['last_battle_timestamp']
                last_battle = trainer['last_battle']

        trainer_list.append({
            'trainer_name': trainer['trainer_name'],
            'battle_count': trainer['battle_count'],
            'last_battle': trainer.get('last_battle'),
            'last_battle_ts': trainer.get('last_battle_timestamp') or 0,
            'has_deaths': has_deaths,
            'has_wipe': has_wipe,
            'wipe_score': 1 if has_wipe else 0,
            'death_score': 1 if has_deaths else 0,
            'difficulty_score': highest_difficulty_num,
            'highest_difficulty': highest_difficulty
        })

    SORTS = {
        'date': lambda t: (-t['last_battle_ts'], t['trainer_name']),
        'battles': lambda t: (-t['battle_count'], t['trainer_name']),
        'alpha': lambda t: (t['trainer_name'].lower(),),
        'wipe': lambda t: (-t['wipe_score'], -t['battle_count'], t['trainer_name']),
        'deaths': lambda t: (-t['death_score'], -t['battle_count'], t['trainer_name']),
        'difficulty': lambda t: (-t['difficulty_score'], -t['battle_count'], t['trainer_name']),
    }

    trainer_list.sort(key=SORTS.get(sort, SORTS['date']))

    return render(request, 'xhenos_player.html', {
        'player_name': player_name,
        'trainers': trainer_list,
        'total_battles': total_battle_count,
        'win_percentage': win_percentage,
        'death_percentage': death_percentage,
        'last_battle': last_battle,
        'top_killers': top_killers,
        'most_used': most_used,
        'most_killed': most_killed,
        'most_active': most_active,
        'max_kills': max_kills,
        'max_usage': max_usage,
        'max_deaths': max_deaths,
        'max_turns': max_turns,
        'max_switches': max_switches,
        # NEW: Pass new chart data
        'most_used_moves': most_used_moves,
        'most_damage_dealt': most_damage_dealt,
        'least_damage_taken': least_damage_taken,
        'most_damage_taken': most_damage_taken,
        'max_move_usage': max_move_usage,
        'max_damage_dealt': max_damage_dealt,
        'max_damage_taken_least': max_damage_taken_least,
        'max_damage_taken_most': max_damage_taken_most,
    })


def process_markdown_content(content):
    """Process markdown content with consistent configuration for both changelogs and guides"""
    md = markdown.Markdown(
        extensions=[
            'extra',
            'toc',
            'codehilite',
            'fenced_code',
            'tables',
            'sane_lists'
        ],
        extension_configs={
            'toc': {
                'permalink': False,
                'baselevel': 1,
                'toc_depth': 2,
                'slugify': lambda value, separator: re.sub(r'[-\s]+', separator,
                                                           re.sub(r'[^\w\s-]', '', value).strip().lower()),
            },
            'codehilite': {
                'css_class': 'codehilite',
                'use_pygments': False,
                'noclasses': True
            }
        },
        output_format='html'
    )

    html = md.convert(content)
    toc_html = md.toc if hasattr(md, 'toc') and md.toc.strip() else None

    if toc_html:
        # Remove the entire H1 <li> element (opening tag, link, and nested ul opening)
        # This leaves us with: <div class="toc"><ul><ul>...H2 items...</ul></li></ul></div>
        toc_html = re.sub(
            r'(<div class="toc">\s*<ul>\s*)<li><a[^>]*>[^<]*</a>\s*<ul>',
            r'\1<ul>',  # Keep one <ul> tag
            toc_html,
            count=1,
            flags=re.DOTALL
        )

        # Now remove the trailing </li></ul> that belonged to the H1, leaving just </ul></div>
        toc_html = re.sub(
            r'</ul>\s*</li>\s*</ul>(\s*</div>)$',
            r'</ul>\1',
            toc_html,
            count=1,
            flags=re.DOTALL
        )

    return html, toc_html


def read_changelog(version):
    """Read and process changelog for a specified version"""
    path = Path(f"content/changelogs/changelog_{version}.md")
    if not path.exists():
        return None, None

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # Convert Markdown to HTML
    html, toc_html = process_markdown_content(content)

    # Insert icons into <h2> headings
    for category, icon_html in CATEGORY_ICONS.items():
        pattern = rf"<h2([^>]*)>(\s*){re.escape(category)}(\s*)</h2>"
        replacement = rf'<h2\1>{icon_html} {category}</h2>'
        html = re.sub(pattern, replacement, html)

    return html, toc_html


def normalize_github_links(project):
    """
    Normalize github_link to always be a list of dicts for template compatibility.
    Handles both string URLs and list of link objects.
    """
    github_link = project.get('github_link')

    if not github_link:
        project['github_links'] = []
    elif isinstance(github_link, str):
        # Single string URL - convert to list format
        project['github_links'] = [{'url': github_link, 'label': 'View on GitHub'}]
    elif isinstance(github_link, list):
        # Already a list - use as-is
        project['github_links'] = github_link
    else:
        # Unexpected format - default to empty
        project['github_links'] = []

    return project


def custom_404(request, exception):
    return render(request, '404.html', {}, status=404)