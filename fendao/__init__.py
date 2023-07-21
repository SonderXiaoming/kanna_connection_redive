import re
import json
import os
from nonebot import MessageSegment
from .create_img import team2pic
from ..util.text2img import image_draw
from ..util.tools import load_config, stage_dict, DATA_PATH
from .timeaxis import get_clanbattlework, get_info, type2chinese, workid2unitid, fendao, single_limit, Max_query
from hoshino import Service
from hoshino.util import pic2b64, filt_message
from hoshino.modules.priconne import chara
from hoshino.modules.priconne._pcr_data import CHARA_NAME

helpText1 = '''
查轴指令帮助：
查轴 [阶段] [类型] [BOSS] [作业序号]

阶段：ABCD，对应公会战的四个阶段
类型：T 代表自动刀，W 代表尾刀，S代表手动刀，填写多个代表都行，留空表示我全要
BOSS：1-5，对应公会战的一至五王
作业序号：花舞作业的序号，如‘A101’

指令示例：
查轴 A 
(查询一阶段的所有作业信息)
查轴 A101 
(详细查询特定作业)
查轴 A S
(查询一阶段的手动作业信息)
查轴 A 1 
(查询一阶段一王的所有作业信息)
查轴 A T 1 
(查询一阶段一王的AUTO刀作业信息)
查轴 A TS 1 
(查询一阶段一王的AUTO刀和手动刀作业信息)
注：指令示例中的空格均不可省略。

=============================================
数据来源于: https://www.caimogu.cc/gzlj.html
'''.strip()

helpText2 = '''
分刀指令帮助：
分刀 [阶段] [毛分/毛伤] (类型) (BOSS) 
阶段：ABCD，对应公会战的四个阶段，支持跨面，如‘CCD’，和后面boss一一对应，只填写一个默认全是这一阶段
类型：T 代表自动刀，W 代表尾刀，S代表手动刀，填写多个代表都行，留空表示我全要
BOSS：1-5，对应公会战的一至五王，可以‘123’或者‘12’,也可以‘555’,留空表示哪个boss无所谓
作业序号：列表中作业的序号

指令示例：
分刀 A 毛分
(查询一阶段的所有分刀可能，按分数排序)
分刀 A 毛分 123
(查询一阶段的1,2,3王所有分刀可能，按分数排序)
分刀 A 毛分 T 
(查询一阶段一王的AUTO刀所有分刀可能，按分数排序)
分刀 A 毛分 T 123
(查询一阶段的1,2,3王所有AUTO刀分刀可能，按分数排序)
自动分刀 毛伤
(上号根据你box自动查看你的box做出分刀，会顶号)
自动分刀 毛伤 T
(设置只考虑自动刀，同上)
注：指令示例中的空格均不可省略。

【添加角色黑名单】 + 角色名称
（支持多角色，例如春环环奈，无空格）
【添加角色缺失】 + 角色名称
（支持多角色，例如春环环奈，无空格）
【删除角色黑名单】 + 角色名称
（支持多角色，例如春环环奈，无空格）
【删除角色缺失】 + 角色名称
（支持多角色，例如春环环奈，无空格）
【删除作业黑名单】 + 作业id
【添加作业黑名单】 + 作业id
【查看角色缺失】（查看哪些角色缺失）
【查看角色黑名单】（查看哪些角色是黑名单）
【查看作业黑名单】（查看哪些作业是黑名单）
【清空角色缺失】（清空角色缺失）
【清空角色黑名单】（清空角色黑名单）
【清空作业黑名单】（清空作业黑名单）

=============================================
数据来源于: https://www.caimogu.cc/gzlj.html
'''.strip()

user_path = os.path.join(DATA_PATH, "fendao", "user")

sv = Service('分刀', enable_on_default=True, help_=f"{helpText1}\n\n{helpText2}")


async def set_unit_list(bot, ev, filename, delete=False):
    defen, unknown = chara.roster.parse_team(re.sub(r'[?？，,_]', '', ev.message.extract_plain_text()))
    config = await load_config(filename)
    if unknown:
        _, name, score = chara.guess_id(unknown)
        if score < 70 and not defen:
            return  # 忽略无关对话
        unknown = filt_message(unknown)
        msg = f'无法识别"{unknown}"' if score < 70 else f'无法识别"{unknown}" 您说的有{score}%可能是{name}'
        await bot.finish(ev, msg)

    if not defen and delete:
        config = []
    elif not defen:
        await bot.finish(ev, '请后面加角色名', at_sender=True)

    if not delete:
        msg = '设置成功'
        for id_ in defen:
            if id_ not in config:
                config.append(id_)
    else:
        msg = '删除成功'
        for id_ in defen:
            if id_ in config:
                config.remove(id_)

    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False)
    except:
        bot.finish(ev, '你好像没设置过角色黑名单or缺失')

    await bot.send(ev, msg)


async def set_work_list(bot, ev, filename, delete=False):
    defen = ev.message.extract_plain_text().upper()
    config = await load_config(filename)
    if not defen and delete:
        config = []
    elif not defen:
        await bot.finish(ev, '请后面加作业id', at_sender=True)

    if not delete:
        msg = '设置成功'
        if defen not in config:
            config.append(defen)
    else:
        msg = '删除成功'
        if defen in config:
            config.remove(defen)
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False)
    except:
        bot.finish(ev, '你好像没设置过作业黑名单')
    await bot.send(ev, msg)


def get_json_name(name1, name2):
    if name1 == "作业":
        json_name = 'work_black.json'
    elif name2 == "缺失":
        json_name = 'unit_loss.json'
    else:
        json_name = 'unit_black.json'
    return json_name


@sv.on_fullmatch('查轴帮助')
async def help1(bot, ev):
    await bot.send(ev, image_draw(helpText1))


@sv.on_fullmatch('分刀帮助')
async def help2(bot, ev):
    await bot.send(ev, image_draw(helpText2))


@sv.on_prefix('查轴')
async def query_timeaxis(bot, ev):
    content = ev.message.extract_plain_text().strip()
    msg = ""

    if re.match(r'^[A-Za-z][A-Za-z]?\d{3}$', content):
        work_id = content
        stage = work_id[0]
        try:
            result = await get_info(stage, work_id=work_id)
        except:
            await bot.send(ev, msg)

        info = result["info"]
        msg += f"{stage}面{work_id[-3]}王作业" + MessageSegment.image(pic2b64(await team2pic([(work_id, str(result["damage"]), result["unit_id"])])))

        for video in result["video_link"]:
            text = video["text"]
            url = video["url"]
            note = video["note"]
            msg += f"{info}\n相关视频：\n" + f"{text}\n{note}\n{url}" if note else f"{text}\n{url}"
        await bot.send(ev, msg)
        return

    stage = 'A'
    type = "STW"
    boss = "12345"

    args = content.split()
    for arg in args:
        if arg.upper() in stage_dict:
            stage = arg
        elif ''.join(sorted(arg.upper())) in type:  # 是否包含，先排序(忽略顺序)
            type = arg
        elif ''.join(sorted(arg.upper())) in boss:
            boss = arg
        else:
            await bot.send(ev, "出现无效参数，爬爬")
            return

    msg += f'{stage}面{await type2chinese(type)}作业'

    for single in boss:
        msg += f'\n{single}王作业：\n' + str(MessageSegment.image(pic2b64(await team2pic(
            [(work_id, str(work[work_id]["damage"]), work[work_id]["unit_id"]) for work in await get_info(stage, boss=single, type=type) for work_id in work], 
            max_query = single_limit if len(boss) > 1 else Max_query))))

    await bot.send(ev, msg)


@sv.on_prefix('分刀')
async def fen_dao(bot, ev):
    content = ev.message.extract_plain_text().strip()
    args = content.split()
    stage = 'A'
    type = "ST"
    arrange = "毛分"
    boss = "12345"
    
    
    for arg in args:
        if arg.upper()[0] in stage_dict:
            if len(arg) > 3:
                arg = arg[:3]
            stage = arg
        elif arg == "毛分" or arg == "毛伤":
            arrange = arg
        elif ''.join(sorted(arg.upper())) in "STW":  # 是否包含，先排序(忽略顺序)
            type = arg
        elif arg.isdigit():
            boss = "".join([number for number in arg if 1<=int(number)<=5])[:3]
        else:
            await bot.send(ev, "出现无效参数，爬爬")
            return
    
    msg = f'{stage}面'

    black_info = ''

    black_list = [await load_config(os.path.join(user_path, f'{ev.user_id}', f'{name}')) for name in ['unit_loss.json', 'unit_black.json', 'work_black.json']]

    if black_list[2]:
        black_info += f'作业黑名单：{str(black_list[2])[1:-1]}\n'

    if black_list[1]:
        black_info += f'角色黑名单：{str([CHARA_NAME[id][0] for id in black_list[1]])[1:-1]}\n'
    
    if black_list[0]:
        black_info += f'角色缺失：{str([CHARA_NAME[id][0] for id in black_list[0]])[1:-1]}\n'

    if black_info:
        await bot.send(ev, black_info)

    boss = () if len(boss) > 3 else boss
    msg += f"{boss}王分刀参考" if boss else "分刀参考"
    dao = fendao(stage, arrange, set_type=type, all_boss= boss)
    dao.set_black(*black_list)
    result = await dao.fen_dao()

    if len(result) == 0:
        await bot.send(ev, '无分刀作业，请检查角色设置和或更新作业网缓存')
        return

    for i, answer in enumerate(result):
        total = f"伤害总计：{answer[0]}W" if arrange == '毛伤' else f"分数总计：{answer[1]}W"
        msg += f"\n第{i+1}种方案，{total}\n{MessageSegment.image(pic2b64(await team2pic(await workid2unitid(answer[2]), borrow=True, unit_loss=black_list[0])))}"
    
    await bot.send(ev, msg)

@sv.on_prefix('添加角色缺失')
@sv.on_prefix('添加作业黑名单')
@sv.on_prefix('添加角色黑名单')
async def set_black(bot, ev):
    name1: str = ev.prefix[2:4]
    name2: str = ev.prefix[4:6]
    user_id = ev.user_id
    os.makedirs(os.path.join(user_path, f'{user_id}'), exist_ok= True)
    filename = os.path.join(user_path, f'{user_id}', get_json_name(name1, name2))
    if name1 == "作业":
        await set_work_list(bot, ev, filename)
    else:
        await set_unit_list(bot, ev, filename)


@sv.on_prefix('删除角色黑名单')
@sv.on_prefix('删除角色缺失')
@sv.on_prefix('删除作业黑名单')
async def delete_black(bot, ev):
    name1: str = ev.prefix[2:4]
    name2: str = ev.prefix[4:6]
    if (ev.message.extract_plain_text()):
        filename = os.path.join(user_path, f'{ev.user_id}', get_json_name(name1, name2))
        if name1 == "作业":
            await set_work_list(bot, ev, filename, delete=True)
        else:
            await set_unit_list(bot, ev, filename, delete=True)
    else:
        await bot.send(ev, '请后面加作业id/角色名', at_sender=True)


@sv.on_rex(r'^清空(角色|作业)(缺失|黑名单)$')
async def clean_black(bot, ev):
    match = ev["match"]
    filename = os.path.join(user_path, f'{ev.user_id}', get_json_name(match.group(1), match.group(2)))
    if match.group(1) == "作业":
        await set_work_list(bot, ev, filename, delete=True)
    else:
        await set_unit_list(bot, ev, filename, delete=True)


@sv.on_rex(r'^查看(角色|作业)(缺失|黑名单)$')
async def query_black(bot, ev):
    match = ev["match"]
    if config:= await load_config(os.path.join(user_path, f'{ev.user_id}', get_json_name(match.group(1), match.group(2)))):
        await bot.send(ev, str(config)[1:-1])
    else:
        await bot.send(ev, f"你没有设置过{match.group(1)}{match.group(2)}")


@sv.on_fullmatch('更新作业网缓存')
async def renew_worklist(bot, ev):
    if get_clanbattlework():
        await bot.send(ev, '刷新成功')
    else:
        await bot.send(ev, '刷新失败，可能是网络问题或者作业网此时没作业')


@sv.scheduled_job('interval', minutes=60)
async def renew_worklist_auto():
    await get_clanbattlework()
