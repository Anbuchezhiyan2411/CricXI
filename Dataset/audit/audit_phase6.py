import pandas as pd
import numpy as np

df = pd.read_csv('Dataset/output/master_players.csv')

print(f"Total rows: {len(df)}")

# Check duplicate player inconsistencies
dups = df[df.duplicated('player_name', keep=False)].sort_values(['player_name', 'decade'])
print(f"Total duplicate instances: {len(dups)} across {len(dups['player_name'].unique())} unique players\n")

inconsistencies = []
for name, grp in dups.groupby('player_name'):
    roles = grp['primary_role'].tolist()
    decades = grp['decade'].tolist()
    pids = grp['player_id'].tolist()
    wks = grp['is_wicketkeeper'].tolist()
    b_hands = grp['batting_hand'].tolist()
    bw_types = grp['bowling_type'].tolist()
    poss = grp['eligible_positions'].tolist()
    
    if len(set(roles)) > 1:
        inconsistencies.append({
            'player': name,
            'issue': 'Inconsistent primary_role',
            'details': [(pid, dec, r) for pid, dec, r in zip(pids, decades, roles)]
        })
    if len(set(wks)) > 1:
        inconsistencies.append({
            'player': name,
            'issue': 'Inconsistent is_wicketkeeper',
            'details': [(pid, dec, w) for pid, dec, w in zip(pids, decades, wks)]
        })
    if len(set(b_hands)) > 1:
        inconsistencies.append({
            'player': name,
            'issue': 'Inconsistent batting_hand',
            'details': [(pid, dec, bh) for pid, dec, bh in zip(pids, decades, b_hands)]
        })

print(f"Found {len(inconsistencies)} duplicate consistency issues:")
for inc in inconsistencies:
    print(f"  [{inc['issue']}] {inc['player']}: {inc['details']}")

print("\n--- Detailed inspection of troubled squads ---")
for sq in [('South Africa', 2000), ('South Africa', 2010), ('South Africa', 2020), ('Sri Lanka', 2000), ('Sri Lanka', 2010)]:
    c, d = sq
    sub = df[(df['country'] == c) & (df['decade'] == d)]
    print(f"\n=== {c} {d} ===")
    for _, r in sub.iterrows():
        p_id = r['player_id']
        name = r['player_name']
        role = r['primary_role']
        wk = r['is_wicketkeeper']
        cpt = r['is_captain']
        pos = r['eligible_positions']
        bat = r['batting_rating']
        bowl = r['bowling_rating']
        fld = r['fielding_rating']
        ovr = r['overall_rating']
        print(f"{p_id:3d} | {name:22s} | {role:5s} | WK:{str(wk):5s} | CPT:{str(cpt):5s} | Pos:{pos:10s} | Bat:{bat:4.1f} | Bowl:{bowl:4.1f} | Fld:{fld:4.1f} | Ovr:{ovr:4.1f}")

