from dataclasses import dataclass
from io import BytesIO
import itertools
import math
import os
from typing import Tuple

import httpx
from ..util.tools import FONT_PATH, RES_PATH
from PIL import Image, ImageDraw, ImageFont
from hoshino.modules.priconne.chara import fromid
from .accurateassis import get_ex_equip_max_star

font_cn_path = os.path.join(FONT_PATH, "SourceHanSansCN-Medium.otf")
res_path = os.path.join(RES_PATH, "support_query")

IMAGE_WIDTH = 593
IMAGE_HEIGHT = 788

star_list = [
    Image.open(os.path.join(res_path, "16px-星星.png")).convert("RGBA"),
    Image.open(os.path.join(res_path, "16px-星星6.png")).convert("RGBA"),
    Image.open(os.path.join(res_path, "16px-星星蓝.png")).convert("RGBA"),
    Image.open(os.path.join(res_path, "16px-星星无.png")).convert("RGBA"),
]

ex_star_list = [
    Image.open(os.path.join(res_path, "ex_star_white.png")).convert("RGBA"),
    Image.open(os.path.join(res_path, "ex_star_grey.png")).convert("RGBA"),
    Image.open(os.path.join(res_path, "ex_star_blue.png")).convert("RGBA"),
    Image.open(os.path.join(res_path, "ex_star_red.png")).convert("RGBA"),
]


def get_font_size(font: ImageFont.ImageFont, text: str) -> Tuple[int, int]:
    bbox = font.getbbox(text)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def cut_str(obj: str, sec: int):
    """
    按步长分割字符串
    """
    return [obj[i : i + sec] for i in range(0, len(obj), sec)]


@dataclass
class TextImageInfo:
    w: int
    h: int
    base_x: int
    base_y: int
    text: str


async def draw_star(
    im: Image.Image, battle_star: int, star: int, size: int, x: int, y: int
):
    start1 = star_list[0].resize((size, size), Image.LANCZOS)
    if star == 6:
        start2 = start1
        start3 = star_list[1].resize((size * 12 // 10, size * 12 // 10), Image.LANCZOS)
        im.paste(start3, (x + 6 * size, y - size // 10), mask=start3)
    elif battle_star:
        start2 = star_list[2].resize((size, size), Image.LANCZOS)
    else:
        start2 = star_list[3].resize((size, size), Image.LANCZOS)
        battle_star = star

    for i in range(1, 5 + 1):
        draw_star = start1 if i <= battle_star else start2
        im.paste(draw_star, (x + i * size, y), mask=draw_star)


async def draw_ex_equip_star(
    im: Image.Image, max_star: int, star: int, width: int, x: int, y: int
) -> Image.Image:
    height = width * 37 // 27
    for i in range(1, star + 1):
        draw_star = (
            ex_star_list[2].resize((width, height), Image.LANCZOS)
            if i <= 3
            else ex_star_list[3].resize((width, height), Image.LANCZOS)
        )
        im.paste(draw_star, (x + i * width, y), mask=draw_star)

    for i in range(star + 1, max_star + 1):
        draw_star = (
            ex_star_list[1].resize((width, height), Image.LANCZOS)
            if i <= 3
            else ex_star_list[0].resize((width, height), Image.LANCZOS)
        )
        im.paste(draw_star, (x + i * width, y), mask=draw_star)


async def get_ex_equipment_img(equipment_id, size) -> Image.Image:

    if not equipment_id:
        image = Image.open(os.path.join(res_path, "unknown.png"))

    else:
        path = os.path.join(res_path, "ex_equipment", f"{equipment_id}.png")
        if os.path.exists(path):
            image = Image.open(path)
        else:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://pcredivewiki.tw/static/images/equipment/icon_equipment_{equipment_id}.png"
                )
                response.raise_for_status()
                image = Image.open(BytesIO(response.content))
                image.save(path)

    return image.resize((size, size), Image.LANCZOS).convert("RGBA")


async def draw_img(info, font, icon_size, font_color):
    im = Image.open(os.path.join(res_path, "pcr_unit.png")).convert("RGBA")
    icon = (
        (await fromid(info["id"]).get_icon(info["star"][0]))
        .open()
        .convert("RGBA")
        .resize((icon_size, icon_size), Image.LANCZOS)
    )
    im.paste(icon, (220, 71), mask=icon)
    await draw_star(
        im,
        info["star"][0] if info["star"][1] else 0,
        5 if info["star"][1] else info["star"][0],
        25,
        195,
        200,
    )

    draw = ImageDraw.Draw(im)
    info["special_attribute"] = cut_str(info["special_attribute"], 10)
    text = "好感加成：" + "\n                    ".join(info["special_attribute"])
    for text_info in [
        TextImageInfo(*get_font_size(font, info["player"]), 320, 320, info["player"]),
        TextImageInfo(*get_font_size(font, info["level"]), 320, 368, info["level"]),
        TextImageInfo(*get_font_size(font, info["rank"]), 320, 464, info["rank"]),
        TextImageInfo(
            *get_font_size(font, info["unique_equip_slot"]),
            320,
            416,
            info["unique_equip_slot"],
        ),
        TextImageInfo(
            *get_font_size(font, info["skill"][0]), 555, 320, info["skill"][0]
        ),
        TextImageInfo(
            *get_font_size(font, info["skill"][3]), 555, 464, info["skill"][3]
        ),
        TextImageInfo(
            *get_font_size(font, info["skill"][1]), 555, 368, info["skill"][1]
        ),
        TextImageInfo(
            *get_font_size(font, info["skill"][2]), 555, 416, info["skill"][2]
        ),
        TextImageInfo(0, 0, 72, 720, text),
    ]:
        draw.text(
            (text_info.base_x - text_info.w, text_info.base_y - text_info.h),
            text_info.text,
            font_color,
            font,
        )

    for index, equip in enumerate(info["equip"]):
        equip = str(equip)
        i = index % 2
        if equip.isdigit():
            await draw_star(im, 0, int(equip), 18, 95 + i * 370, 80 + 32 * (index - i))
        else:
            w, h = get_font_size(font, equip)
            draw.text(
                (190 + i * 383 - w, 95 + 32 * (index - i) - h), equip, font_color, font
            )

    for index, (equip_id, level) in enumerate(info["ex_equip"]):
        ex_icon = await get_ex_equipment_img(equip_id, 118)
        im.paste(ex_icon, (43 + 198 * index, 542), mask=ex_icon)
        if equip_id:
            await draw_ex_equip_star(
                im,
                get_ex_equip_max_star(equip_id),
                level,
                16,
                40 + 200 * index,
                630,
            )

    return im


async def general_img(all_info):
    num = len(all_info)
    IMAGE_COLUMN = math.isqrt(num)

    IMAGE_ROW = math.ceil(num / IMAGE_COLUMN)
    base = Image.new(
        "RGB", (IMAGE_COLUMN * IMAGE_WIDTH, IMAGE_ROW * IMAGE_HEIGHT), (0, 0, 0)
    )
    font = ImageFont.truetype(font_cn_path, 20)
    img_list = [await draw_img(info, font, 155, (0, 0, 0, 255)) for info in all_info]
    for i, (y, x) in enumerate(
        itertools.product(range(1, IMAGE_ROW + 1), range(1, IMAGE_COLUMN + 1))
    ):
        if i >= num:
            break

        from_image = img_list[i]
        base.paste(from_image, ((x - 1) * IMAGE_WIDTH, (y - 1) * IMAGE_HEIGHT))
    return base
