import os
from ..util.tools import FONT_PATH, RES_PATH
from PIL import Image, ImageDraw, ImageFont
from hoshino.modules.priconne.chara import fromid

font_cn_path = os.path.join(FONT_PATH, "SourceHanSansCN-Medium.otf")
res_path = os.path.join(RES_PATH, "support_query")

star_list_orgin = [
Image.open(os.path.join(res_path, '16px-星星.png')).convert("RGBA"),
Image.open(os.path.join(res_path, '16px-星星6.png')).convert("RGBA"),
Image.open(os.path.join(res_path, '16px-星星蓝.png')).convert("RGBA"),
Image.open(os.path.join(res_path, '16px-星星无.png')).convert("RGBA")
]

def _cut_str(obj: str, sec: int):
    """
    按步长分割字符串
    """
    return [obj[i: i+sec] for i in range(0, len(obj), sec)]

async def draw_star(im,change,star,size,x,y):
    star_list = star_list_orgin[:]
    star_list[0] = star_list[0].resize((size,size))

    if star == 6:
        star_list[1] = star_list[1].resize((size,size))
        for i in range(1,6):
            im.paste(star_list[0], (x+i*size,y), mask=star_list[0])
        im.paste(star_list[1], (x+6*size,y), mask=star_list[1])
    elif change:
        star_list[2] = star_list[2].resize((size,size))
        for i in range(1,6):
            if i <= star:
                im.paste(star_list[0], (x+i*size,y), mask=star_list[0])
            else:
                im.paste(star_list[2], (x+i*size,y), mask=star_list[2])
    else:
        star_list[3] = star_list[3].resize((size,size))
        for i in range(1,6):
            if i <= star:
                im.paste(star_list[0], (x+i*size,y), mask=star_list[0])
            else:
                im.paste(star_list[3], (x+i*size,y), mask=star_list[3])

async def draw_img(info,font,icon_size,font_black):
        im = Image.open(os.path.join(res_path, 'template.jpg')).convert("RGBA")
        c_format = fromid(info["id"])
        icon = await c_format.render_icon(icon_size)
        im.paste(icon, (22,23), mask=icon)

        draw = ImageDraw.Draw(im)
        w, h = font.getsize(info["player"])
        draw.text((305-w,30-h), info["player"], font_black, font)

        w, h = font.getsize(info['level'])
        draw.text((305-w,60-h), info['level'], font_black, font)

        w, h = font.getsize(info['rank'])
        draw.text((305-w,90-h), info['rank'], font_black, font)

        w, h = font.getsize(info['unique_equip_slot'])
        draw.text((305-w,120-h), info['unique_equip_slot'], font_black, font)

        w, h = font.getsize(info['skill'][0])
        draw.text((156-w,280-h), info['skill'][0], font_black, font)

        w, h = font.getsize(info['skill'][3])
        draw.text((156-w,315-h), info['skill'][3], font_black, font)

        w, h = font.getsize(info['skill'][1])
        draw.text((305-w,280-h), info['skill'][1], font_black, font)

        w, h = font.getsize(info['skill'][2])
        draw.text((305-w,315-h), info['skill'][2], font_black, font)

        special_attribute =  _cut_str(info['special_attribute'], 25)

        text = '好感加成：'
        text +='\n                    '.join(special_attribute)
        draw.text((25,345),text, font_black, font)
        
        for index,equip in enumerate(info["equip"]):
            if index % 2 == 0:
                if equip == "未装备" or equip == "已装备":
                    w, h = font.getsize(equip)
                    draw.text((156-w,170+16*index-h), equip, font_black, font)
                else:
                    await draw_star(im,False,equip,12,91,160+16*index)
            else:
                if equip == "未装备" or equip == "已装备":
                    w, h = font.getsize(equip)
                    draw.text((305-w,170+16*(index-1)-h), equip, font_black, font)
                else:
                    await draw_star(im,False,equip,12,240,160+16*(index-1))
        
        await draw_star(im,info['star'][1],info['star'][0],16,6,100)
        return im

async def general_img(all_info):
    IMAGE_WIDTH = 330
    IMAGE_HEIGHT = 400
    num = len(all_info)
    IMAGE_COLUMN = int(num**(1/2))
    IMAGE_ROW = num//IMAGE_COLUMN + 1 if num % IMAGE_COLUMN != 0 else num//IMAGE_COLUMN
    base = Image.new('RGB', (IMAGE_COLUMN * IMAGE_WIDTH, IMAGE_ROW * IMAGE_HEIGHT),(0,0,0))
    font = ImageFont.truetype(font_cn_path,12)
    icon_size = 95
    font_black = (77, 76, 81, 255)
    img_list = []
    for info in all_info:
        image = await draw_img(info,font,icon_size,font_black)
        img_list.append(image)
    i = 0
    for y in range(1, IMAGE_ROW + 1):
        for x in range(1, IMAGE_COLUMN + 1):
            try:
                from_image = img_list[i]
            except:
                return base
            base.paste(from_image, ((x - 1) * IMAGE_WIDTH, (y - 1) * IMAGE_HEIGHT))
            i += 1
    return base
        



        


        

