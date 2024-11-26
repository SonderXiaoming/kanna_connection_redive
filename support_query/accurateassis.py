import json
import re
from hoshino.util import filt_message
from hoshino.modules.priconne import chara
from hoshino.modules.priconne._pcr_data import CHARA_NAME

equip_dict = {
    "sliver": {0: 0, 1: 30, 2: 80, 3: 160},  # 4
    "golden": {0: 0, 1: 60, 2: 160, 3: 360, 4: 700, 5: 1200},  # 7
    "purple": {0: 0, 1: 100, 2: 260, 3: 540, 4: 1020, 5: 1800},  # 11
}  # 装备经验

unquie_equip = [
    (0, 10),
    (90, 15),
    (240, 25),
    (490, 40),
    (890, 50),
    (1390, 60),
    (1990, 75),
    (2740, 100),
]

ex_equip = [
    (150, 400, 800),
    (150, 400, 800, 1300),
    (800, 1800, 3000, 4400, 6000),  # 后面一样了
]

bonus_dict = {
    "atk": "物理攻击力",
    "crt": "物理暴击率",
    "matk": "魔法攻击力",
    "mcrt": "魔法暴击率",
    "erec": "TP自动回复",
    "hp": "血量",
    "def": "物理防御力",
    "mdef": "魔法防御力",
    "hrec_rate": "回复量上升",
    "erec_rate": "TP上升",
}


def get_ex_equip_max_star(equipment_id: int) -> int:
    rank = equipment_id % 1000 // 100
    return rank + 2 if rank < 3 else 5


def ex_equip_exp2star(exp: int, equipment_id: int) -> int:
    if not equipment_id:
        return 0
    rank = equipment_id % 1000 // 100
    rank = 2 if rank > 3 else rank - 1
    exp_list = ex_equip[rank]
    return next(
        (i for i, star_exp in enumerate(exp_list, 1) if exp < star_exp),
        len(exp_list),
    )


class accurateassis(object):
    def __init__(self, assisjson_path):
        self.assisjson_path = assisjson_path
        with open(self.assisjson_path, "r", encoding="utf-8") as f:
            self.assisjson = json.load(f)

    def translatename2id(self, name):
        if name == "所有":
            self.transresult_id = -1
            return ""
        defen = re.sub(r"[?？，,_]", "", name)
        defen, unknown = chara.roster.parse_team(defen)
        if unknown:
            _, name, score = chara.guess_id(unknown)
            if score < 70 and not defen:
                return  # 忽略无关对话
            unknown = filt_message(unknown)
            return (
                f'无法识别"{unknown}"'
                if score < 70
                else f'无法识别"{unknown}" 您说的有{score}%可能是{name}'
            )
        else:
            self.transresult_id = defen
            return ""

    def equip_exp2star(self, num, exp, rank):
        if num == 0:
            return "未装备"
        elif rank < 4:  # 没星
            return "已装备"
        elif 4 <= rank < 7:  # 3星
            return next(
                (
                    i
                    for i in range(3)
                    if equip_dict["sliver"][i] <= exp < equip_dict["sliver"][i + 1]
                ),
                3,
            )
        elif 7 <= rank < 11:
            for i in range(5):
                if equip_dict["golden"][i] <= exp < equip_dict["golden"][i + 1]:
                    return i
        elif rank > 11:
            for i in range(5):
                if equip_dict["purple"][i] <= exp < equip_dict["purple"][i + 1]:
                    return i
        return 5  # FIXME：红装，绿装呢

    def unique_exp2level(self, num, exp):
        if num == 0:
            return "未装备"
        elif exp <= unquie_equip[0][0]:  # z专武初始1级
            level = 1 + (exp / unquie_equip[0][1])
        elif exp <= unquie_equip[-1][0]:  # 一开始毫无规律，打表
            for index, stage in enumerate(unquie_equip):
                low = stage[0]
                if low < exp <= unquie_equip[index + 1][0]:
                    level = (exp - low) / stage[1] + index * 10
        else:  # 后面每升10级，升一级所需经验值+25，10级为一组，等差数列
            exp -= unquie_equip[-1][0]
            n = int(
                (-7 + (49 + 4 * exp / 125) ** (1 / 2)) / 2
            )  # 等差公式求出经验值多余多少个10级，向下取整
            if n <= 7:
                level = (
                    70 + 10 * n + (exp - 875 * n - 125 * (n) ** 2) / (75 + 25 * n)
                )  # 算出多多少级
            else:  # 每次需要250经验值值时不再增长
                n = 7
                level = 70 + 10 * n + (exp - 875 * n - 125 * (n) ** 2) / 250
        return int(level)

    def letter2chinese(self, bonus_param):
        for letter in list(bonus_param):
            if letter in bonus_dict:
                bonus_param[bonus_dict[letter]] = bonus_param[letter]
                del bonus_param[letter]
        return str(bonus_param).replace("'", "")[1:-1]

    def general_info(self, units):
        all_info = []
        for it in units:
            info = {}
            try:
                info["player"] = it["owner_name"]  # 玩家名字
                it = it["unit_data"]
            except:
                info["player"] = self.user_name

            id = it["id"] // 100
            if self.transresult_id == -1 or id in self.transresult_id:
                equip_slots = []
                rank = it["promotion_level"]
                for equip_id in range(6):
                    equip = it["equip_slot"][equip_id]["is_slot"]
                    equip_rank = it["equip_slot"][equip_id]["enhancement_pt"]
                    equip_star = self.equip_exp2star(equip, equip_rank, rank)
                    equip_slots.append(equip_star)

                ex_equip_slots = []
                for cb_ex_equip in range(3):
                    try:
                        ex_equip, ex_equip_rank = self.unit_ex_equip_dict.get(
                            it["cb_ex_equip_slot"][cb_ex_equip]["serial_id"], (0, 0)
                        )

                    except:
                        ex_equip = it["cb_ex_equip_slot"][cb_ex_equip][
                            "ex_equipment_id"
                        ]
                        ex_equip_rank = it["cb_ex_equip_slot"][cb_ex_equip][
                            "enhancement_pt"
                        ]

                    ex_equip_star = ex_equip_exp2star(ex_equip_rank, ex_equip)
                    ex_equip_slots.append((ex_equip, ex_equip_star))

                star = (
                    (it["battle_rarity"], True)
                    if it["battle_rarity"] != 0
                    else (it["unit_rarity"], False)
                )

                try:
                    unique_level = self.unique_exp2level(
                        it["unique_equip_slot"][0]["is_slot"],
                        it["unique_equip_slot"][0]["enhancement_pt"],
                    )
                except:
                    unique_level = "未装备"

                try:
                    info["skill"] = (
                        str(it["union_burst"][0]["skill_level"]),
                        str(it["main_skill"][0]["skill_level"]),
                        str(it["main_skill"][1]["skill_level"]),
                        str(it["ex_skill"][0]["skill_level"]),
                    )  # "技能UB,1,2,Ex
                except:
                    info["skill"] = ("1", "1", "0", "1")  # "技能UB,1,2,Ex

                try:
                    info["special_attribute"] = self.letter2chinese(it["bonus_param"])
                except:
                    info["special_attribute"] = f"好感等级{self.love_dict[id]}"

                info["unique_equip_slot"] = str(unique_level)
                info["ex_equip"] = ex_equip_slots
                info["star"] = star  # 星级，是否调星
                info["level"] = str(it["unit_level"])  # 等级
                info["rank"] = str(rank)  # rank
                info["equip"] = equip_slots  # 武器穿戴情况
                info["id"] = id
                all_info.append(info)
        return all_info

    def serchassis(self):
        support_unit_list = self.assisjson["support_unit_list"]
        all_info = self.general_info(support_unit_list)
        all_info.sort(key=lambda x: x["id"])
        return all_info

    def get_item(self, id):
        item_list = self.assisjson["item_list"]
        for item in item_list:
            if item["id"] == id:
                return item["stock"]
        item_list = self.assisjson["user_equip"]
        return next((item["stock"] for item in item_list if item["id"] == id), -1)

    def user_card(self):
        unit_list = self.assisjson["unit_list"]
        self.user_name = self.assisjson["user_info"]["user_name"]
        love_list = self.assisjson["user_chara_info"]
        self.love_dict = {data["chara_id"]: data["love_level"] for data in love_list}
        self.unit_ex_equip_dict = {
            equip["serial_id"]: (equip["ex_equipment_id"], equip["enhancement_pt"])
            for equip in self.assisjson["user_ex_equip"]
        }
        all_info = self.general_info(unit_list)
        all_info.sort(key=lambda x: int(x["level"]), reverse=True)
        return all_info

    def user_info(self):
        userinfo = self.assisjson
        title = ["名称", userinfo["user_info"]["user_name"]]  # 名称
        info = [
            ["等级", userinfo["user_info"]["team_level"]],
            [
                "头像",
                CHARA_NAME[userinfo["user_info"]["favorite_unit_id"] // 100][0],
            ],
            [
                "宝石",
                userinfo["user_jewel"]["free_jewel"]
                + userinfo["user_jewel"]["paid_jewel"],
            ],
            [
                "马娜",
                userinfo["user_gold"]["gold_id_free"]
                + userinfo["user_gold"]["gold_id_pay"],
            ],
            ["地下城币", self.get_item(90002)],
            ["竞技场币", self.get_item(90003)],
            ["公主竞技场币", self.get_item(90004)],
            ["母猪石", self.get_item(90005)],
            ["会战币", self.get_item(90006)],
            ["大师币", self.get_item(90008)],
            ["星球杯", self.get_item(25001)],
            ["心碎", self.get_item(140001)],
        ]
        return title, info
