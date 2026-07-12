import csv

with open("EN_Card_Data.csv", "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    print(f"{'ID':<5} | {'Name':<25} | {'HP':<4} | {'Damage'}")
    print("-" * 50)
    seen = set()
    for row in reader:
        if row["Stage (Pokémon)/Type (Energy and Trainer)"] == "Basic Pokémon" and "{W}" in row["Type"] and row["Card ID"] not in seen:
            seen.add(row["Card ID"])
            print(f"{row['Card ID']:<5} | {row['Card Name']:<25} | {row['HP']:<4} | {row['Damage']}")
