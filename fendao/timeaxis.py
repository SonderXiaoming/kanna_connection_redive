import os
import json
import copy
import itertools
from hoshino import aiorequests
from nonebot import on_startup
from ..util.tools import stage_dict
from hoshino.modules.priconne._pcr_data import CHARA_NAME

clanbattlework_path = os.path.join(os.path.dirname(__file__), 'clanbattlework.json')

MAX_calculate = 114514  # 最大计算量
MAX_result = 3  # 最大获取结果数
Max_query = 8  # 一个boss显示几个作业
single_limit = 3  # 一个阶段中一个boss显示几个作业


async def get_clanbattlework():
    global clanbattlework
    clanbattle_work = {}
    boss_id = 0
    check_id = None
    # 获取json数据
    if os.path.exists(clanbattlework_path):
        with open(clanbattlework_path, 'r', encoding='utf-8') as load_f:
            clanbattlework = json.load(load_f)
    else:
        clanbattlework_local_path = os.path.join(os.path.dirname(__file__), 'clanbattlework.local.json')
        with open(clanbattlework_local_path, 'r', encoding='utf-8') as load_f:
            clanbattlework = json.load(load_f)
    try:
        res = await aiorequests.get("https://www.caimogu.cc/gzlj/data?date=", headers={'x-requested-with': 'XMLHttpRequest'})
        data = await res.json()
        for work in data["data"]:
            hw_id = work["id"]
            stage = work["stage"]
            if hw_id != check_id:
                check_id = hw_id
                boss_id += 1
                clanbattle_work[boss_id] = {}
            clanbattle_work[boss_id][stage] = {
                "rate": work["rate"], 
                "bosswork": {}
                }
            for bosswork in work["homework"]:
                clanbattle_work[boss_id][stage]["bosswork"][bosswork["sn"]] = {
                    "info": bosswork["info"], 
                    "unit_id": bosswork["unit"], 
                    "damage": bosswork["damage"], 
                    "video_link": bosswork["video"]
                    }
        if clanbattle_work[1][1]["bosswork"] == {}:
            return False
        with open(clanbattlework_path, "w", encoding='utf-8') as f:
            json.dump(clanbattle_work, f, ensure_ascii=False)
        with open(clanbattlework_path, 'r', encoding='utf-8') as load_f:
            clanbattlework = json.load(load_f)
        return True
    except:
        return False

async def units2workid(units, stage, boss):
    result = []
    if clanbattlework: 
        try:
            works = clanbattlework[str(boss)][str(stage)]["bosswork"]
            for work_id in works:
                if set(units) <= set(works[work_id]["unit_id"]):
                    result.append(work_id)
        except:
            pass
    return result

@on_startup
async def check_msg():
    if not await get_clanbattlework():
        print('作业刷新失败')  # 启动就获取一次


async def type2chinese(type):
    msg = ""
    type_edit = type.upper()
    if "S" in type_edit:
        msg += "手动"
    if "T" in type_edit:
        msg += "自动"
    if "W" in type_edit:
        msg += "尾刀"
    return "" if msg == "手动自动尾刀" else msg


async def workid2unitid(workid_list):
    teams = []
    for workid in workid_list:
        result = await get_info(workid[0], work_id=workid)
        team = (workid, str(result["damage"]), result["unit_id"])
        teams.append(team)
    return teams


async def letter2stageid(stage_letter):
    return str(stage_dict[stage_letter.upper()])


async def get_info(stage, boss=None, work_id=None, type="TWS"):
    clanbattlework_copy = copy.deepcopy(clanbattlework)  # 使用深度拷贝，防止字典被污染

    if not stage.isdigit():
        stage = await letter2stageid(stage)

    if work_id:
        return clanbattlework_copy[work_id[-3]][await letter2stageid(work_id[0])]["bosswork"][work_id.upper()]

    works_list = [clanbattlework_copy[str(i)][stage]["bosswork"] for i in range(1, 5 + 1)] if not boss else [clanbattlework_copy[str(boss)][stage]["bosswork"]]

    type = type.upper()
    # type,T自动，W尾刀，S手动

    for work in works_list:
        for work_id in list(work):
            if "T" in type and "T" in work_id:
                continue
            if "W" in type and "W" in work_id:
                continue
            if "S" in type and len(work_id[:-3]) == 1:
                continue
            del work[work_id]
    return works_list

class fendao():

    def __init__(self, stage, arrange, set_type="TS", all_boss=()):
        self.set_stage = stage.upper()
        self.set_arrange = arrange
        self.set_type = set_type.upper()
        self.all_boss = all_boss
        self.work_dict = {}

    def set_black(self, loss_units=[], black_units=[], black_work=[]):
        self.loss_units = loss_units
        self.black_units = black_units
        self.black_work = black_work
        self.box = set(CHARA_NAME) - set(loss_units)

    def set_auto(self, autoinfo, qqid):
        self.autoinfo = autoinfo
        self.qqid = qqid

    def judge2team(self, x, y):
        return len(set(x+y)) > 8

    async def CheckAvailability(self, perm: tuple):

        knife = len(perm)

        box = self.box

        check = False

        def same_chara(x, y):
            return 10 - len(x | y)

        def have_chara(x):
            return len(x & box)

        def have_84(x, y):
            return have_chara(x) >= 8 and have_chara(y) >= 4

        if knife == 1:  # 剩1刀没出
            x = set(perm[0][0])
            if have_chara(x) >= 4:  # 五个角色里有4个可用即可
                check = True

        elif knife == 2:  # 剩2刀没出
            x, y = set(perm[0][0]), set(perm[1][0])
            if same_chara(x, y) == 0:  # 如果没有重复
                if have_chara(x) >= 4 and have_chara(y) >= 4:  # 这两队中每队的5个角色要有4个
                    check = True
                elif same_chara(x, y) <= 2:  # 有1~2个重复
                    if have_chara(x | y) >= 8:  # 这两队中出现的角色要有8个
                        check = True

        elif knife == 3:  # 剩3刀没出
            x, y, z = set(perm[0][0]), set(perm[1][0]), set(perm[2][0])
            jxy, jyz, jxz = same_chara(x, y), same_chara(
                y, z), same_chara(x, z)  # 获取两两之间重复角色
            if jxy < 3 and jyz < 3 and jxz < 3 and jxy + jxz + jyz <= 3:
                # print("无冲，接下来判断当前账号是否可用")
                if jxy + jxz + jyz == 3:  # 210/111
                    if set(x | y | z).issubset(box):  # 三队中出现的所有角色都要有
                        check = True
                elif (jxy == 0) + (jxz == 0) + (jyz == 0) == 2:  # 200/100:  # 200/100
                    # 重复的两队有8个角色 另一队有4个
                    if jxy and have_84(x | y, z) or jxz and have_84(x | z, y) or jyz and have_84(y | z, x):
                        check = True
                elif jxy + jxz + jyz == 0:  # 000
                    if have_chara(x) >= 4 and have_chara(y) >= 4 and have_chara(z) >= 4:  # 每队有4个
                        check = True
                else:  # 110:
                    if have_chara(x | y | z) >= 12:  # 三队中出现的所有角色（13个）要有任意12个
                        check = True

        if check:
            total_damage = 0
            total_score = 0
            teamid_list = []
            for data in perm:
                total_damage += data[1]
                total_score += data[2]
                teamid_list.append(data[3])
            teamid_list.sort()
            return True, total_damage, total_score, teamid_list
        else:
            return False, 0, 0, []

    async def get_result(self):
        res = []
        for perm in itertools.product(*self.worklist):
            avail, total_damage, total_score, teamid_list = await self.CheckAvailability(perm)
            if avail:
                if len(res) < MAX_calculate:
                    res.append((total_damage, total_score, tuple(teamid_list)))
                else:
                    break
        result = await self.arrange_fen_dao(list(set(res)), arrange=self.set_arrange)
        return result[:MAX_result]

    async def check_black_unit(self, unit_id):
        if len(set(unit_id) | set(self.black_units)) != len(unit_id + self.black_units):
            return False
        return True

    async def arrange_fen_dao(self, res, arrange):
        if arrange == '毛分':
            res.sort(key=lambda x: x[1], reverse=True)
        else:
            res.sort(key=lambda x: x[0], reverse=True)
        return res

    async def get_work_list(self, works, boss, stage):
        self.work_dict[boss] = []
        for black in self.black_work:
            if black in works:
                del works[black]
        for work_id in works:
            if await self.check_black_unit(works[work_id]["unit_id"]):
                damage = works[work_id]["damage"]
                score = damage*clanbattlework[boss][stage]["rate"]
                self.work_dict[boss].append(
                    (works[work_id]["unit_id"], damage, score, work_id))
        self.work_dict[boss] = await self.arrange_fen_dao(self.work_dict[boss], "毛分")

    async def fen_dao(self):
        # 默认不计算尾刀
        stage_list = []

        if len(self.all_boss) != 0:
            self.all_boss = [boss for boss in self.all_boss]

        if len(self.set_stage) == 1:
            stage = await letter2stageid(self.set_stage)
            stage_list = [stage, stage, stage]
        else:
            stage_list = [await letter2stageid(stages) for stages in list(self.set_stage)]
        if len(self.all_boss) > 0:
            for index, boss in enumerate(self.all_boss):
                works = await get_info(stage_list[index], boss=boss, type=self.set_type)
                await self.get_work_list(works[0], boss, stage)
            self.worklist = [self.work_dict[i] for i in self.all_boss]
            result = await self.get_result()
            return result

        elif len(self.all_boss) == 0 and len(stage_list) == 3:
            work_list = []
            works = await get_info(stage_list[0], type=self.set_type)
            for work in works:
                for work_id in work:
                    if work_id not in self.black_work and await self.check_black_unit(work[work_id]["unit_id"]):
                        damage = work[work_id]["damage"]
                        score = damage*clanbattlework[work_id[-3]][stage]["rate"]
                        work_list.append(
                            (work[work_id]["unit_id"], damage, score, work_id))
            # 排序，实际是毛伤，但我发现都能用
            work_list = await self.arrange_fen_dao(work_list, "毛分")
            self.worklist = [work_list, work_list, work_list]
            result = await self.get_result()
            return result
        else:
            return '输入错误'
