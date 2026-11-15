"""
CricXI Phase 4.4 — Comprehensive Player Database Audit & Normalization Script.
Performs full audit, corrects inaccuracies, recalibrates ratings, and ensures data integrity.
"""

import pandas as pd
from pathlib import Path
from typing import Dict, Any, List, Tuple

def clamp_rating(val: float, min_val: float = 0.0, max_val: float = 100.0) -> float:
    return round(max(min_val, min(max_val, float(val))), 1)

def compute_overall_rating(role: str, bat_rat: float, bowl_rat: float, fld_rat: float) -> float:
    r = str(role).strip().upper()
    if r == "BAT":
        ovr = bat_rat * 0.80 + bowl_rat * 0.05 + fld_rat * 0.15
    elif r == "WK":
        ovr = bat_rat * 0.65 + fld_rat * 0.35
    elif r == "AR":
        ovr = bat_rat * 0.45 + bowl_rat * 0.45 + fld_rat * 0.10
    elif r in {"PACE", "SPIN"}:
        ovr = bowl_rat * 0.80 + bat_rat * 0.10 + fld_rat * 0.10
    else:
        ovr = bat_rat * 0.45 + bowl_rat * 0.45 + fld_rat * 0.10
    return clamp_rating(ovr)

def run_audit(dry_run: bool = True):
    csv_path = Path("Dataset/output/master_players.csv")
    players_csv_path = Path("Dataset/output/players.csv")
    
    df = pd.read_csv(csv_path)
    orig_df = df.copy()
    
    changes = [] # list of dicts: player_id, player_name, country, decade, field, old_val, new_val, reason
    
    def record_change(idx, field, old_val, new_val, reason):
        pid = df.at[idx, 'player_id']
        pname = df.at[idx, 'player_name']
        country = df.at[idx, 'country']
        decade = df.at[idx, 'decade']
        changes.append({
            "player_id": pid,
            "player_name": pname,
            "country": country,
            "decade": decade,
            "field": field,
            "old_value": old_val,
            "new_value": new_val,
            "reason": reason
        })
        df.at[idx, field] = new_val

    # 1. Clean NaN / nan / whitespace in string columns
    for idx in range(len(df)):
        # bowling_hand
        bh = str(df.at[idx, 'bowling_hand']).strip()
        if bh in ["nan", "NaN", "", "NoneType", "null"]:
            record_change(idx, 'bowling_hand', df.at[idx, 'bowling_hand'], "None", "Normalized null/nan string to 'None'")
        
        # bowling_type
        bt = str(df.at[idx, 'bowling_type']).strip()
        if bt in ["nan", "NaN", "", "NoneType", "null"]:
            record_change(idx, 'bowling_type', df.at[idx, 'bowling_type'], "None", "Normalized null/nan string to 'None'")

    # 2. Hand vs Bowling Type Mismatch
    # ID 288 Ijaz Ahmed
    ijaz_idx = df[(df['player_name'] == 'Ijaz Ahmed') & (df['decade'] == 1990)].index
    for idx in ijaz_idx:
        if df.at[idx, 'bowling_type'] == 'Left Arm Medium':
            record_change(idx, 'bowling_type', df.at[idx, 'bowling_type'], 'Right Arm Medium', "Fixed hand mismatch: Ijaz Ahmed bowled Right Arm Medium")

    # ID 289 Inzamam-ul-Haq
    inz_idx = df[(df['player_name'] == 'Inzamam-ul-Haq') & (df['decade'] == 1990)].index
    for idx in ijaz_idx:
        if df.at[idx, 'bowling_hand'] == 'Right' and 'Left' in str(df.at[idx, 'bowling_type']):
            record_change(idx, 'bowling_hand', 'Right', 'Left', "Fixed hand mismatch: Inzamam bowled Left Arm Orthodox")

    # 3. Wicketkeeper Corrections
    # Known genuine wicketkeepers who must have is_wicketkeeper = True, bowling = None, bowling_rating <= 5.0
    wk_corrections = [
        # (name, decade, new_role, new_is_wk, new_pos)
        ("Kumar Sangakkara", 2010, "WK", True, "3|4"),
        ("Brendon McCullum", 2010, "WK", True, "1|2|5|6"),
        ("Brendon McCullum", 2000, "WK", True, "1|2|5|6"),
        ("Heinrich Klaasen", 2020, "WK", True, "4|5|6"),
        ("Nicholas Pooran", 2020, "WK", True, "3|4|5|6"),
        ("Mushfiqur Rahim", 2020, "WK", True, "4|5"),
        ("Jonny Bairstow", 2010, "WK", True, "1|2|5|6"),
        ("Rahul Dravid", 2000, "BAT", True, "3|4"), # Designated keeper in 2000s ODIs/WC
        ("KL Rahul", 2020, "BAT", True, "1|2|4|5"), # Regular keeper in ODIs/T20Is
        ("Devon Conway", 2020, "BAT", True, "1|2"), # Regular keeper in T20Is
        ("AB de Villiers", 2000, "BAT", True, "3|4|5|6"),
        ("AB de Villiers", 2010, "BAT", True, "3|4|5|6"),
        ("Andy Flower", 2000, "WK", True, "3|4|5"),
    ]

    for name, decade, role, is_wk, pos in wk_corrections:
        matches = df[(df['player_name'] == name) & (df['decade'] == decade)].index
        for idx in matches:
            if df.at[idx, 'primary_role'] != role:
                record_change(idx, 'primary_role', df.at[idx, 'primary_role'], role, f"Updated role to {role} for authentic profile")
            if df.at[idx, 'is_wicketkeeper'] != is_wk:
                record_change(idx, 'is_wicketkeeper', df.at[idx, 'is_wicketkeeper'], is_wk, f"Verified and set is_wicketkeeper = {is_wk}")
            if df.at[idx, 'eligible_positions'] != pos:
                record_change(idx, 'eligible_positions', df.at[idx, 'eligible_positions'], pos, f"Updated eligible positions to {pos}")
            # Ensure WK does not have active bowling style
            if is_wk:
                if str(df.at[idx, 'bowling_hand']) != "None":
                    record_change(idx, 'bowling_hand', df.at[idx, 'bowling_hand'], "None", "Wicketkeepers do not bowl; set bowling_hand to None")
                if str(df.at[idx, 'bowling_type']) != "None":
                    record_change(idx, 'bowling_type', df.at[idx, 'bowling_type'], "None", "Wicketkeepers do not bowl; set bowling_type to None")
                if float(df.at[idx, 'bowling_rating']) > 10.0:
                    record_change(idx, 'bowling_rating', df.at[idx, 'bowling_rating'], 5.0, "Wicketkeepers do not bowl; normalized bowling_rating to 5.0")

    # Clean any remaining WKs with bowling attributes
    all_wks = df[df['is_wicketkeeper'] == True].index
    for idx in all_wks:
        if str(df.at[idx, 'bowling_hand']) != "None":
            record_change(idx, 'bowling_hand', df.at[idx, 'bowling_hand'], "None", "Cleaned bowling_hand for wicketkeeper")
        if str(df.at[idx, 'bowling_type']) != "None":
            record_change(idx, 'bowling_type', df.at[idx, 'bowling_type'], "None", "Cleaned bowling_type for wicketkeeper")
        if float(df.at[idx, 'bowling_rating']) > 10.0:
            record_change(idx, 'bowling_rating', df.at[idx, 'bowling_rating'], 5.0, "Normalized bowling_rating to 5.0 for wicketkeeper")

    # Steve Smith 2010: Right Arm Leg Spin (he bowled leg spin throughout early 2010s)
    smith_idx = df[(df['player_name'] == 'Steve Smith') & (df['decade'] == 2010)].index
    for idx in smith_idx:
        if str(df.at[idx, 'bowling_hand']) == "None" or str(df.at[idx, 'bowling_type']) == "None":
            record_change(idx, 'bowling_hand', df.at[idx, 'bowling_hand'], 'Right', "Steve Smith bowled leg spin in 2010s")
            record_change(idx, 'bowling_type', df.at[idx, 'bowling_type'], 'Leg Spin', "Steve Smith bowled leg spin in 2010s")

    # 4. Role Corrections for All-rounders & Specialists
    # Irfan Pathan 2000 -> AR (was PACE, 9|10|11)
    irfan_idx = df[(df['player_name'] == 'Irfan Pathan') & (df['decade'] == 2000)].index
    for idx in irfan_idx:
        record_change(idx, 'primary_role', df.at[idx, 'primary_role'], 'AR', "Irfan Pathan is an authentic international all-rounder")
        record_change(idx, 'eligible_positions', df.at[idx, 'eligible_positions'], '6|7|8', "Authentic batting position for all-rounder Irfan Pathan")

    # 5. Position Flexibility Normalization
    # Explicit examples from prompt:
    # Babar Azam: 2,3 (or 2|3)
    babar_idx = df[(df['player_name'] == 'Babar Azam') & (df['decade'] == 2020)].index
    for idx in babar_idx:
        record_change(idx, 'eligible_positions', df.at[idx, 'eligible_positions'], '2|3', "Set realistic flexibility per prompt specification (2,3)")

    # Mitchell Starc: 9,10 (or 9|10)
    starc_idx = df[df['player_name'] == 'Mitchell Starc'].index
    for idx in starc_idx:
        record_change(idx, 'eligible_positions', df.at[idx, 'eligible_positions'], '9|10', "Set realistic flexibility per prompt specification (9,10)")

    # Adam Gilchrist: 1|2|6|7
    gilchrist_idx = df[df['player_name'] == 'Adam Gilchrist'].index
    for idx in gilchrist_idx:
        record_change(idx, 'eligible_positions', df.at[idx, 'eligible_positions'], '1|2|6|7', "Gilchrist was world-renowned opening WK in white ball cricket")

    # Dean Jones: 3|4
    dj_idx = df[df['player_name'] == 'Dean Jones'].index
    for idx in dj_idx:
        record_change(idx, 'eligible_positions', df.at[idx, 'eligible_positions'], '3|4', "Dean Jones batted No. 3/4 in ODIs")

    # Ricky Ponting 1990: 3|4
    punter_idx = df[(df['player_name'] == 'Ricky Ponting') & (df['decade'] == 1990)].index
    for idx in punter_idx:
        record_change(idx, 'eligible_positions', df.at[idx, 'eligible_positions'], '3|4', "Ricky Ponting batted at No. 3")

    # Sachin Tendulkar 1990 & 2000: 1|2|3|4
    sachin_idx = df[df['player_name'] == 'Sachin Tendulkar'].index
    for idx in sachin_idx:
        record_change(idx, 'eligible_positions', df.at[idx, 'eligible_positions'], '1|2|3|4', "Sachin was premier opener in ODIs and No. 4 in Tests")

    # Jos Buttler 2020: 1|2|5|6
    buttler_idx = df[df['player_name'] == 'Jos Buttler'].index
    for idx in buttler_idx:
        record_change(idx, 'eligible_positions', df.at[idx, 'eligible_positions'], '1|2|5|6', "Buttler opens in T20s and bats 5/6 in ODIs")

    # Rishabh Pant 2020: 4|5|6|7
    pant_idx = df[df['player_name'] == 'Rishabh Pant'].index
    for idx in pant_idx:
        record_change(idx, 'eligible_positions', df.at[idx, 'eligible_positions'], '4|5|6|7', "Pant bats 4/5 in T20s and Tests")

    # Quinton de Kock 2010: 1|2|3
    qdk_idx = df[(df['player_name'] == 'Quinton de Kock') & (df['decade'] == 2010)].index
    for idx in qdk_idx:
        record_change(idx, 'eligible_positions', df.at[idx, 'eligible_positions'], '1|2|3', "de Kock opened the batting throughout 2010s")

    # Tailenders (Pure No. 10/11 bowlers who shouldn't be batting at 9)
    tailenders_10_11 = [
        "Glenn McGrath", "Courtney Walsh", "Muttiah Muralitharan", "Jasprit Bumrah",
        "Mohammed Siraj", "Allan Donald", "Waqar Younis", "Shoaib Akhtar", "Bob Willis",
        "Ewen Chatfield", "Trent Boult", "Josh Hazlewood", "Mohammed Shami", "Neil Foster"
    ]
    for tname in tailenders_10_11:
        t_matches = df[df['player_name'] == tname].index
        for idx in t_matches:
            if df.at[idx, 'eligible_positions'] == '9|10|11':
                record_change(idx, 'eligible_positions', df.at[idx, 'eligible_positions'], '10|11', f"Genuine tailender {tname} restricted to 10|11")

    # 6. Ratings Normalization for Small-Sample Penalized Legends
    calibrated_ratings = [
        # (name, decade, field, new_rating, reason)
        # Batters
        ("Sachin Tendulkar", 2000, "batting_rating", 84.0, "Small sample penalty correction: all-time great batsman"),
        ("Inzamam-ul-Haq", 2000, "batting_rating", 80.0, "Small sample penalty correction: premier international batsman"),
        ("Mohammad Yousuf", 2000, "batting_rating", 80.0, "Small sample penalty correction: premier international batsman"),
        ("Younis Khan", 2010, "batting_rating", 74.0, "Small sample penalty correction: World T20 winning captain/batsman"),
        ("Michael Vaughan", 2000, "batting_rating", 74.0, "Small sample penalty correction: Ashes-winning captain/batsman"),
        ("Jonathan Trott", 2010, "batting_rating", 75.0, "Small sample penalty correction: premier top-order batsman"),
        ("Marnus Labuschagne", 2020, "batting_rating", 78.0, "Small sample penalty correction: elite international batsman"),
        ("Marvan Atapattu", 2000, "batting_rating", 76.0, "Small sample penalty correction: premier opening batsman"),
        ("Ashwell Prince", 2000, "batting_rating", 74.0, "Small sample penalty correction: solid middle-order batsman"),
        ("Jacques Rudolph", 2000, "batting_rating", 74.0, "Small sample penalty correction: international batsman"),
        ("Wavell Hinds", 2000, "batting_rating", 72.0, "Small sample penalty correction: international opening batsman"),
        ("Hamilton Masakadza", 2000, "batting_rating", 69.0, "Small sample penalty correction: premier Zimbabwean batsman"),
        ("Tamim Iqbal", 2000, "batting_rating", 70.0, "Small sample penalty correction: premier opening batsman"),
        ("Imrul Kayes", 2010, "batting_rating", 65.0, "Small sample penalty correction: international opening batsman"),
        ("Mominul Haque", 2020, "batting_rating", 68.0, "Small sample penalty correction: international top-order batsman"),
        ("Mushfiqur Rahim", 2020, "batting_rating", 72.0, "Small sample penalty correction: veteran international batsman"),
        ("Lou Vincent", 2000, "batting_rating", 68.0, "Small sample penalty correction: international batsman"),
        ("Nathan Astle", 2000, "batting_rating", 75.0, "Small sample penalty correction: premier international batsman"),
        ("Tom Latham", 2010, "batting_rating", 67.0, "Small sample penalty correction: international batsman"),
        ("Asad Shafiq", 2010, "batting_rating", 70.0, "Small sample penalty correction: international batsman"),
        ("Abdullah Shafique", 2020, "batting_rating", 72.0, "Small sample penalty correction: international batsman"),
        ("Dimuth Karunaratne", 2010, "batting_rating", 70.0, "Small sample penalty correction: premier opening batsman"),
        ("Dimuth Karunaratne", 2020, "batting_rating", 70.0, "Small sample penalty correction: premier opening batsman"),
        ("Shivnarine Chanderpaul", 2000, "batting_rating", 78.0, "Small sample penalty correction: all-time great batsman"),
        ("Shivnarine Chanderpaul", 2010, "batting_rating", 74.0, "Small sample penalty correction: all-time great batsman"),
        ("Kraigg Brathwaite", 2010, "batting_rating", 68.0, "Small sample penalty correction: international opening batsman"),
        
        # Bowlers
        ("Glenn McGrath", 2000, "bowling_rating", 84.0, "Small sample penalty correction: all-time legendary pace bowler"),
        ("Jason Gillespie", 2000, "bowling_rating", 82.0, "Small sample penalty correction: premier international pace bowler"),
        ("Nathan Lyon", 2010, "bowling_rating", 84.0, "Small sample penalty correction: elite international spinner"),
        ("Mashrafe Mortaza", 2000, "bowling_rating", 75.0, "Small sample penalty correction: premier strike bowler"),
        ("Shahadat Hossain", 2000, "bowling_rating", 72.0, "Small sample penalty correction: international strike bowler"),
        ("Mashrafe Mortaza", 2010, "bowling_rating", 76.0, "Small sample penalty correction: premier strike bowler"),
        ("Taijul Islam", 2020, "bowling_rating", 76.0, "Small sample penalty correction: international spinner"),
        ("James Anderson", 2000, "bowling_rating", 80.0, "Small sample penalty correction: all-time great swing bowler"),
        ("Steve Harmison", 2000, "bowling_rating", 80.0, "Small sample penalty correction: world-class fast bowler"),
        ("Ishant Sharma", 2010, "bowling_rating", 78.0, "Small sample penalty correction: premier international pace bowler"),
        ("Mohammed Shami", 2010, "bowling_rating", 82.0, "Small sample penalty correction: elite international strike bowler"),
        ("Mohammed Shami", 2020, "bowling_rating", 86.0, "Small sample penalty correction: elite international strike bowler"),
        ("Chris Martin", 2000, "bowling_rating", 76.0, "Small sample penalty correction: frontline strike pace bowler"),
        ("Shoaib Akhtar", 2000, "bowling_rating", 84.0, "Small sample penalty correction: legendary express fast bowler"),
        ("Junaid Khan", 2010, "bowling_rating", 76.0, "Small sample penalty correction: international strike pace bowler"),
        ("Yasir Shah", 2010, "bowling_rating", 80.0, "Small sample penalty correction: premier international leg spinner"),
        ("Makhaya Ntini", 2000, "bowling_rating", 82.0, "Small sample penalty correction: premier international pace bowler"),
        ("Nuwan Kulasekara", 2000, "bowling_rating", 80.0, "Small sample penalty correction: ICC World No.1 swing bowler"),
        ("Nuwan Pradeep", 2010, "bowling_rating", 74.0, "Small sample penalty correction: international strike bowler"),
        ("Suranga Lakmal", 2010, "bowling_rating", 76.0, "Small sample penalty correction: international strike pace bowler"),
        ("Kasun Rajitha", 2020, "bowling_rating", 74.0, "Small sample penalty correction: international strike pace bowler"),
        ("Fidel Edwards", 2000, "bowling_rating", 78.0, "Small sample penalty correction: express international fast bowler"),
        ("Kemar Roach", 2010, "bowling_rating", 80.0, "Small sample penalty correction: premier international fast bowler"),
        ("Shannon Gabriel", 2010, "bowling_rating", 78.0, "Small sample penalty correction: express international fast bowler"),
        ("Jayden Seales", 2020, "bowling_rating", 76.0, "Small sample penalty correction: frontline international pace bowler"),
        ("Brian Vitori", 2010, "bowling_rating", 72.0, "Small sample penalty correction: international strike pace bowler"),
        ("Jason Holder", 2010, "bowling_rating", 76.0, "Calibration correction: premier international all-rounder"),
        
        # Non-bowler / part-timer corrections
        ("Darren Bravo", 2010, "bowling_rating", 10.0, "Pure batsman with 0 international wickets; normalized bowling_rating"),
        ("Vusi Sibanda", 2010, "bowling_rating", 25.0, "Occasional part-timer; normalized inflated bowling_rating"),
    ]

    for name, decade, field, new_rating, reason in calibrated_ratings:
        matches = df[(df['player_name'] == name) & (df['decade'] == decade)].index
        for idx in matches:
            old_val = df.at[idx, field]
            if abs(float(old_val) - float(new_rating)) > 0.05:
                record_change(idx, field, old_val, new_rating, reason)

    # 7. Recalculate Overall Ratings where ratings or role changed
    for idx in range(len(df)):
        role = df.at[idx, 'primary_role']
        b_r = float(df.at[idx, 'batting_rating'])
        bw_r = float(df.at[idx, 'bowling_rating'])
        f_r = float(df.at[idx, 'fielding_rating'])
        new_ovr = compute_overall_rating(role, b_r, bw_r, f_r)
        old_ovr = float(df.at[idx, 'overall_rating'])
        if abs(new_ovr - old_ovr) > 0.05:
            record_change(idx, 'overall_rating', old_ovr, new_ovr, "Recalculated overall_rating using project formula")

    print(f"Total changes recorded: {len(changes)}")
    
    # Validation checks
    assert len(df) == 506, f"Row count changed: {len(df)}"
    assert df['player_id'].nunique() == 506, "Player ID count mismatch"
    assert (df['player_id'] == orig_df['player_id']).all(), "Player IDs were altered!"
    assert not df['player_id'].duplicated().any(), "Duplicate player IDs found!"

    # Field change breakdowns
    field_counts = {}
    for c in changes:
        f = c['field']
        field_counts[f] = field_counts.get(f, 0) + 1
    print("Changes by field:", field_counts)

    if not dry_run:
        df.to_csv(csv_path, index=False)
        print(f"Successfully saved updated master dataset to {csv_path}")
        
        # Also sync players.csv (first 11 columns)
        players_cols = [
            "player_id", "player_name", "country", "decade", "batting_hand",
            "bowling_hand", "bowling_type", "primary_role", "eligible_positions",
            "is_captain", "is_wicketkeeper"
        ]
        players_df = df[players_cols].copy()
        players_df.to_csv(players_csv_path, index=False)
        print(f"Successfully synced players metadata to {players_csv_path}")

    return df, changes

if __name__ == "__main__":
    run_audit(dry_run=False)
