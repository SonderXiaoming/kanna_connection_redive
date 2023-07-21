from  ..util.tools import lap2stage, stage_dict, boss_max
from .base import float2int

standard = {
    "low": 0.3,
    "high": 0.8, 
    "e_low":0.1,
    "e_high":0.3 
}

def kpi_dao(damage, order, lap):
    stage = stage_dict[lap2stage(lap)]
    rate = damage / boss_max[stage-1][order-1]

    if stage == 5:
        if rate > standard["high"]:
            return 1.5 #e面高伤特别奖励
        elif rate > standard["e_high"]:
            return 1
        elif rate < standard["e_low"]:
            return 0.5
        else:
            return 0.5 / (standard['e_high'] - standard['e_low']) * (rate - standard['e_low']) + 0.5
    
    if rate > standard["high"]:
        return 1
    elif rate < standard["low"]:
        return 0.5
    else:
        return 0.5 / (standard['high'] - standard['low']) * (rate - standard['low']) + 0.5
    
    
def kpi_report(info, special):
    player_info = {}
    for player in info:
        pcrid = str(player['pcrid'])
        if pcrid not in player_info:
            correct = 0 if pcrid not in special else special[pcrid]
            player_info[pcrid] = {"pcrid":pcrid,"name":player['name'],"knife":correct,"correct":correct}
        
        player_info[pcrid]["knife"] += kpi_dao(player['damage'], int(player["boss"]), player['lap'])

    players = [(player["pcrid"],player["name"],float2int(round(player["knife"], 3)), player["correct"]) for player in list(player_info.values())]
    players.sort(key = lambda x:x[2],reverse=True)
    return players