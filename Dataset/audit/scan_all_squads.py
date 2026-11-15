import pandas as pd

df = pd.read_csv('Dataset/output/master_players.csv')

squads = df.groupby(['country', 'decade'])

for (country, decade), group in squads:
    # Check bowlers with batting > 65
    suspicious = []
    for _, r in group.iterrows():
        role = r['primary_role']
        pos = str(r['eligible_positions'])
        bat = float(r['batting_rating'])
        bowl = float(r['bowling_rating'])
        wk = bool(r['is_wicketkeeper'])
        name = r['player_name']
        pid = r['player_id']
        
        # Check pure bowler marked as top order or high batting
        if role in ('PACE', 'SPIN') and bat > 60:
            suspicious.append(f"Bowler {name} ({pid}) has high bat={bat}")
        if role == 'BAT' and bowl > 60:
            suspicious.append(f"Batter {name} ({pid}) has high bowl={bowl}")
        if role in ('PACE', 'SPIN') and any(p in pos.split('|') for p in ['1', '2', '3', '4']):
            suspicious.append(f"Bowler {name} ({pid}) has top-order positions: {pos}")
        if role == 'BAT' and any(p in pos.split('|') for p in ['10', '11']):
            suspicious.append(f"Batter {name} ({pid}) has tailender positions: {pos}")
            
    if suspicious:
        print(f"=== {country} {decade} ===")
        for s in suspicious:
            print("  ", s)
