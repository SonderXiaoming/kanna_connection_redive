import json
import asyncio
import os

DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
RES_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'img')
FONT_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'fonts')

stage_dict = {
    "B":1,
    "C":2,
    "D":3,
    0:"B",
    1:"B",
    2:"C",
    3:"D"
}

rate_score = {
    "B":[1.6,1.6,1.8,1.9,2],
    "C":[2,2,2.1,2.1,2.2],
    "D":[4.5,4.5,4.7,4.8,5]
}

stage = [0, 6, 22]

boss_max = [
    [
        6000000,
        8000000,
        10000000,
        12000000,
        15000000
    ],
    [
        6000000,
        8000000,
        10000000,
        12000000,
        15000000
    ],
    [
        12000000,
        14000000,
        17000000,
        19000000,
        22000000
    ],
    [
        19000000,
        20000000,
        23000000,
        25000000,
        27000000
    ],
    [
        85000000,
        90000000,
        95000000,
        100000000,
        110000000
    ]
]

def lap2stage(lap_num):
    if lap_num in range(7):
        stage = 'B'
    elif lap_num in range(7,23):
        stage = 'C'
    else:
        stage = 'D'
    return stage

async def load_config(path):
    try:
        with open(path, encoding='utf8') as f:
            config = json.load(f)
            return config
    except:
        return []

async def write_config(path, config):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False)
    
async def check_client(client):
    for i in range(3):
        try:
            load_index = await client.callapi('/load/index', {'carrier': 'OPPO'})
            if "server_error" not in load_index:
                return True
        except:
            pass
    return False

async def safe_send(bot, ev, msg):
    if not msg:
        return
    try:
        await bot.send(ev, msg)
    except:
        pass
