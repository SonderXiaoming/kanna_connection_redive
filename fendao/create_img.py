import os
from .timeaxis import Max_query
from ..util.tools import FONT_PATH, RES_PATH
from PIL import Image, ImageDraw, ImageFont
from hoshino.modules.priconne.chara import fromid

font_path = os.path.join(FONT_PATH, "SourceHanSansCN-Medium.otf")

async def team2pic(entries,borrow = False, unit_loss=(),max_query = Max_query, border_pix=5):
    entries.sort(key= lambda x:(int(x[1])),reverse=True)
    lend_id = []

    n = len(entries)

    if n > max_query:
        entries = entries[:max_query]
        n = len(entries)

    if borrow:
        all_unit = []
        set_unit = set()
        for team in entries:
            all_unit += list(team[2])
            set_unit = set_unit | set(team[2])   

        for unit in set_unit:
            all_unit.remove(unit)

        lend_id = all_unit

    icon_size = 64
    im = Image.new('RGBA', (5 * icon_size + 100, n * (icon_size + border_pix)), (255, 255, 255, 255))
    font = ImageFont.truetype(font_path, 16)
    draw = ImageDraw.Draw(im)
    for i, e in enumerate(entries):
        y1 = i * (icon_size + border_pix)
        y2 = y1 + icon_size
        check = True
        for j, c in enumerate(e[2]):
            c_format = fromid(c)
            icon = await c_format.render_icon(icon_size)
            x1 = j * icon_size
            x2 = x1 + icon_size
            im.paste(icon, (x1, y1, x2, y2), icon)
            if c in unit_loss:
                check = False
                frame_x1 = x1
                frame_y1 = y1
            elif check and c in lend_id:
                check = False
                frame_x1 = x1
                frame_y1 = y1
                lend_id.remove(c)
        
        if not check:
            im_frame = Image.open(os.path.join(RES_PATH, 'fendao', 'frame.png')).convert("RGBA")
            im_frame = im_frame.resize((64,64))
            im.paste(im_frame, (frame_x1, frame_y1), im_frame)
        
        x1 = 5 * icon_size + 5
        x2 = x1 + 16

        if "T" in e[0]:
            set_type = "自动"
        elif "W" in e[0]:
            set_type = "尾刀"
        else:
            set_type = "手动"

        draw.text((x1, y1), set_type, (0, 0, 0, 255), font)
        draw.text((x1, y1+20), e[0], (0, 0, 0, 255), font)
        draw.text((x1, y1+40), f"{e[1]}W", (0, 0, 0, 255), font)
    return im