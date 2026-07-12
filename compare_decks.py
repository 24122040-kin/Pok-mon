import os
import random
from multiprocessing import Pool
from cg.game import battle_start, battle_select, battle_finish
from main import agent as heuristic_agent_main, read_deck_csv

# Define candidate decks
DECKS = {
    # Deck A: Extreme Glass-Cannon (Evolved by GA)
    "Deck A (Glass-Cannon)": (
        [722]*2 + [723]*3 + [1145]*4 + [1152]*2 + [1227]*2 + [3]*47
    ),
    
    # Deck B: Balanced Water Meta (Surfing Beach Stadium)
    "Deck B (Balanced Meta)": (
        [722]*4 + [723]*4 + [1145]*4 + [1152]*4 + [1205]*2 + [1227]*4 + [1235]*4 + [1262]*2 + [1158]*1 + [3]*31
    ),
    
    # Deck C: 12-Pokemon Balanced (Surfing Beach Stadium)
    "Deck C (12-Pokemon Balanced)": (
        [721]*4 + [722]*4 + [723]*4 + [1145]*4 + [1152]*4 + [1205]*2 + [1227]*4 + [1262]*2 + [1158]*1 + [3]*31
    ),

    # Deck D: 14-Pokemon Sustainability
    "Deck D (14-Pokemon Sustainability)": (
        [722]*4 + [723]*4 + [803]*4 + [583]*2 + [1145]*4 + [1152]*4 + [1205]*2 + [1227]*4 + [1235]*4 + [1262]*2 + [1158]*1 + [3]*25
    )
}

def load_opponent_decks() -> list[list[int]]:
    opponent_decks = []
    opp_dir = "opponent_decks"
    if os.path.exists(opp_dir):
        for f in os.listdir(opp_dir):
            if f.endswith(".csv"):
                try:
                    with open(os.path.join(opp_dir, f), "r") as file:
                        deck = [int(line.strip()) for line in file.read().split("\n") if line.strip()][:60]
                        if len(deck) == 60:
                            opponent_decks.append(deck)
                except Exception:
                    pass
    if not opponent_decks:
        opponent_decks.append(read_deck_csv())
    return opponent_decks

def play_one_game(args) -> int:
    player_deck, opponent_deck = args
    try:
        battle_finish()
    except Exception:
        pass
        
    try:
        obs_dict, start_data = battle_start(player_deck, opponent_deck)
        step_count = 0
        while step_count < 200:
            current = obs_dict.get("current")
            if not current or current.get("result", -1) != -1:
                break
                
            choices = heuristic_agent_main(obs_dict)
            obs_dict = battle_select(choices)
            step_count += 1
            
        current = obs_dict.get("current")
        if current and current.get("result") == 0:
            return 1
    except Exception:
        pass
    return 0

def evaluate_deck(player_deck: list[int], opponent_decks: list[list[int]], num_games=50) -> float:
    games_args = []
    for _ in range(num_games):
        opp_deck = random.choice(opponent_decks)
        games_args.append((player_deck, opp_deck))
        
    with Pool() as pool:
        results = pool.map(play_one_game, games_args)
        
    return sum(results) / num_games

def main():
    opp_decks = load_opponent_decks()
    print(f"Loaded {len(opp_decks)} opponent decks.")
    
    best_name = None
    best_rate = -1.0
    best_deck = None
    
    print("\n=== RUNNING DECK TOURNAMENT ===")
    for name, deck_list in DECKS.items():
        # Ensure deck is exactly 60 cards
        if len(deck_list) != 60:
            print(f"Error: {name} has {len(deck_list)} cards, skipping.")
            continue
            
        rate = evaluate_deck(deck_list, opp_decks, num_games=50)
        print(f"{name}: Win Rate = {rate*100:.1f}%")
        
        if rate > best_rate:
            best_rate = rate
            best_name = name
            best_deck = deck_list
            
    print(f"\nWinner: {best_name} with Win Rate = {best_rate*100:.1f}%")
    
    # Save the winner deck to deck.csv
    with open("deck.csv", "w") as file:
        file.write("\n".join(str(card_id) for card_id in best_deck) + "\n")
    print(f"Saved {best_name} to deck.csv.")

if __name__ == "__main__":
    main()
