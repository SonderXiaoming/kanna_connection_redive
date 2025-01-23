import json
import re
import os
import time
from nonebot import get_bot
from .create_img import general_img
from .accurateassis import accurateassis
from ..login import query
from ..util.text2img import image_draw
from ..util.tools import load_config, DATA_PATH, check_client
from hoshino import Service,priv
from hoshino.typing import CQEvent
from hoshino.util import pic2b64
from hoshino.typing import NoticeSession,MessageSegment
from hoshino.modules.priconne._pcr_data import CHARA_NAME
from hoshino.modules.convert2img.convert2img import grid2imgb64

help_text = '''
【开启修改助战】机器人登录账号，准备接收修改助战指令（可以与出刀监控登录的账号不同）
【查助战人】查询现在是登录了哪一位群友的账号
【修改助战XX】XX为角色名（支持常用外号），机器人会自动找到并替换助战，并返回该角色的详细信息
【关闭修改助战】手动关闭此功能，号主上号时也会自动顶号退出
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

monitor_groups = dict()

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

def get_info(file,name,isself=False):
    try:
        A = accurateassis(file) #输入json的路径
    except:
        return '没有缓存,请先根据指令进行缓存',False
    check = A.translatename2id(name) #输入要查询角色的名称
    if check:
        return check,False
    all_info = A.serchassis() if not isself else A.user_card()
    if len(all_info) == 0:
        return '没有找到该角色',False
    return all_info, True

@sv.on_fullmatch('开启修改助战')
async def record_monitor(bot, ev: CQEvent):
    user_id = ev.user_id
    group_id = ev.group_id
    supmon = SupportMonitor()
    nickname = await supmon.add_monitor(user_id, group_id, bot)
    if nickname:
        monitor_groups[group_id] = supmon
        msg = f'已记录群{group_id}的监控人【{nickname}】，可使用【修改助战XX】来切换此人助战'
        await bot.send(ev, msg)
    else:
        await bot.send(ev, "你没有绑定过账号")

@sv.on_fullmatch('关闭修改助战')
async def delete_monitor(bot, ev: CQEvent):
    user_id = ev.user_id
    group_id = ev.group_id
    if monitor_groups[group_id]:
        supmon = monitor_groups[group_id]
        if supmon.qid == user_id:
            del monitor_groups[group_id]
            await bot.send(ev, "已关闭【修改助战】功能")
        else:
            await bot.send(ev, f'你无权关闭{supmon.nickname}的助战！你可以联系{supmon.nickname}关闭或直接发送【开启修改助战】将此功能切换到你的账号上')
    else:
        await bot.send(ev, "【修改助战】功能未开启")

@sv.on_fullmatch('查助战人')
async def search_monitor(bot, ev: CQEvent):
    group_id = ev.group_id
    try:
        supmon = monitor_groups[group_id]
        await bot.send(ev, f'当前助战人为：{supmon.nickname}({supmon.qid})')
    except:
        await bot.send(ev, "没有助战人，请发送【开启修改助战】，允许群友修改你的助战列表")
        pass

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
        support_list = await get_support_list('support_query',acccountinfo,qq_id)
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
async def refreshAndShowZZ(bot, ev, cname):
    group_id = ev.group_id
    supmon = monitor_groups[group_id]
    qid = supmon.qid
    monitor_client = supmon.monitor_client
    # 刷新自己的box缓存，写入文件
    support_list = await monitor_client.callapi('/load/index', {'carrier': 'OPPO'})
    if "server_error" in support_list:
        await bot.send(ev, "网络异常")
        return
    with open(os.path.join(info_path, 'user', f'{qid}','self.json'), 'w', encoding='utf-8') as f:
        json.dump(support_list, f, ensure_ascii=False)
    
    # 读取文件，找到目标角色信息
    all_info, check = get_info(os.path.join(info_path, 'user', f'{qid}', 'self.json'), cname, True)
    if not check:
        await bot.send(ev, all_info)
        return
    
    # 绘制图片输出
    images = await general_img(all_info)
    result = pic2b64(images)
    msg = str(MessageSegment.image(result))
    await bot.send(ev, msg)

@sv.on_prefix(f'修改助战')
async def clan_uni(bot, ev: CQEvent):
    # 获取群监控
    group_id = ev.group_id
    supmon = monitor_groups[group_id]
    
    # 异常处理
    if not supmon:
        await bot.send(ev, '没有助战人，请发送【开启修改助战】，允许群友修改你的助战列表')
        return
    if not await check_client(supmon.monitor_client):
        del monitor_groups[group_id]
        await bot.send(ev, '【修改助战】功能已被顶号退出')
        return

    monitor_client = supmon.monitor_client # 获取助战登录实例
    target_chara = ev.message.extract_plain_text().strip() # 切割指令获取目标角色
    chara_id = 0
    # 从角色 id-外号 映射表中查找目标角色id
    for CHARA_ID in CHARA_NAME:
        if target_chara in CHARA_NAME[CHARA_ID]:
            print(target_chara)
            chara_id = CHARA_ID
            chara_name = CHARA_NAME[CHARA_ID][0]
            await bot.send(ev, f'已找到{chara_name}，正在尝试挂至助战...')  #角色存在
            break

    # 助战位信息占位元素
    units = [
                {'unit_id': 100000, 'position': 3, 'support_start_time': 0, 'clan_support_count': 1},
                {'unit_id': 100000, 'position': 4, 'support_start_time': 0, 'clan_support_count': 0}
            ]
    # 调API获取助战位置信息
    # 神坑，pcr竟然将地下城助战和公会助战放在一个数组里，没挂助战的位置还获取不到信息
    prof = await monitor_client.callapi('/support_unit/get_setting', {})
    large_units = prof['clan_support_units']
    # 过滤一遍只留下公会助战
    for unit in large_units:
        if unit['position'] in (3, 4):
            index = unit['position'] - 3
            units[index] = unit
    
    # 检查角色是否已在助战中
    # todo：这里不严谨，当助战角色被挂到其他场景的助战位时也应该提示操作失败
    for unit in units:
        unit_id = int(str(unit['unit_id'])[:-2])
        if chara_id == unit_id:
            await bot.send(ev, f'操作失败，角色已经在助战中!')
            return
    
    # 遍历两个公会助战位，尝试挂角色
    for index, unit in enumerate(units):
        # 检查冷却时间
        unit_time = unit['support_start_time']
        now = time.time()
        diff = int(now - unit_time)
        print(diff)
        if int(diff) > 1800:
            unit_id = int(str(chara_id) + '01')
            try:
                # 卸下原角色
                await monitor_client.callapi('/support_unit/change_setting', {'support_type': 1, 'position': index + 3, 'action': 2, 'unit_id': unit_id})
                time.sleep(3)
                # 挂上新角色
                await monitor_client.callapi('/support_unit/change_setting', {'support_type': 1, 'position': index + 3, 'action': 1, 'unit_id': unit_id})
                msg = f'已将{supmon.nickname}的{chara_name}挂至{index + 1}号助战位中'
                await bot.send(ev, msg)
                await refreshAndShowZZ(bot, ev, target_chara) # 图片展示挂上去的助战的数据
            except:
                await bot.send(ev,'操作失败/生成助战信息图片失败')
                pass
            return

    await bot.send(ev,'发生了错误！可能是：没有找到相应角色|角色名输入错误|两个助战位都未超过30分钟!')

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
        support_list = await get_support_list('self_query',acccountinfo,qq_id)
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
