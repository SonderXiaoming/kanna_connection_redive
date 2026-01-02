import os
import time
import json
from .bigfun import get_boss_info,get_record
from ..util.text2img import image_draw
from ..util.tools import load_config, lap2stage, stage_dict, rate_score, DATA_PATH
from ...convert2img.convert2img import grid2imgb64
from hoshino.modules.priconne._pcr_data import CHARA_NAME
try:
    from ..fendao.timeaxis import units2workid
except:
    def units2workid(x): return []

run_path = os.path.join(os.path.dirname(__file__),"rungroup.json")
clan_path = os.path.join(DATA_PATH, 'clanbattle')

def find_item(item_list, id):
    for item in item_list:
        if item["id"] == id:
            return item["stock"]
    else:
        return 0

def float2int(num):
    if num == int(num):
        return int(num)
    else:
        return num

def format_time(time):
    time = int(time)
    time_str = ""
    if hour := time // 3600:
        time_str += f"{hour}小时"
    if minute := time % 3600 // 60:
        time_str += f"{minute}分钟"
    if second := time % 60:
        time_str += f"{second}秒"
    return time_str

def format_bignum(num):
    if num > 10000:
        return f"{num//10000}万"
    return num

def format_precent(num):
    if num < 0.00005:
        return "血皮"
    return f"{num*100:.2f}%"

def clanbattle_report(info, max_dao):
    player_info = {}
    all_damage = 0
    all_score = 0
    for player in info:
        pcrid = str(player['pcrid'])
        if pcrid not in player_info:
            player_info[pcrid] = {"pcrid":pcrid,"name":player['name'],"knife":0,"damage":0,"score":0}
        player_info[pcrid]["knife"] += 1 if player['flag'] == 0 else 0.5
        player_info[pcrid]["damage"] += player['damage']
        all_damage += player['damage']
        boss_rate = rate_score[lap2stage(player['lap'])][int(player['boss'])-1]
        player_info[pcrid]["score"] += boss_rate * player['damage']
        all_score += boss_rate * player['damage']
    players = [(player["pcrid"],player["name"],min(float2int(player["knife"]), max_dao),player["damage"],int(player["score"])) for player in list(player_info.values())]
    players.sort(key = lambda x:x[4],reverse=True)
    return players, all_damage, int(all_score)

def day_report(info):
    player_info = {}
    for player in info:
        pcrid = str(player['pcrid'])
        if pcrid not in player_info:
            player_info[pcrid] = {"pcrid":pcrid,"name":player['name'],"knife":0}
        player_info[pcrid]["knife"] += 1 if player['flag'] == 0 else 0.5
    players = [(player["pcrid"],player["name"],float2int(player["knife"])) for player in list(player_info.values())]
    return players

async def get_stat(data,group_id):
    config_file = os.path.join(clan_path, f'{group_id}',"clanbattle.json")
    config = await load_config(config_file)
    member_dao = []
    stat = {3: [], 2.5: [], 2: [], 1.5: [], 1: [], 0.5: [], 0: []}
    reply = []
    reply.append("以下是出刀次数统计：\n")
    total = 0
    for member in data:
        name = member[1]
        dao = min(member[2], 3)
        stat[dao].append(name)
        total += dao
        member_dao.append(name)
    reply.append(f'总计出刀：{total}')
    stat[0] = list(set(list(config["member"])) - set(member_dao))
    for k, v in stat.items():
        if len(v) > 0:
            reply.append(f"\n----------\n以下是出了{k}刀的成员：")
            reply.append('|'.join(v))
    msg = "".join(reply)
    img = image_draw(msg)
    return img

async def cuidao(data, dnum, group_id):
    if dnum < 1 or dnum > 3:
        msg = "您输入的数字不合法！"
        return msg

    config_file = os.path.join(clan_path, f'{group_id}',"clanbattle.json")
    config = await load_config(config_file)

    member_finished = dict()
    for member in data:
        if member[2] >= (4 - dnum):
            member_finished[member[1]] = member[0]
    key_difference = set(config["member"].keys()) - set(member_finished.keys())
    members = {k: config["member"][k] for k in key_difference}
    return members.values()

async def get_cbreport(data,total_damage,total_score):
    reply = []
    for index,member in enumerate(data):
        name = member[1]
        knife = member[2]
        damage = member[3]
        score = member[4]
        rate_damage = f"{member[3]/total_damage*100:.2f}%"
        rate_score = f"{member[4]/total_score*100:.2f}%"
        reply.append([str(index+1),name,str(knife),str(damage),str(score),str(rate_damage),str(rate_score)])
    img = grid2imgb64(reply,["排名","昵称","出刀次数","造成伤害","分数","伤害占比","分数占比"])
    return img

async def get_kpireport(data):
    return grid2imgb64([[str(index+1),member[1], member[0], str(member[2]), str(member[3])] for index, member in enumerate(data)],["排名","昵称","游戏id","等效出刀", "补正"])

async def get_plyerreport(data):
    reply = []
    knife = 0
    for dao in data:
        time_str = time.strftime("%Y/%m/%d-%H:%M:%S" ,time.localtime(dao["time"]))
        knife += 1 if dao['flag'] == 0 else 0.5
        item = "完整刀" if not dao['flag'] else "尾刀" if dao['flag'] == 1 else "补偿"
        score = int(rate_score[lap2stage(dao['lap'])][int(dao['boss'])-1] * dao['damage'])
        reply.append([time_str, str(knife), f"{dao['damage']}", f"{dao['lap']}周目{dao['boss']}王", str(score), item, str(dao["history_id"])])
    img = grid2imgb64(reply[::-1],["日期","出刀次数","造成伤害","BOSS", "得分", "类型", "出刀编号"])
    return img

async def bigfun_fix(group_id, db):
    config_file = os.path.join(clan_path, f'{group_id}',"clanbattle.json")
    config = await load_config(config_file)

    if "cookie" not in config:
        raise Exception("请先发送“绑定团队战工具帮助”")
    
    if "member" not in config:
        raise Exception("请先发送“出刀监控”")
    
    cookie = config["cookie"]
    config["boss"] = await get_boss_info(cookie)
    
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False)
    
    result = await get_record(cookie)
    await db.member_check()
    await db.bigfun_check(result)

    return "修正完成，一切都回到了最开始，最本源，最正确的样子"

async def dao_detial(info):
    order = info[1]
    stage = lap2stage(info[0])
    stage_num = stage_dict[stage]
    msg = f"{stage}面{stage_num}阶段，{info[0]}周目，{order}王"
    for i in range(5):
        msg += f"\n{CHARA_NAME[info[i + 3] // 100][0]} 星级:{info[i + 8]} RANK:{info[i + 13]} 专武:{info[i + 23]} 造成伤害:{info[i + 18]}"
    predict_work = await units2workid(info[3:8], stage_num, order)
    msg += "\n可能作业：" + (str(predict_work) if predict_work else "未收录轴")
    return msg

class CancleError(Exception):
    pass
