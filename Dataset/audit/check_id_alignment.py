import sys
sys.path.insert(0, '.')
import pandas as pd
from Dataset.audit.data_afghanistan import AFGHANISTAN_PLAYERS
from Dataset.audit.data_australia import AUSTRALIA_PLAYERS
from Dataset.audit.data_bangladesh import BANGLADESH_PLAYERS
from Dataset.audit.data_england import ENGLAND_PLAYERS
from Dataset.audit.data_india import INDIA_PLAYERS
from Dataset.audit.data_new_zealand import NEW_ZEALAND_PLAYERS
from Dataset.audit.data_pakistan import PAKISTAN_PLAYERS
from Dataset.audit.data_south_africa import SOUTH_AFRICA_PLAYERS
from Dataset.audit.data_sri_lanka import SRI_LANKA_PLAYERS
from Dataset.audit.data_west_indies import WEST_INDIES_PLAYERS
from Dataset.audit.data_zimbabwe import ZIMBABWE_PLAYERS

all_audit = {}
for d in [
    AFGHANISTAN_PLAYERS, AUSTRALIA_PLAYERS, BANGLADESH_PLAYERS,
    ENGLAND_PLAYERS, INDIA_PLAYERS, NEW_ZEALAND_PLAYERS,
    PAKISTAN_PLAYERS, SOUTH_AFRICA_PLAYERS, SRI_LANKA_PLAYERS,
    WEST_INDIES_PLAYERS, ZIMBABWE_PLAYERS
]:
    all_audit.update(d)

df = pd.read_csv('Dataset/output/master_players.csv')

name_mismatches = []
for idx, r in df.iterrows():
    pid = int(r['player_id'])
    csv_name = str(r['player_name']).strip()
    audit_data = all_audit.get(pid)
    if not audit_data:
        name_mismatches.append(f"PID {pid}: Missing from audit files! CSV has '{csv_name}'")
    else:
        audit_name = audit_data['player_name'].strip()
        if csv_name.lower() != audit_name.lower():
            name_mismatches.append(f"PID {pid} ({r['country']} {r['decade']}): CSV name '{csv_name}' != Audit name '{audit_name}'")

print(f"Total name/ID mismatches found: {len(name_mismatches)}")
for m in name_mismatches:
    print(" ", m)
