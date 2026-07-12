import os
import random
import numpy as np
import torch as th
from env import PokemonTCGEnv
from model import PokemonFeatureExtractor
from train import OpponentPolicy, evaluate_agent, export_to_onnx
from sb3_contrib import MaskablePPO

# 1. Define Teams Configuration
# 4 Elements X 4 Ratios = 16 Teams
ELEMENTS = {
    "Fire":  {"mons": [31, 46, 76, 77, 97], "energy": 2},
    "Grass": {"mons": [25, 27, 28, 45, 1], "energy": 1},
    "Water": {"mons": [33, 35, 47, 722, 803], "energy": 3},
    "Mix":   {"mons": [31, 46, 25, 27, 33, 722], "energy": 3}
}

RATIOS = {
    "GlassCannon": (8, 21, 31),
    "Balanced":    (12, 20, 28),
    "Control":     (16, 24, 20),
    "Swarm":       (20, 20, 20)
}

TRAINERS = [1145, 1152, 1227, 1235, 1262, 1205]

def build_deck(mon_ids, energy_id, ratio):
    num_mons, num_trainers, num_energy = ratio
    deck = []
    mon_pool = mon_ids * 4
    trainer_pool = TRAINERS * 4
    random.shuffle(mon_pool)
    random.shuffle(trainer_pool)
    
    deck.extend(mon_pool[:num_mons])
    deck.extend(trainer_pool[:num_trainers])
    while len(deck) < 60:
        deck.append(energy_id)
    return deck[:60]

def init_model(env):
    policy_kwargs = dict(
        features_extractor_class=PokemonFeatureExtractor,
        features_extractor_kwargs=dict(features_dim=128),
        net_arch=dict(pi=[128, 128], vf=[128, 128])
    )
    return MaskablePPO("MlpPolicy", env, policy_kwargs=policy_kwargs, learning_rate=3e-4, n_steps=1024, batch_size=64, verbose=0)

def main():
    print("========================================")
    print("   POKEMON TCG AI WORLD CUP 2026")
    print("========================================")
    
    teams = {}
    
    print("Phase 1: Generating 16 Teams and initializing models...")
    for elem_name, elem_data in ELEMENTS.items():
        for ratio_name, ratio_val in RATIOS.items():
            team_name = f"{elem_name}_{ratio_name}"
            deck = build_deck(elem_data["mons"], elem_data["energy"], ratio_val)
            teams[team_name] = {"deck": deck, "model": None, "win_rate": 0.0}
    
    # Phase 2: Group Stage - Random Matchmaking
    EPOCHS = 5
    STEPS_PER_EPOCH = 10000
    
    envs = {}
    for team_name in teams.keys():
        env = PokemonTCGEnv(player_deck=teams[team_name]["deck"])
        model = init_model(env)
        teams[team_name]["model"] = model
        envs[team_name] = env
        
    print(f"\nPhase 2: Group Stage ({EPOCHS} Epochs)")
    for epoch in range(1, EPOCHS + 1):
        print(f"--- Epoch {epoch}/{EPOCHS} ---")
        team_names = list(teams.keys())
        random.shuffle(team_names)
        
        for team in team_names:
            opponent_team = random.choice([t for t in team_names if t != team])
            opp_policy = OpponentPolicy(mode="rl")
            opp_policy.model = teams[opponent_team]["model"]
            envs[team].opponent_policy = opp_policy
            
            teams[team]["model"].learn(total_timesteps=STEPS_PER_EPOCH)
            print(f"  [{team}] trained vs [{opponent_team}]")
            
    print("\nPhase 3: Final Evaluation (Knockout Stage)")
    for team in teams.keys():
        eval_env = PokemonTCGEnv(player_deck=teams[team]["deck"], opponent_policy=OpponentPolicy(mode="heuristic"))
        wr = evaluate_agent(eval_env, teams[team]["model"], eval_games=30)
        teams[team]["win_rate"] = wr
        print(f"Team {team} Evaluation WR: {wr*100:.1f}%")
        
    print("\n========================================")
    print("   WORLD CUP FINAL LEADERBOARD")
    print("========================================")
    sorted_teams = sorted(teams.items(), key=lambda x: x[1]["win_rate"], reverse=True)
    for i, (name, data) in enumerate(sorted_teams):
        print(f"#{i+1}: {name} - WR: {data['win_rate']*100:.1f}%")
        
    champion_name = sorted_teams[0][0]
    champion_deck = sorted_teams[0][1]["deck"]
    champion_model = sorted_teams[0][1]["model"]
    
    print(f"\n🏆 CHAMPION: {champion_name} 🏆")
    print("Saving champion's deck and ONNX model...")
    
    with open("deck.csv", "w") as f:
        f.write("\n".join(map(str, champion_deck)) + "\n")
        
    champion_model.save("model_Champion.zip")
    export_to_onnx(champion_model, "model.onnx")
    print("World Cup finished successfully. Check deck.csv and model.onnx.")

if __name__ == "__main__":
    main()
