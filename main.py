import os
import random

from cg.api import (
    Observation,
    to_observation_class,
    OptionType,
    SelectType,
    SelectContext,
    AreaType,
    CardType
)

def read_deck_csv() -> list[int]:
    """Read deck.csv.
    
    Returns:
        list[int]: A list of card IDs in the deck.
    """
    file_path = "deck.csv"
    if not os.path.exists(file_path):
        file_path = "/kaggle_simulations/agent/" + file_path
    with open(file_path, "r") as file:
        csv = file.read().split("\n")
    deck = []
    for i in range(60):
        deck.append(int(csv[i]))
    return deck

def get_pokemon_from_option(obs: Observation, opt, your_idx: int):
    player_idx = opt.playerIndex if getattr(opt, "playerIndex", None) is not None else your_idx
    player = obs.current.players[player_idx]
    
    # 1. Check inPlayArea and inPlayIndex
    in_play_area = getattr(opt, "inPlayArea", None)
    in_play_index = getattr(opt, "inPlayIndex", None)
    if in_play_area is not None:
        if in_play_area == AreaType.ACTIVE:
            return player.active[0] if player.active else None
        elif in_play_area == AreaType.BENCH:
            if in_play_index is not None and 0 <= in_play_index < len(player.bench):
                return player.bench[in_play_index]
                
    # 2. Check area and index (when the option itself represents a card in play)
    area = getattr(opt, "area", None)
    index = getattr(opt, "index", None)
    if area is not None:
        if area == AreaType.ACTIVE:
            return player.active[0] if player.active else None
        elif area == AreaType.BENCH:
            if index is not None and 0 <= index < len(player.bench):
                return player.bench[index]
                
    return None

def get_card_id(obs: Observation, opt, your_idx: int) -> int:
    # Check cardId directly
    card_id = getattr(opt, "cardId", None)
    if card_id is not None and card_id != 0:
        return card_id
        
    # Check card in area
    area = getattr(opt, "area", None)
    index = getattr(opt, "index", None)
    player_idx = opt.playerIndex if getattr(opt, "playerIndex", None) is not None else your_idx
    
    if area is not None and index is not None:
        player = obs.current.players[player_idx]
        if area == AreaType.HAND:
            if player.hand and 0 <= index < len(player.hand):
                return player.hand[index].id
        elif area == AreaType.LOOKING:
            if obs.current.looking and 0 <= index < len(obs.current.looking):
                card = obs.current.looking[index]
                return card.id if card else 0
        elif area == AreaType.DISCARD:
            if player.discard and 0 <= index < len(player.discard):
                return player.discard[index].id
        elif area == AreaType.DECK:
            if obs.select and obs.select.deck and 0 <= index < len(obs.select.deck):
                return obs.select.deck[index].id
        elif area == AreaType.ACTIVE:
            if player.active:
                return player.active[0].id
        elif area == AreaType.BENCH:
            if 0 <= index < len(player.bench):
                return player.bench[index].id
                
    return 0

def get_max_attack_damage(obs: Observation, your_idx: int) -> int:
    """Calculate maximum damage our active Pokemon can deal."""
    player = obs.current.players[your_idx]
    active_pkmn = player.active[0] if player.active else None
    if not active_pkmn:
        return 0
    if active_pkmn.id == 723: # Mega Abomasnow ex
        return 200 # Frost Barrier consistent damage
    elif active_pkmn.id == 721: # Kyogre
        return 130 # Swirling Waves damage
    elif active_pkmn.id == 722: # Snover
        return 30
    return 10

def score_option(obs: Observation, opt, context, your_idx: int) -> float:
    opt_type = opt.type
    player = obs.current.players[your_idx]
    opponent = obs.current.players[1 - your_idx]
    
    score = 100.0
    
    # Get card details if applicable
    card_id = get_card_id(obs, opt, your_idx)
    
    # 1. SETUP ACTIVE POKEMON
    if context == SelectContext.SETUP_ACTIVE_POKEMON:
        if card_id == 721: # Kyogre
            score = 1000.0
        elif card_id == 722: # Snover
            score = 500.0
        else:
            score = 100.0
            
    # 2. SETUP BENCH POKEMON
    elif context == SelectContext.SETUP_BENCH_POKEMON:
        if card_id in (721, 722):
            score = 1000.0
        else:
            score = 100.0
            
    # 3. SWITCH or TO_ACTIVE or ATTACH_FROM (Selecting a Pokémon in play)
    elif context in (SelectContext.SWITCH, SelectContext.TO_ACTIVE, SelectContext.ATTACH_FROM):
        pkmn = get_pokemon_from_option(obs, opt, your_idx)
        if pkmn:
            energy_count = len(pkmn.energies)
            
            if context == SelectContext.ATTACH_FROM:
                # Selecting which Pokémon to attach energy to
                # Prioritize active if it needs energy
                if opt.area == AreaType.ACTIVE:
                    if pkmn.id == 723 and energy_count < 3: # Mega Abomasnow ex
                        score = 3000.0
                    elif pkmn.id == 721 and energy_count < 3: # Kyogre
                        score = 2900.0
                    elif pkmn.id == 722 and energy_count < 2: # Snover
                        score = 2800.0
                    else:
                        score = 1000.0
                else: # Bench
                    if pkmn.id == 722 and energy_count < 2:
                        score = 2500.0
                    elif pkmn.id == 721 and energy_count < 3:
                        score = 2400.0
                    elif pkmn.id == 723 and energy_count < 3:
                        score = 2300.0
                    else:
                        score = 1000.0
            else:
                # Switching / promoting Active Pokémon
                # Prioritize Abomasnow ex, then Kyogre, then Snover
                if pkmn.id == 723:
                    score = 2000.0 + energy_count * 100.0
                elif pkmn.id == 721:
                    score = 1500.0 + energy_count * 100.0
                elif pkmn.id == 722:
                    score = 1000.0 + energy_count * 100.0
                else:
                    score = 500.0 + pkmn.hp
        else:
            score = 100.0
            
    # 4. ATTACH_TO (Selecting a card to attach)
    elif context == SelectContext.ATTACH_TO:
        # Prioritize Water Energy (ID 3) or Maximum Belt (ID 1158)
        if card_id == 1158:
            score = 2000.0
        elif card_id == 3:
            score = 1000.0
        else:
            score = 100.0
            
    # 5. TO_HAND, TO_BENCH, TO_FIELD (Searching/Moving cards)
    elif context in (SelectContext.TO_HAND, SelectContext.TO_BENCH, SelectContext.TO_FIELD):
        # Check if we have Snover on board
        has_snover = len(player.bench) > 0 or (player.active and player.active[0] and player.active[0].id == 722)
        
        if card_id == 723: # Mega Abomasnow ex
            score = 3000.0 if has_snover else 1500.0
        elif card_id == 722: # Snover
            score = 2500.0
        elif card_id == 721: # Kyogre
            score = 2000.0
        elif card_id in (1235, 1205, 1227): # Supporters
            score = 1800.0
        elif card_id == 3: # Water Energy
            score = 1000.0
        else:
            score = 500.0
            
    # 6. ACTIVATE / YES_NO / MULLIGAN / COIN_HEAD / IS_FIRST
    elif context in (SelectContext.ACTIVATE, SelectContext.MULLIGAN, SelectContext.COIN_HEAD, SelectContext.IS_FIRST) or opt_type in (OptionType.YES, OptionType.NO):
        if opt_type == OptionType.YES:
            score = 1000.0
        elif opt_type == OptionType.NO:
            score = 100.0
            
    # 7. MAIN PHASE SELECTION
    elif context == SelectContext.MAIN:
        max_dmg = get_max_attack_damage(obs, your_idx)
        opp_active = opponent.active[0] if opponent.active else None
        opp_hp = opp_active.hp if opp_active else 999
        can_ko_active = (max_dmg >= opp_hp)
        
        # --- RULE 3: BYPASS & SNIPE (ATTACK DECISION) ---
        if opt_type == OptionType.ATTACK:
            if can_ko_active:
                score = 15000.0 # Secure KO immediately
            else:
                # Normal attack preference logic
                if opt.attackId == 1047: # Frost Barrier (200 damage)
                    score = 11000.0
                elif opt.attackId == 1046: # Hammer-lanche
                    if player.deckCount < 15:
                        score = 8000.0
                    else:
                        score = 10000.0
                elif opt.attackId == 1043: # Swirling Waves (130 damage)
                    score = 9500.0
                elif opt.attackId == 1042: # Riptide
                    score = 9400.0
                else:
                    score = 9000.0
                
        elif opt_type == OptionType.EVOLVE:
            score = 9500.0
            
        elif opt_type == OptionType.ATTACH:
            # We are attaching a card from hand to a Pokémon in play
            # Let's find the card being attached
            card = None
            if opt.area == AreaType.HAND and player.hand and 0 <= opt.index < len(player.hand):
                card = player.hand[opt.index]
                
            pkmn = get_pokemon_from_option(obs, opt, your_idx)
            if card and pkmn:
                if card.id == 1158: # Maximum Belt
                    if pkmn.id in (723, 721):
                        score = 8900.0 if opt.inPlayArea == AreaType.ACTIVE else 8600.0
                    else:
                        score = 500.0
                elif card.id == 3: # Water Energy
                    energy_count = len(pkmn.energies)
                    if opt.inPlayArea == AreaType.ACTIVE:
                        if pkmn.id == 723 and energy_count < 3:
                            score = 8800.0
                        elif pkmn.id == 721 and energy_count < 3:
                            score = 8750.0
                        elif pkmn.id == 722 and energy_count < 2:
                            score = 8700.0
                        else:
                            score = 7000.0
                    else: # Bench
                        if pkmn.id == 722 and energy_count < 2:
                            score = 8600.0
                        elif pkmn.id == 721 and energy_count < 3:
                            score = 8500.0
                        elif pkmn.id == 723 and energy_count < 3:
                            score = 8400.0
                        else:
                            score = 7000.0
            else:
                score = 7000.0
                
        elif opt_type == OptionType.PLAY:
            card = None
            if player.hand and 0 <= opt.index < len(player.hand):
                card = player.hand[opt.index]
                
            if card:
                # --- RULE 1: ANTI-GASSING OUT ---
                # Prioritize playing drawing Supporter cards when hand is small and no KO is possible
                if len(player.hand) < 3 and not can_ko_active:
                    if card.id in (1227, 1235): # Lillie / Waitress
                        score = 12000.0
                    elif card.id == 1126: # Precious Trolley
                        score = 11500.0
                else:
                    if card.id == 1126: # Precious Trolley
                        score = 9000.0
                    elif card.id == 1152: # Poké Pad
                        score = 8600.0
                    elif card.id in (722, 721): # Snover / Kyogre
                        score = 8500.0
                    elif card.id in (1145, 1205): # Mega Signal / Cyrano
                        score = 8000.0
                    elif card.id == 1235: # Waitress
                        score = 7800.0
                    elif card.id == 1227: # Lillie's Determination
                        if len(player.hand) <= 3:
                            score = 7900.0
                        else:
                            score = 5000.0
                    else:
                        score = 7000.0
            else:
                score = 7000.0
                
        elif opt_type == OptionType.ABILITY:
            # --- RULE 1: ANTI-GASSING OUT ---
            if len(player.hand) < 3 and not can_ko_active:
                score = 11500.0
            else:
                score = 7500.0
            
        elif opt_type == OptionType.RETREAT:
            # --- RULE 2: PRIZE DENIAL & RETREAT ---
            # If Active is low HP (<= 50) and we have a bench backup, prioritize retreating!
            active_pkmn = player.active[0] if player.active else None
            if active_pkmn and active_pkmn.hp <= 50 and len(player.bench) > 0:
                is_ex = getattr(active_pkmn, "ex", False) or active_pkmn.id == 723
                score = 14000.0 if is_ex else 11000.0
            else:
                score = 100.0
                
        elif opt_type == OptionType.END:
            score = 10.0
            
    return score

def agent(obs_dict: dict) -> list[int]:
    """Implement Your Pokémon Trading Card Game Agent.
    
    Each element in the returned list must be >= 0 and < len(obs.select.option).
    The list length must be between obs.select.minCount and obs.select.maxCount (inclusive), with no duplicate elements.
    
    Returns:
        list[int]: A list of option index.
    """
    obs: Observation = to_observation_class(obs_dict)
    if obs.select == None:
        # In the initial selection, the obs.select is None, and it is necessary to return the deck.
        # The deck is a list of 60 card IDs.
        # The deck must comply with the Pokémon Trading Card Game rules.
        return read_deck_csv()
    
    context = obs.select.context
    options = obs.select.option
    your_idx = obs.current.yourIndex
    
    # Score all options
    scored_options = []
    for i, opt in enumerate(options):
        try:
            score = score_option(obs, opt, context, your_idx)
        except Exception:
            score = 100.0
        scored_options.append((score, i))
        
    # Sort options by score descending
    scored_options.sort(key=lambda x: x[0], reverse=True)
    
    # Select maxCount elements
    k = obs.select.maxCount
    selected_indices = [idx for score, idx in scored_options[:k]]
    
    return selected_indices
