import os
import random
from multiprocessing import Pool
import numpy as np

from env import PokemonTCGEnv
from train import OpponentPolicy, evaluate_agent
from cg.game import battle_start, battle_select, battle_finish
from main import agent as heuristic_agent_main
from model import PokemonFeatureExtractor

from sb3_contrib import MaskablePPO

# Baseline Cards to use for building
# Fire Aggro
FIRE_MON = [31, 46, 76]
FIRE_ENERGY = 2

# Grass Combo
GRASS_MON = [25, 27, 28]
GRASS_ENERGY = 1

# Water Control
WATER_MON = [722, 803, 583]
WATER_ENERGY = 3

TRAINERS = [1145, 1152, 1227, 1235, 1262]

def build_deck(mon_ids, energy_id, ratio=(12, 20, 28)):
    num_mons, num_trainers, num_energy = ratio
    
    deck = []
    
    # Pool of available cards (max 4 each)
    mon_pool = mon_ids * 4
    trainer_pool = TRAINERS * 4
    
    random.shuffle(mon_pool)
    random.shuffle(trainer_pool)
    
    # Add mons
    deck.extend(mon_pool[:num_mons])
    
    # Add trainers
    deck.extend(trainer_pool[:num_trainers])
        
    # Add energy (can have >4)
    while len(deck) < 60:
        deck.append(energy_id)
        
    return deck[:60]

def short_train(deck, steps=10000, model_name="temp_model"):
    print(f"Training {model_name} for {steps} steps...")
    opp_policy = OpponentPolicy(mode="heuristic")
    env = PokemonTCGEnv(opponent_policy=opp_policy, player_deck=deck)
    
    policy_kwargs = dict(
        features_extractor_class=PokemonFeatureExtractor,
        features_extractor_kwargs=dict(features_dim=128),
        net_arch=dict(pi=[128, 128], vf=[128, 128])
    )
    
    model = MaskablePPO(
        "MlpPolicy",
        env,
        policy_kwargs=policy_kwargs,
        verbose=0,
        learning_rate=3e-4,
        n_steps=1024,
        batch_size=64,
        gamma=0.99
    )
    model.learn(total_timesteps=steps)
    
    eval_env = PokemonTCGEnv(opponent_policy=OpponentPolicy(mode="heuristic"), player_deck=deck)
    win_rate = evaluate_agent(eval_env, model, eval_games=10)
    
    model.save(f"{model_name}.zip")
    return win_rate

def phase_1_sweep():
    print("=== PHASE 1: TUNING DECK RATIOS ===")
    # (mons, trainers, energy)
    ratios = [
        (8, 21, 31),
        (12, 20, 28),
        (16, 24, 20),
        (20, 20, 20)
    ]
    
    best_rate = -1
    best_ratio = None
    
    for r in ratios:
        deck = build_deck(WATER_MON, WATER_ENERGY, ratio=r)
        rate = short_train(deck, steps=20000, model_name=f"model_ratio_{r[0]}")
        print(f"Ratio {r} -> Win Rate: {rate*100:.1f}%")
        if rate > best_rate:
            best_rate = rate
            best_ratio = r
            
    print(f"-> Best Ratio Found: {best_ratio} with {best_rate*100:.1f}%\n")
    return best_ratio

def phase_2_generate(best_ratio):
    print("=== PHASE 2: STRATEGY GENERATION ===")
    print(f"Using optimal ratio {best_ratio} for 3 strategies...")
    decks = {
        "Water_Control": build_deck(WATER_MON, WATER_ENERGY, best_ratio),
        "Fire_Aggro": build_deck(FIRE_MON, FIRE_ENERGY, best_ratio),
        "Grass_Combo": build_deck(GRASS_MON, GRASS_ENERGY, best_ratio),
    }
    return decks

def phase_3_gauntlet(decks):
    print("=== PHASE 3: GAUNTLET TRAINING ===")
    trained_models = {}
    for name, deck in decks.items():
        # Train against heuristic for 20k steps
        rate = short_train(deck, steps=20000, model_name=f"model_{name}")
        trained_models[name] = (f"model_{name}.zip", deck, rate)
        print(f"Trained {name}: Eval WR = {rate*100:.1f}%\n")
    return trained_models

def main():
    print("Starting Auto-Meta RL Pipeline...")
    best_ratio = phase_1_sweep()
    strat_decks = phase_2_generate(best_ratio)
    final_models = phase_3_gauntlet(strat_decks)
    
    print("=== PHASE 4: FINAL EVALUATION ===")
    print("Leaderboard:")
    sorted_models = sorted(final_models.items(), key=lambda x: x[1][2], reverse=True)
    for i, (name, data) in enumerate(sorted_models):
        print(f"#{i+1}: {name} (Win Rate: {data[2]*100:.1f}%)")

if __name__ == "__main__":
    main()
