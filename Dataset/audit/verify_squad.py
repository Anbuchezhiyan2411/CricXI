def compute_overall_rating(primary_role: str, bat: float, bowl: float, fld: float) -> float:
    role = primary_role.upper()
    if role == 'BAT':
        val = bat * 0.80 + bowl * 0.05 + fld * 0.15
    elif role == 'WK':
        val = bat * 0.65 + fld * 0.35
    elif role == 'AR':
        val = bat * 0.45 + bowl * 0.45 + fld * 0.10
    elif role in ('PACE', 'SPIN'):
        val = bowl * 0.80 + bat * 0.10 + fld * 0.10
    else:
        val = bat * 0.40 + bowl * 0.40 + fld * 0.20
    return round(min(100.0, max(0.0, val)), 1)


def verify_squad(squad_dict, squad_name="Squad"):
    errors = []
    player_keys = list(squad_dict.keys())
    if len(player_keys) != 11:
        errors.append(f"{squad_name}: Must have exactly 11 players, found {len(player_keys)}")
        return False, errors

    captains = [k for k in player_keys if squad_dict[k].get("is_captain")]
    if len(captains) != 1:
        errors.append(f"{squad_name}: Must have exactly 1 captain, found {len(captains)}: {captains}")

    keepers = [k for k in player_keys if squad_dict[k].get("is_wicketkeeper")]
    if len(keepers) < 1:
        errors.append(f"{squad_name}: Must have at least 1 wicketkeeper, found 0")

    # Bowling options
    bowlers = [k for k in player_keys if squad_dict[k].get("primary_role") in ("PACE", "SPIN", "AR") or squad_dict[k].get("bowling_rating", 0) >= 60.0]
    if len(bowlers) < 5:
        errors.append(f"{squad_name}: Must have at least 5 bowling options, found {len(bowlers)}")

    # Check bipartite matching for positions 1..11
    adj = {}
    for k in player_keys:
        pos_str = str(squad_dict[k]["eligible_positions"])
        positions = [int(p) for p in pos_str.split("|") if p.isdigit()]
        adj[k] = positions

    # Bipartite matching via backtracking
    def find_match(idx, occupied):
        if idx == len(player_keys):
            return True
        p_id = player_keys[idx]
        for pos in adj[p_id]:
            if 1 <= pos <= 11 and pos not in occupied:
                occupied.add(pos)
                if find_match(idx + 1, occupied):
                    return True
                occupied.remove(pos)
        return False

    if not find_match(0, set()):
        errors.append(f"{squad_name}: Fails Hall's marriage condition / bipartite matching for positions 1..11!")

    return len(errors) == 0, errors

