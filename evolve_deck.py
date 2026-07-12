import os
import random
import argparse
from multiprocessing import Pool
from cg.game import battle_start, battle_select, battle_finish
from main import agent as heuristic_agent_main

# Allowed Card Pool for Abomasnow ex/Kyogre archetype optimization
ALLOWED_CARDS = {
    3: "Basic Water Energy",
    721: "Kyogre",
    722: "Snover",
    723: "Mega Abomasnow ex",
    1126: "Precious Trolley (ACE SPEC)",
    1145: "Mega Signal",
    1152: "Poké Pad",
    1158: "Maximum Belt (ACE SPEC)",
    1205: "Cyrano",
    1227: "Lillie's Determination",
    1235: "Waitress"
}

ACE_SPECS = {1126, 1158}

def validate_and_format_deck(deck_dict: dict) -> list[int]:
    """Ensure the deck is exactly 60 cards and respects all Pokemon TCG rules."""
    deck = []
    # 1. Enforce max 1 ACE SPEC
    has_ace_spec = False
    for card_id in ACE_SPECS:
        if deck_dict.get(card_id, 0) > 0:
            if has_ace_spec:
                deck_dict[card_id] = 0 # remove duplicates of ACE SPEC
            else:
                deck_dict[card_id] = 1 # maximum 1 of any ACE SPEC
                has_ace_spec = True
                
    # 2. Enforce max 4 of any card (excluding energy ID 3)
    for card_id, count in deck_dict.items():
        if card_id != 3:
            deck_dict[card_id] = min(count, 4)
            
    # 3. Ensure at least 1 Basic Pokemon (721 or 722)
    if deck_dict.get(721, 0) == 0 and deck_dict.get(722, 0) == 0:
        deck_dict[721] = 2 # default fallback
        
    # 4. Fill remaining cards with Water Energy to make exactly 60 cards
    non_energy_sum = sum(count for card_id, count in deck_dict.items() if card_id != 3)
    if non_energy_sum > 59:
        # If too many cards, scale down some trainers
        for card_id in list(deck_dict.keys()):
            if card_id != 3 and card_id not in {721, 722, 723}:
                deck_dict[card_id] = max(0, deck_dict[card_id] - 2)
        non_energy_sum = sum(count for card_id, count in deck_dict.items() if card_id != 3)
        
    deck_dict[3] = 60 - non_energy_sum
    
    # Construct flat list
    for card_id, count in deck_dict.items():
        deck.extend([card_id] * count)
        
    return sorted(deck)

def load_opponent_decks() -> list[list[int]]:
    """Load all opponent decks from the opponent_decks/ folder."""
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
        # Fallback to current deck if none found
        from main import read_deck_csv
        opponent_decks.append(read_deck_csv())
    return opponent_decks

def play_one_game(args) -> int:
    """Run a single simulation game. Returns 1 if player 0 wins, 0 otherwise."""
    player_deck, opponent_deck = args
    try:
        battle_finish() # clear any old state
    except Exception:
        pass
        
    try:
        obs_dict, start_data = battle_start(player_deck, opponent_deck)
        step_count = 0
        while step_count < 200:
            current = obs_dict.get("current")
            if not current or current.get("result", -1) != -1:
                break
                
            active_player = current.get("yourIndex", 0)
            # Both players use the same smart heuristic baseline policy
            choices = heuristic_agent_main(obs_dict)
            obs_dict = battle_select(choices)
            step_count += 1
            
        current = obs_dict.get("current")
        if current and current.get("result") == 0:
            return 1
    except Exception:
        pass
    return 0

def evaluate_deck_fitness(player_deck: list[int], opponent_decks: list[list[int]], num_games=30) -> float:
    """Run parallel simulations to compute win rate for a candidate deck."""
    games_args = []
    for _ in range(num_games):
        opp_deck = random.choice(opponent_decks)
        games_args.append((player_deck, opp_deck))
        
    # Use multiprocessing Pool to evaluate games in parallel
    with Pool() as pool:
        results = pool.map(play_one_game, games_args)
        
    win_rate = sum(results) / num_games
    return win_rate

def generate_random_deck() -> list[int]:
    """Generate a valid random deck from the allowed card pool."""
    deck_dict = {card_id: 0 for card_id in ALLOWED_CARDS}
    # Randomly assign counts between 0 and 4
    for card_id in ALLOWED_CARDS:
        if card_id != 3:
            if card_id in ACE_SPECS:
                deck_dict[card_id] = random.choice([0, 1])
            else:
                deck_dict[card_id] = random.randint(0, 4)
    return validate_and_format_deck(deck_dict)

def mutate_deck(deck: list[int]) -> list[int]:
    """Apply random mutations to a deck list."""
    # Convert list to dict
    deck_dict = {card_id: deck.count(card_id) for card_id in ALLOWED_CARDS}
    
    # 2-3 mutations
    for _ in range(random.randint(1, 3)):
        # Decr a non-energy card
        candidates_to_decr = [c for c, count in deck_dict.items() if c != 3 and count > 0]
        if candidates_to_decr:
            decr_card = random.choice(candidates_to_decr)
            deck_dict[decr_card] -= 1
            
        # Incr a random card
        incr_card = random.choice(list(ALLOWED_CARDS.keys()))
        if incr_card != 3:
            deck_dict[incr_card] += 1
            
    return validate_and_format_deck(deck_dict)

def crossover_decks(deck_a: list[int], deck_b: list[int]) -> list[int]:
    """Perform crossover between two parent decks."""
    dict_a = {c: deck_a.count(c) for c in ALLOWED_CARDS}
    dict_b = {c: deck_b.count(c) for c in ALLOWED_CARDS}
    
    child_dict = {}
    for c in ALLOWED_CARDS:
        # Take average count of parents
        child_dict[c] = int(round((dict_a[c] + dict_b[c]) / 2.0))
        
    return validate_and_format_deck(child_dict)

def main():
    parser = argparse.ArgumentParser(description="Evolve Pokemon TCG deck using Genetic Algorithm.")
    parser.add_argument("--generations", type=int, default=5, help="Number of GA generations.")
    parser.add_argument("--population", type=int, default=10, help="GA population size.")
    args = parser.parse_args()

    opp_decks = load_opponent_decks()
    print(f"Loaded {len(opp_decks)} opponent decks.")

    # 1. Initialize population
    print("Initializing GA Population...")
    # Seed population with current deck list
    from main import read_deck_csv
    current_deck = read_deck_csv()
    population = [current_deck]
    for _ in range(args.population - 1):
        population.append(generate_random_deck())

    # 2. GA Epoch Loop
    for gen in range(args.generations):
        print(f"\n=== GENERATION {gen + 1}/{args.generations} ===")
        
        # Evaluate fitness
        fitness_scores = []
        for i, ind in enumerate(population):
            win_rate = evaluate_deck_fitness(ind, opp_decks, num_games=30)
            fitness_scores.append((win_rate, ind))
            print(f"Individual {i+1}: Win Rate = {win_rate*100:.1f}%")
            
        # Sort by win rate descending
        fitness_scores.sort(key=lambda x: x[0], reverse=True)
        best_win_rate = fitness_scores[0][0]
        best_deck = fitness_scores[0][1]
        
        print(f"Gen {gen+1} Best Win Rate: {best_win_rate*100:.1f}%")
        
        # Select parents (Top 40%)
        num_parents = max(2, int(args.population * 0.4))
        parents = [ind for score, ind in fitness_scores[:num_parents]]
        
        # Generate offspring
        next_population = [best_deck] # Keep best deck (Elitisms)
        while len(next_population) < args.population:
            if random.random() < 0.7:
                # Crossover
                p1, p2 = random.sample(parents, 2)
                child = crossover_decks(p1, p2)
            else:
                # Mutation
                parent = random.choice(parents)
                child = mutate_deck(parent)
            next_population.append(child)
            
        population = next_population

    # 3. Save final best deck list
    print(f"\nGA Optimization Complete! Best Win Rate = {best_win_rate*100:.1f}%")
    
    # Save best deck to deck.csv
    with open("deck.csv", "w") as file:
        file.write("\n".join(str(card_id) for card_id in best_deck) + "\n")
    print("Saved optimal evolved deck to deck.csv.")

if __name__ == "__main__":
    main()
