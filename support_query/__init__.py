import json
import re
import os
import time
from nonebot import get_bot
from .create_img import general_img
from .accurateassis import accurateassis
from ..login import query
from ..util.text2img import image_draw
from ..util.tools import load_config, DATA_PATH
from ..clanbattle import clanbattle_info
from ..clanbattle.model import ClanBattle
from hoshino import Service, priv
from hoshino.typing import CQEvent
from hoshino.util import pic2b64
from hoshino.typing import NoticeSession, MessageSegment
from hoshino.modules.priconne._pcr_data import CHARA_NAME
from hoshino.modules.convert2img.convert2img import grid2imgb64

help_text = '''
【(上|挂|换|更换|切换|修改)(地下城|公会|公会战|会战|工会战|工会|露娜|露娜塔|关卡|活动|深域|深渊)(支援|助战)XX】XX为角色名（支持常用外号），机器人会自动找到并替换助战，并返回该角色的详细信息
========================================================
【刷新box缓存】会顶号，请注意，机器人自动上号记录你的box
【box查询+角色名字】（@别人可以查别人，角色名输入【所有】则都查）
【绑定本群公会】将自己绑定在这个群
【删除本群公会绑定】将自己踢出公会（管理可以at别人实现踢人效果）
【公会box查询+角色名字】查询绑定公会的玩家的box，不支持输入所有（卡不死你）
【刷新助战缓存】会顶号，请注意，机器人自动上号记录公会助战
【精确助战+角色名字】（角色名输入【所有】则都查）
【绑定账号+账号+密码】加号为空格(加好友私聊)
'''.strip()

sv = Service(
    name="精准助战",  # 功能名
    visible=True,  # 可见性
    enable_on_default=True,  # 默认启用
    help_=help_text,  # 帮助说明
)

class SupportMonitor(object):
    def __init__(self):
        self.qid = 0
        self.nickname = ""
        self.monitor_client = None
    
    async def add_monitor(self, qid, group_id, bot):
        monitor_client, nickname = await self.user_login(qid, group_id, bot)
        if monitor_client:
            self.qid = qid # 助战人的qq号
            self.nickname = nickname # 助战人的昵称
            self.monitor_client = monitor_client # 助战人的登录实例
            return self.nickname
        else:
            return None

    async def user_login(self, qid, group_id, bot):
        acccountinfo = await load_config(os.path.join(DATA_PATH, 'account', f'{qid}.json'))
        if acccountinfo != []:
            monitor_client = await query(acccountinfo)
            user_info = await bot.get_group_member_info(group_id = group_id, user_id = qid)
            nickname = user_info["card"] or user_info["nickname"]
            return monitor_client, nickname

info_path = os.path.join(DATA_PATH, "support_query")

async def get_support_list(info, acccountinfo, qq_id):
    client = await query(acccountinfo)
    load_index = await client.callapi('/load/index', {'carrier': 'OPPO'})
    home_index = await client.callapi('/home/index', {'message_id': 1, 'tips_id_list': [], 'is_first': 1, 'gold_history': 0})
    if info == 'support_query':
        clan_id = home_index['user_clan']['clan_id']
        support_list = await client.callapi('/clan_battle/support_unit_list_2', {"clan_id": clan_id})
        return support_list
    if info == 'self_query':
        return load_index

def get_info(file, name, isSelf = False):
    try:
        A = accurateassis(file) # 输入json的路径
    except:
        return '没有缓存,请先根据指令进行缓存', False
    check = A.translatename2id(name) # 输入要查询角色的名称
    if check:
        return check, False
    all_info = A.serchassis() if not isSelf else A.user_card()
    if len(all_info) == 0:
        return '没有找到该角色', False
    return all_info, True

@sv.on_fullmatch('查box帮助', '助战帮助')
async def query_help(bot, ev: CQEvent):
    img = image_draw(help_text)
    await bot.send(ev, img)

@sv.on_prefix('精准助战','精确助战')
async def query_clanbattle_support(bot, ev: CQEvent):
    group_id = ev.group_id
    file = os.path.join(info_path,'group',f'{group_id}','support.json')
    name = ev.message.extract_plain_text().strip()
    all_info,check = get_info(file,name)
    if not check:
        await bot.send(ev, all_info)
        return
    images = await general_img(all_info)
    result = pic2b64(images)
    msg = str(MessageSegment.image(result))
    await bot.send(ev, msg)

@sv.on_fullmatch('刷新助战缓存')
async def create_support_cache(bot, ev: CQEvent):
    qq_id = ev.user_id
    acccountinfo = await load_config(os.path.join(DATA_PATH, 'account', f'{qq_id}.json'))
    if acccountinfo != []:
        support_list = await get_support_list('support_query', acccountinfo, qq_id)
        if "server_error" in support_list:
            await bot.send(ev, "可能现在不是会战的时候或者网络异常")
            return
        group_id = ev.group_id
        os.makedirs(os.path.join(info_path, 'group', f'{group_id}'), exist_ok=True)
        with open(os.path.join(info_path,'group',f'{group_id}','support.json'), 'w', encoding='utf-8') as f:
            json.dump(support_list, f, ensure_ascii=False)
        await bot.send(ev, "刷新成功")
    else:
        await bot.send(ev, "你没有绑定过账号")

# 刷新自己的助战列表，显示自己指定助战的详细信息
async def refreshAndShowSupportInfo(bot, ev, client, cname, qq_id):
    # 刷新自己的box缓存，写入文件
    index_infos = await client.callapi('/load/index', {'carrier': 'OPPO'})
    if "server_error" in index_infos:
        await bot.send(ev, "网络异常")
        return
    print(index_infos)

    # 如果当前账号没有对应路径和文件，创建文件夹和文件
    try:
        os.makedirs(os.path.join(info_path, 'user', f'{qq_id}'), exist_ok=True)
        with open(os.path.join(info_path, 'user', f'{qq_id}', 'self.json'), 'w', encoding='utf-8') as f:
            json.dump(index_infos, f, ensure_ascii=False)
    except:
        await bot.send(ev, "无法将box信息写入文件！")
        raise
    
    # 读取文件，找到目标角色信息
    all_info, check = get_info(os.path.join(info_path, 'user', f'{qq_id}', 'self.json'), cname, True)
    if not check:
        await bot.send(ev, all_info)
        return
    
    # 绘制图片输出
    try:
        images = await general_img(all_info)
        result = pic2b64(images)
        msg = str(MessageSegment.image(result))
        await bot.send(ev, msg)
    except:
        await bot.send(ev, "生成助战角色配置图片失败！")
        raise


@sv.on_rex(r"^(上|挂|换|切换|更换|修改)(地下城|公会|公会战|会战|工会战|工会|露娜|露娜塔|关卡|活动|深域|深渊)?(支援|助战) ?(\S+)$")
async def change_support(bot, ev: CQEvent):
    # 切割指令获取目标角色
    match = ev['match']
    scene = match.group(2) if match.group(2) else "公会战"
    target_chara = match.group(4).strip()
    chara_id = 0

    # 从角色 id-外号 映射表中查找目标角色id
    for CHARA_ID in CHARA_NAME:
        if target_chara in CHARA_NAME[CHARA_ID]:
            print(target_chara)
            chara_id = CHARA_ID
            chara_name = CHARA_NAME[CHARA_ID][0]
            await bot.send(ev, f'已确定您说的是{chara_name}')  # 根据外号识别出角色真名和id
            break

    # 无法根据外号识别角色
    if chara_id == 0:
        await bot.send(ev, f'未找到{target_chara}！请使用其他名称重试')  
        return

    # 关卡助战位 占位元素
    friend_units = [
        {'unit_id': 100000, 'position': 1, 'support_start_time': 0, 'clan_support_count': 1},
        {'unit_id': 100000, 'position': 2, 'support_start_time': 0, 'clan_support_count': 0}
    ]
    
    # 地下城助战位 占位元素
    dungeon_units = [
        {'unit_id': 100000, 'position': 1, 'support_start_time': 0, 'clan_support_count': 1},
        {'unit_id': 100000, 'position': 2, 'support_start_time': 0, 'clan_support_count': 0}
    ]
    
    # 会战助战位 占位元素
    clan_units = [
        {'unit_id': 100000, 'position': 3, 'support_start_time': 0, 'clan_support_count': 1},
        {'unit_id': 100000, 'position': 4, 'support_start_time': 0, 'clan_support_count': 0}
    ]

    # 获取指定的成员的信息
    group_id = ev.group_id
    isClanBattle = scene == "公会战" or scene == "会战" or scene == "工会战" or scene == "工会" or scene == "公会"
    if isClanBattle:
        if len(ev.message) == 3 and ev.message[0].type == 'text' and ev.message[1].type == 'at':
            qq_id = int(ev.message[1].data['qq'])
        else:
            clan_info: ClanBattle = clanbattle_info[group_id]
            qq_id = clan_info.qq_id
    else:
        if len(ev.message) == 3 and ev.message[0].type == 'text' and ev.message[1].type == 'at':
            qq_id = int(ev.message[1].data['qq'])
        else:
            qq_id = ev.user_id
    user_info = await bot.get_group_member_info(group_id = group_id, user_id = qq_id)
    nickname = user_info["card"] or user_info["nickname"]
    await bot.send(ev, f'正在{nickname if isClanBattle else "您"}的BOX中寻找该角色...')
    # 登录账号
    acccount_info = await load_config(os.path.join(DATA_PATH, 'account', f'{qq_id}.json'))

    if acccount_info != []:
        client = await query(acccount_info)
        # 调API获取助战位置信息
        # 神坑，pcr竟然将地下城助战和公会助战放在一个数组里，没挂助战的位置还获取不到信息
        all_support_units = await client.callapi('/support_unit/get_setting', {})
        clan_dungeon_support_units = all_support_units['clan_support_units']
        friend_support_units = all_support_units['friend_support_units']
        all_support_units = all_support_units['clan_support_units'] + all_support_units['friend_support_units']
        # 过滤一遍只留下公会助战
        for unit in clan_dungeon_support_units:
            if unit['position'] in (1, 2):
                index = unit['position'] - 1
                dungeon_units[index] = unit

            if unit['position'] in (3, 4):
                index = unit['position'] - 3
                clan_units[index] = unit

        for unit in friend_support_units:
            if unit['position'] in (1, 2):
                index = unit['position'] - 1
                friend_units[index] = unit
        
        # 检查角色是否已在助战中，当助战角色被挂到其他场景的助战位时也提示操作失败
        for unit in all_support_units:
            unit_id = int(str(unit['unit_id'])[:-2])
            if chara_id == unit_id:
                if 'friend_support_reward' in unit:
                    pos = "关卡&活动"
                else:
                    if unit['position'] in (1, 2):
                        pos = "地下城"
                    else:
                        pos = "公会&露娜塔"
                await bot.send(ev, f'操作失败，角色已经在{pos}助战中!')
                return
        
        # 遍历两个公会助战位，尝试挂角色
        target_units = []
        support_type = 1
        position_offset = 1
        units_name = ""
        if scene == '地下城':
            target_units = dungeon_units
            units_name = "地下城"
        elif scene == '公会' or scene == '工会' or scene == '工会战' or scene == '公会战':
            target_units = clan_units
            position_offset = 3
            units_name = "公会战"
        elif scene == '露娜' or scene == '露娜塔':
            target_units = clan_units
            position_offset = 3
            units_name = "露娜塔"
        elif scene == '关卡' or scene == '活动' or scene == '深域' or scene == '深渊':
            target_units = friend_units
            support_type = 2
            units_name = "关卡&活动"
        
        for index, unit in enumerate(target_units):
            # 检查冷却时间
            unit_time = unit['support_start_time']
            now = time.time()
            diff = int(now - unit_time)
            if diff > 1800:
                unit_id = int(str(chara_id) + '01')
                try:
                    # 卸下原角色
                    await client.callapi('/support_unit/change_setting', {
                        'support_type': support_type,
                        'position': index + position_offset,
                        'action': 2,
                        'unit_id': unit_id
                    })
                    time.sleep(3)
                    # index_infos = await client.callapi('/load/index', {'carrier': 'OPPO'})
                    # if "server_error" in index_infos:
                    #     await bot.send(ev, "网络异常")
                    # user_ex_equip = index_infos['user_ex_equip'] or []
                    # if user_ex_equip:
                    #     for ex_equip in user_ex_equip:
                    #         if ex_equip['ex_equipment_id'] == 10000 and ex_equip['enhancement_pt'] == 6000 and ex_equip['rank'] == 2:
                    #             target_weapon = ex_equip['serial_id']
                    # time.sleep(3)
                    # 挂上新角色
                    await client.callapi('/support_unit/change_setting', {
                        'support_type': support_type,
                        'position': index + position_offset,
                        'action': 1,
                        'unit_id': unit_id
                    })
                    msg = f'已将{nickname}的{chara_name}挂至{units_name}{index + 1}号助战位中'
                    await bot.send(ev, msg)   
                except:
                    await bot.send(ev, '操作失败')
                    pass
                
                await refreshAndShowSupportInfo(bot, ev, client, chara_name, qq_id) # 图片展示挂上去的助战的数据
                return

        await bot.send(ev,'操作失败！可能是两个助战位都未超过30分钟')


@sv.on_prefix('box查询')
async def query_clanbattle_support(bot, ev: CQEvent):
    qq_id = ev.user_id
    name = ev.message.extract_plain_text().strip()
    content = ev.raw_message
    if '[CQ:at,qq=' in content:
        qq_id = re.findall(r"CQ:at,qq=([0-9]+)",content)[0]
    all_info,check = get_info(os.path.join(info_path, 'user', f'{qq_id}','self.json'),name,True)
    if not check:
        await bot.send(ev, all_info)
        return
    images = await general_img(all_info)
    result = pic2b64(images)
    msg = str(MessageSegment.image(result))
    await bot.send(ev, msg)

@sv.on_fullmatch('刷新box缓存')
async def create_self_cache(bot, ev: CQEvent):
    qq_id = ev.user_id
    os.makedirs(os.path.join(info_path, 'user', f'{qq_id}'), exist_ok=True)
    acccountinfo = await load_config(os.path.join(DATA_PATH, 'account', f'{qq_id}.json'))
    if acccountinfo != []:
        support_list = await get_support_list('self_query', acccountinfo, qq_id)
        if "server_error" in support_list:
            await bot.send(ev, "网络异常")
            return
        with open(os.path.join(info_path, 'user', f'{qq_id}','self.json'), 'w', encoding='utf-8') as f:
            json.dump(support_list, f, ensure_ascii=False)
        await bot.send(ev, "刷新成功")
    else:
        await bot.send(ev, "你没有绑定过账号")

@sv.on_fullmatch('绑定本群公会')
async def create_self_cache(bot, ev: CQEvent):
    qq_id = ev.user_id
    group_id = ev.group_id
    acccountinfo = await load_config(os.path.join(DATA_PATH, 'account', f'{qq_id}.json'))
    if acccountinfo != []:
        os.makedirs(os.path.join(info_path, 'group', f'{group_id}'),exist_ok=True)
        file = os.path.join(info_path, 'group', f'{group_id}','player.json')
        player_list = await load_config(file)
        if qq_id not in player_list:
            player_list.append(qq_id)
        with open(file, 'w', encoding='utf-8') as f:
            json.dump(player_list, f, ensure_ascii=False)
        await bot.send(ev, "绑定本群公会成功")
    else:
        await bot.send(ev, "你没有绑定过账号")

@sv.on_prefix('删除本群公会绑定')
async def create_self_cache(bot, ev: CQEvent):
    if len(ev.message) == 1 and ev.message[0].type == 'text' and not ev.message[0].data['text']:
        qq_id = ev.user_id
    elif ev.message[0].type == 'at':
        if not priv.check_priv(ev, priv.ADMIN):
            msg = '很抱歉您没有权限进行此操作，该操作仅管理员'
            await bot.send(ev, msg)
            return
        qq_id = int(ev.message[0].data['qq'])
    group_id = ev.group_id
    os.makedirs(os.path.join(info_path, 'group', f'{group_id}'),exist_ok=True)
    file = os.path.join(info_path, 'group', f'{group_id}','player.json')
    player_list = await load_config(file)
    if qq_id in player_list:
        player_list.remove(qq_id)
    with open(file, 'w', encoding='utf-8') as f:
        json.dump(player_list, f, ensure_ascii=False)
    await bot.send(ev, "删除本群公会绑定成功")

@sv.on_prefix('公会box查询')
async def query_clanbattle_support(bot, ev: CQEvent):
    clan_info = []
    name = ev.message.extract_plain_text().strip()
    if name == '所有':
        await bot.send(ev, '爬爬，你想累死我')
        return
    group_id = ev.group_id
    player_list = await load_config(os.path.join(info_path, 'group', f'{group_id}','player.json'))
    if player_list != []:
        for qq_id in player_list:
            file = os.path.join(info_path, 'user', f'{qq_id}','self.json')
            all_info,check = get_info(file,name,True)
            if check:
                clan_info += all_info
    if len(clan_info) == 0:
        await bot.send(ev, '没有找到该角色')
        return
    images = await general_img(clan_info)
    result = pic2b64(images)
    msg = str(MessageSegment.image(result))
    await bot.send(ev, msg)

@sv.on_fullmatch('生成pcr简介')
async def query_clanbattle_support(bot, ev: CQEvent):
    qq_id = ev.user_id
    try:
        A = accurateassis(os.path.join(info_path, 'user', f'{qq_id}','self.json'))
    except:
        await bot.send(ev, '你没有缓存')
        return
    title, info = A.user_info()
    img = grid2imgb64(info,title)
    await bot.send(ev, img)

@sv.on_notice('group_decrease')
async def leave_notice(session: NoticeSession):
    uid = str(session.ctx['user_id'])
    gid = str(session.ctx['group_id'])
    bot = get_bot()
    os.makedirs(os.path.join(info_path, 'group', f'{gid}'), exist_ok=True)
    file = os.path.join(info_path, 'group', f'{gid}','player.json')
    player_list = await load_config(file)
    if uid in player_list:
        player_list.remove(uid)
        with open(file, 'w', encoding='utf-8') as f:
            json.dump(player_list, f, ensure_ascii=False)
        await bot.send_group_msg(group_id = int(gid),message = f'{uid}退群了，已自动删除其绑定在本群的公会绑定')
