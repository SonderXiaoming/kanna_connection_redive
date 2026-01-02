import json
import re
import os
from nonebot import get_bot
from .create_img import general_img
from .accurateassis import accurateassis
from ..login import query
from ..util.text2img import image_draw
from ..util.tools import load_config, DATA_PATH
from hoshino import Service,priv
from hoshino.typing import CQEvent
from hoshino.util import pic2b64
from hoshino.typing import NoticeSession,MessageSegment
from hoshino.modules.convert2img.convert2img import grid2imgb64

help_text = '''
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

info_path = os.path.join(DATA_PATH, "support_query")

async def get_support_list(info,acccountinfo,qq_id):
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

@sv.on_fullmatch('查box帮助')
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
