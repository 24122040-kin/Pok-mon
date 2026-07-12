import re

def update():
    with open("main.py", "r") as f:
        content = f.read()

    # 1. Replace get_max_attack_damage
    get_max_dmg_pattern = re.compile(r"def get_max_attack_damage.*?return 10", re.DOTALL)
    new_get_max_dmg = """def get_max_attack_damage(obs, your_idx: int) -> int:
    \"\"\"Calculate maximum damage our active Pokemon can deal.\"\"\"
    player = obs.current.players[your_idx]
    active_pkmn = player.active[0] if player.active else None
    if not active_pkmn:
        return 0
    if active_pkmn.id == 46: # Gouging Fire ex
        return 260 # Blaze Blitz
    elif active_pkmn.id == 31: # Chi-Yu
        return 60 # Ground Melter
    elif active_pkmn.id == 77: # Litten
        return 10
    elif active_pkmn.id == 97: # Litwick
        return 20
    elif active_pkmn.id == 76: # Slugma
        return 10
    return 10"""
    content = get_max_dmg_pattern.sub(new_get_max_dmg, content)

    # 2. Replace score_option
    score_option_pattern = re.compile(r"def score_option.*?return score", re.DOTALL)
    new_score_option = """def score_option(obs, opt, context, your_idx: int) -> float:
    opt_type = opt.type
    player = obs.current.players[your_idx]
    opponent = obs.current.players[1 - your_idx]
    
    score = 100.0
    card_id = get_card_id(obs, opt, your_idx)
    
    if context == SelectContext.SETUP_ACTIVE_POKEMON:
        if card_id == 46: score = 1000.0
        elif card_id == 31: score = 500.0
        else: score = 100.0
            
    elif context == SelectContext.SETUP_BENCH_POKEMON:
        if card_id == 46: score = 1000.0
        else: score = 100.0
            
    elif context in (SelectContext.SWITCH, SelectContext.TO_ACTIVE, SelectContext.ATTACH_FROM):
        pkmn = get_pokemon_from_option(obs, opt, your_idx)
        if pkmn:
            energy_count = len(pkmn.energies)
            if context == SelectContext.ATTACH_FROM:
                if pkmn.id == 46 and energy_count < 3:
                    score = 3200.0 if opt.area == AreaType.ACTIVE else 3000.0
                elif pkmn.id == 31 and energy_count < 2:
                    score = 2900.0 if opt.area == AreaType.ACTIVE else 2400.0
                else: score = 1000.0
            else:
                opp_active = opponent.active[0] if opponent.active else None
                opp_hp = opp_active.hp if opp_active else 999
                max_dmg = get_max_attack_damage(obs, your_idx)
                can_ko = (max_dmg >= opp_hp)
                
                if not can_ko:
                    if pkmn.id != 46: score = 12000.0 - pkmn.hp
                    else: score = 1000.0 
                else:
                    if pkmn.id == 46: score = 2000.0 + energy_count * 100.0
                    elif pkmn.id == 31: score = 1500.0 + energy_count * 100.0
                    else: score = 500.0 + pkmn.hp
        else: score = 100.0
            
    elif context == SelectContext.ATTACH_TO:
        if card_id == 2: score = 1000.0
        else: score = 100.0
            
    elif context in (SelectContext.TO_HAND, SelectContext.TO_BENCH, SelectContext.TO_FIELD):
        if card_id == 46: score = 3000.0
        elif card_id == 31: score = 2500.0
        elif card_id in (1235, 1205, 1227): score = 1800.0
        elif card_id == 2: score = 1000.0
        else: score = 500.0
            
    elif context in (SelectContext.ACTIVATE, SelectContext.MULLIGAN, SelectContext.COIN_HEAD, SelectContext.IS_FIRST) or opt_type in (OptionType.YES, OptionType.NO):
        if opt_type == OptionType.YES: score = 1000.0
        elif opt_type == OptionType.NO: score = 100.0
            
    elif context == SelectContext.MAIN:
        max_dmg = get_max_attack_damage(obs, your_idx)
        opp_active = opponent.active[0] if opponent.active else None
        opp_hp = opp_active.hp if opp_active else 999
        can_ko_active = (max_dmg >= opp_hp)
        
        active_pkmn = player.active[0] if player.active else None
        enemy_max_dmg = calculate_enemy_max_damage_next_turn(obs, 1 - your_idx)
        is_in_lethal_range = active_pkmn and active_pkmn.hp <= enemy_max_dmg
        
        if opt_type == OptionType.ATTACK:
            if can_ko_active: score = 15000.0 
            else: score = 10000.0 
                
        elif opt_type == OptionType.EVOLVE:
            score = 9500.0
            
        elif opt_type == OptionType.ATTACH:
            pkmn = get_pokemon_from_option(obs, opt, your_idx)
            if is_in_lethal_range and opt.inPlayArea == AreaType.ACTIVE:
                score = 3000.0
            else:
                card = None
                if opt.area == AreaType.HAND and player.hand and 0 <= opt.index < len(player.hand):
                    card = player.hand[opt.index]
                if card and pkmn:
                    if card.id == 2: 
                        energy_count = len(pkmn.energies)
                        if opt.inPlayArea == AreaType.ACTIVE:
                            if pkmn.id == 46 and energy_count < 3: score = 8800.0
                            elif pkmn.id == 31 and energy_count < 2: score = 8750.0
                            else: score = 1000.0
                        elif opt.inPlayArea == AreaType.BENCH:
                            if pkmn.id == 46 and energy_count < 3: score = 8600.0
                            elif pkmn.id == 31 and energy_count < 2: score = 8500.0
                            else: score = 900.0
                
        elif opt_type == OptionType.PLAY:
            card = get_card_id(obs, opt, your_idx)
            if card in (1235, 1205): score = 9400.0
            elif card == 1227: score = 9300.0
            elif card == 1145: 
                if can_ko_active: score = 100.0 
                else: score = 9200.0
            else: score = 8000.0
                
        elif opt_type == OptionType.RETREAT:
            if is_in_lethal_range: score = 9100.0
            else: score = 1000.0
                
    return score"""
    content = score_option_pattern.sub(new_score_option, content)

    # 3. Implement Hybrid architecture in agent function
    agent_func_pattern = re.compile(r"def agent.*?return \[0\]", re.DOTALL)
    new_agent_func = """def agent(obs, config):
    \"\"\"Hybrid Kaggle Agent.\"\"\"
    global CARD_DATA_MAP, ATTACK_DMG_MAP
    if not CARD_DATA_MAP:
        CARD_DATA_MAP = load_card_data()
        ATTACK_DMG_MAP = build_attack_damage_map(CARD_DATA_MAP)
        
    try:
        if isinstance(obs, dict):
            obs_obj = to_observation_class(obs)
        else:
            obs_obj = obs
            
        options = obs_obj.select.option
        max_count = obs_obj.select.maxCount
        your_idx = obs_obj.current.yourIndex
        
        # --- PHASE 1: RULE-BASED OVERRIDE (HEURISTIC) ---
        best_score = -999999.0
        best_idx = 0
        
        if max_count == 1 and len(options) > 1:
            for i, opt in enumerate(options):
                try:
                    score = score_option(obs_obj, opt, obs_obj.select.context, your_idx)
                except Exception:
                    score = 100.0
                if score > best_score:
                    best_score = score
                    best_idx = i
                    
            if best_score >= 8500.0:
                # GOD MOVE DETECTED! OVERRIDE RL!
                return [best_idx]
                
        # --- PHASE 2: NEURAL NETWORK (RL MACRO) ---
        return run_onnx_inference(obs_obj)
        
    except Exception as e:
        return [0]"""
    content = agent_func_pattern.sub(new_agent_func, content)

    with open("main.py", "w") as f:
        f.write(content)

if __name__ == "__main__":
    update()
