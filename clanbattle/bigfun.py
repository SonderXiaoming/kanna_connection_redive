from datetime import datetime, timezone, timedelta
import httpx

BOSS_API = "https://bigfun.bilibili.com/api/feweb?target=gzlj-clan-day-report-collect/a"
LIST_API = "https://bigfun.bilibili.com/api/feweb?target=gzlj-clan-boss-report-collect/a"
MEMBER_API = "https://bigfun.bilibili.com/api/feweb?target=gzlj-clan-day-report/a&size=30"

TIMEZONE = timezone(timedelta(hours=8))

async def get_record(cookie):
    records = []
    now = int(datetime.now().timestamp())
    start_date, end_date = await get_start_end_date(cookie)
    if now > end_date:
        now = end_date

    while (start_date <= now):
        data = await get_data(cookie, datetime.fromtimestamp(now).replace(tzinfo=TIMEZONE).strftime('%Y-%m-%d'))
        if data and data.get('data'):
            records.append(data['data'])
        now -= 24 * 3600
    return records


async def get_data(cookie, date):
    try:
        async with httpx.AsyncClient(cookies=cookie) as client:
            resp = await client.get(f'{MEMBER_API}&date={date}')
            return resp.json()
    except:
        return None


async def get_boss_info(cookie):
    async with httpx.AsyncClient(cookies=cookie) as client:
        resp = await client.get(LIST_API)
        data = resp.json()
    if not data or len(data) == 0:
        raise Exception('API访问失败, 请检查你的团队战工具是否可以登录')
    elif 'data' not in data or len(data['data']) == 0:
        raise Exception('API数据异常, 请检查你的团队战工具是否有数据')

    return {boss['boss_name']: index+1 for index, boss in enumerate(data['data']['boss_list'][0:5])}


async def get_start_end_date(cookie):
    async with httpx.AsyncClient(cookies=cookie) as client:
        resp = await client.get(BOSS_API)
        dates = resp.json()
        return (datetime.strptime(dates['data']['day_list'][-1], '%Y-%m-%d').replace(
                    tzinfo=TIMEZONE).timestamp(),
                datetime.strptime(dates['data']['day_list'][0], '%Y-%m-%d').replace(
                    tzinfo=TIMEZONE).timestamp()
                )
