import sqlite3
import os
from datetime import datetime, timezone, timedelta
from ..util.tools import load_config, lap2stage
from .base import clan_path


def pcr_date(timeStamp: int):
    now = datetime.fromtimestamp(
        timeStamp, tz=timezone(timedelta(hours=8)))
    if now.hour < 5:
        now -= timedelta(days=1)
    return now.replace(hour=5, minute=0, second=0, microsecond=0)  # 用5点做基准


class SqliteDao(object):
    def __init__(self, table, columns, fields, groupid):
        DB_PATH = os.path.join(clan_path, f"{groupid}", 'clanbattle.db')
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        self._dbpath = DB_PATH
        self._table = table
        self._columns = columns
        self._fields = fields
        self._create_table()

    def _create_table(self):
        sql = "CREATE TABLE IF NOT EXISTS {0} ({1})".format(
            self._table, self._fields)
        with self._connect() as conn:
            conn.execute(sql)

    def _connect(self):
        return sqlite3.connect(self._dbpath, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)


class SLDao(SqliteDao):
    def __init__(self, groupid):
        super().__init__(
            table='sl',
            columns='uid, last_sl,',
            fields='''
            uid INT NOT NULL,
            last_sl INT
            ''',
            groupid=groupid
        )

    # 0 -> 记录成功
    # 1 -> 当天已有SL记录
    # 2 -> 其它错误
    def add_sl(self, uid):
        time = pcr_date(datetime.now().timestamp()).timestamp()
        with self._connect() as conn:
            try:
                ret = conn.execute(
                    "SELECT uid, last_sl FROM sl WHERE uid = ?", (uid,)).fetchone()

                # 该成员没有使用过SL
                if not ret:
                    conn.execute(
                        'INSERT INTO sl (uid, last_sl) VALUES (?, ?)', (uid, time,))
                    return 0

                last_sl = ret[1]

                # 今天已经有SL记录
                if last_sl == time:
                    return 1

                # 今天没有SL
                else:
                    conn.execute(
                        'UPDATE sl SET last_sl = ? WHERE uid = ?', (time, uid,))
                    return 0

            except (sqlite3.DatabaseError) as e:
                raise

    # 0 -> 没有SL
    # 1 -> 有SL
    # 2 -> Error
    def check_sl(self, uid):
        time = pcr_date(datetime.now().timestamp()).timestamp()
        with self._connect() as conn:
            try:
                ret = conn.execute(
                    "SELECT uid, last_sl FROM sl WHERE uid = ?", (uid,)).fetchone()

                # 该成员没有使用过SL
                if not ret:
                    return 0

                last_sl = ret[1]

                # 今天已经有SL记录
                if last_sl == time:
                    return 1

                # 今天没有SL
                else:
                    return 0

            except (sqlite3.DatabaseError) as e:
                raise

    def refresh(self):
        with self._connect() as conn:
            time = pcr_date(datetime.now().timestamp()).timestamp()
            conn.execute("DELETE FROM sl where last_sl != ?", (time,))


class SubscribeDao(SqliteDao):
    def __init__(self, groupid):
        super().__init__(
            table='subscribe',
            columns='uid, boss, lap, text, ',
            fields='''
            uid INT NOT NULL,
            boss INT NOT NULL,
            lap INT NOT NULL,
            text TEXT NOT NULL
            ''',
            groupid=groupid
        )

    def refresh(self):
        self.clear_subscriber()

    def get_subscriber(self, boss, lap=None):
        with self._connect() as conn:
            try:
                lap = lap if lap else 999
                ret = conn.execute(
                    "SELECT DISTINCT uid, lap, text FROM subscribe WHERE boss = ? AND lap <= ?", (boss, lap,)).fetchall()
                return [(r[0], r[1], r[2]) for r in ret]

            except (sqlite3.DatabaseError) as e:
                raise
    # 1 -> Success
    # 0 -> Fail

    def clear_subscriber(self, boss=None, lap=None):
        sql = f"DELETE FROM subscribe WHERE 1=1" if not boss else f"DELETE FROM subscribe WHERE boss = {boss}"
        if lap:
            sql += f" AND lap <= {lap}"
        with self._connect() as conn:
            try:
                conn.execute(sql)
                return 1
            except (sqlite3.DatabaseError) as e:
                return 0

    def delete_subscriber(self, uid=None, boss=None):
        sql = f"DELETE FROM subscribe WHERE boss = {boss} AND uid = {uid}"
        with self._connect() as conn:
            try:
                conn.execute(sql)
                return 1

            except (sqlite3.DatabaseError) as e:
                return 0

    def add_subscribe(self, uid, boss, lap, text):
        with self._connect() as conn:
            try:
                ret = conn.execute(
                    "SELECT DISTINCT uid, lap FROM subscribe WHERE boss = ? AND uid = ?", (boss, uid)).fetchone()
                if not ret:
                    conn.execute(
                        "INSERT INTO subscribe (uid, boss, lap, text) VALUES (?,?,?,?) ", (uid, boss, lap, text))
                else:
                    conn.execute(
                        f"UPDATE {self._table} SET text = '{text}', lap = {lap} WHERE boss = {boss} AND uid = {uid}")
                return 1

            except (sqlite3.DatabaseError) as e:
                return 0

    async def notify_subscribe(self, boss, lap, clan_lap):
        if lap - clan_lap >= 2 or lap2stage(lap) != lap2stage(clan_lap) or not (info := self.get_subscriber(boss, lap)):
            return ""

        # 清除预约成员
        self.clear_subscriber(boss, lap)

        return ' '.join([f'[CQ:at,qq={qq}]' for qq, _, _ in info]) + f'\n你们预约的{boss}王出现了'


class TreeDao(SqliteDao):
    def __init__(self, groupid):
        super().__init__(
            table='tree',
            columns='uid, boss, time, text',
            fields='''
            uid INT NOT NULL,
            boss INT NOT NULL,
            time INT NOT NULL,
            text TEXT NOT NULL
            ''',
            groupid=groupid
        )

    def refresh(self):
        self.clear_tree()

    def get_tree(self, boss):
        with self._connect() as conn:
            try:
                ret = conn.execute(
                    "SELECT DISTINCT uid, time, text FROM tree WHERE boss = ?", (boss,)).fetchall()
                return [(r[0], r[1], r[2]) for r in ret]

            except (sqlite3.DatabaseError) as e:
                raise
    # 1 -> Success
    # 0 -> Fail

    def clear_tree(self, boss=None):
        sql = f"DELETE FROM tree WHERE 1=1" if not boss else f"DELETE FROM tree WHERE boss = {boss}"
        with self._connect() as conn:
            try:
                conn.execute(sql)
                return 1
            except (sqlite3.DatabaseError) as e:
                return 0

    def delete_tree(self, uid):
        sql = f"DELETE FROM tree WHERE uid = {uid}"
        with self._connect() as conn:
            try:
                conn.execute(sql)
                return 1

            except (sqlite3.DatabaseError) as e:
                return 0

    def add_tree(self, uid, boss, text):
        with self._connect() as conn:
            try:
                ret = conn.execute(
                    "SELECT DISTINCT uid FROM tree WHERE boss = ? AND uid = ?", (boss, uid)).fetchone()
                if not ret:
                    time = int(datetime.now().timestamp())
                    conn.execute(
                        "INSERT INTO tree (uid, boss, time, text) VALUES (?,?,?,?) ", (uid, boss, time, text))
                else:
                    conn.execute(
                        f"UPDATE {self._table} SET text = '{text}' WHERE boss = {boss} AND uid = {uid}")
                return 1

            except (sqlite3.DatabaseError) as e:
                return 0

    async def notify_tree(self, boss):
        # 获取挂树成员
        if not (info := self.get_tree(boss)):
            return ""

        # 清除挂树成员
        self.clear_tree(boss)

        return "以下成员将自动下树：\n" + ' '.join([f'[CQ:at,qq={qq}]' for qq, _, _ in info])


class ApplyDao(SqliteDao):
    def __init__(self, groupid):
        super().__init__(
            table='apply',
            columns='uid, boss, time, text',
            fields='''
            uid INT NOT NULL,
            boss INT NOT NULL,
            time INT NOT NULL,
            text TEXT NOT NULL
            ''',
            groupid=groupid
        )

    def refresh(self):
        self.clear_apply()

    def get_apply(self, boss):
        with self._connect() as conn:
            try:
                ret = conn.execute(
                    "SELECT DISTINCT uid, time, text FROM apply WHERE boss = ?", (boss,)).fetchall()
                return [(r[0], r[1], r[2]) for r in ret]

            except (sqlite3.DatabaseError) as e:
                raise
    # 1 -> Success
    # 0 -> Fail

    def clear_apply(self, boss=None):
        sql = f"DELETE FROM apply WHERE 1=1" if not boss else f"DELETE FROM apply WHERE boss = {boss}"
        with self._connect() as conn:
            try:
                conn.execute(sql)
                return 1
            except (sqlite3.DatabaseError) as e:
                return 0

    def delete_apply(self, uid):
        sql = f"DELETE FROM apply WHERE uid = {uid}"
        with self._connect() as conn:
            try:
                conn.execute(sql)
                return 1

            except (sqlite3.DatabaseError) as e:
                return 0

    def add_apply(self, uid, boss, text):
        with self._connect() as conn:
            try:
                ret = conn.execute(
                    "SELECT DISTINCT uid FROM apply WHERE boss = ? AND uid = ?", (boss, uid)).fetchone()
                if not ret:
                    time = int(datetime.now().timestamp())
                    conn.execute(
                        "INSERT INTO apply (uid, boss, time, text) VALUES (?,?,?,?) ", (uid, boss, time, text))
                else:
                    conn.execute(
                        f"UPDATE {self._table} SET text = '{text}' WHERE boss = {boss} AND uid = {uid}")

                return 1

            except (sqlite3.DatabaseError) as e:
                return 0


class RecordDao(SqliteDao):
    def __init__(self, groupid):
        super().__init__(
            table='records',
            columns='''
            pcrid, name, time, lap, boss, damage, flag, battle_log_id,
            remain_time, battle_time, unit1, unit2, unit3, unit4, unit5,
            unit1_level, unit2_level, unit3_level, unit4_level, unit5_level,
            unit1_damage, unit2_damage, unit3_damage, unit4_damage, unit5_damage,
            unit1_rarity, unit2_rarity, unit3_rarity, unit4_rarity, unit5_rarity,
            unit1_rank, unit2_rank, unit3_rank, unit4_rank, unit5_rank,
            unit1_unique_equip, unit2_unique_equip, unit3_unique_equip, unit4_unique_equip, unit5_unique_equip
            ''',
            fields='''
            pcrid INT NOT NULL, name VARCHAR(16) NOT NULL,
            time INT NOT NULL, lap INT NOT NULL,
            boss VARCHAR(16) NOT NULL, damage INT NOT NULL,
            flag FLOAT NOT NULL, battle_log_id INT NOT NULL,
            remain_time INT NOT NULL, battle_time INT NOT NULL,
            unit1 INT NOT NULL, unit2 INT NOT NULL,
            unit3 INT NOT NULL, unit4 INT NOT NULL,
            unit5  INT NOT NULL, unit1_level INT NOT NULL, 
            unit2_level INT NOT NULL, unit3_level INT NOT NULL, 
            unit4_level INT NOT NULL, unit5_level INT NOT NULL,
            unit1_damage INT NOT NULL, unit2_damage INT NOT NULL, 
            unit3_damage INT NOT NULL, unit4_damage INT NOT NULL, 
            unit5_damage INT NOT NULL, unit1_rarity INT NOT NULL, 
            unit2_rarity INT NOT NULL, unit3_rarity INT NOT NULL, 
            unit4_rarity INT NOT NULL, unit5_rarity INT NOT NULL,
            unit1_rank INT NOT NULL, unit2_rank INT NOT NULL,
            unit3_rank INT NOT NULL, unit4_rank INT NOT NULL,
            unit5_rank INT NOT NULL, unit1_unique_equip INT NOT NULL, 
            unit2_unique_equip INT NOT NULL, unit3_unique_equip INT NOT NULL, 
            unit4_unique_equip INT NOT NULL, unit5_unique_equip INT NOT NULL
            ''',
            groupid=groupid
        )
        self.group_id = groupid

    async def add_record(self, dao_list):
        # 0完整刀。0.5补偿，1尾刀
        try:
            with self._connect() as conn:
                conn.executemany(f"INSERT INTO {self._table} VALUES ({','.join(['?' for i in range(40)])})", dao_list)
        except (sqlite3.DatabaseError) as e:
            raise

    def get_history(self, id):
        with self._connect() as conn:
            try:
                result = conn.execute(f"""
                    SELECT DISTINCT 
                    lap, boss, damage, unit1, unit2, unit3, unit4, unit5,
                    unit1_rarity, unit2_rarity, unit3_rarity, unit4_rarity, unit5_rarity,
                    unit1_rank, unit2_rank, unit3_rank, unit4_rank, unit5_rank,
                    unit1_damage, unit2_damage, unit3_damage, unit4_damage, unit5_damage,
                    unit1_level, unit2_level, unit3_level, unit4_level, unit5_level,
                    unit1_unique_equip, unit2_unique_equip, unit3_unique_equip, unit4_unique_equip, unit5_unique_equip
                    FROM {self._table} WHERE battle_log_id = {id} """).fetchone()
                return result
            except (sqlite3.DatabaseError) as e:
                raise

    def get_player_records(self, name, day):
        latest_time = self.get_latest_time()
        with self._connect() as conn:
            date = pcr_date(latest_time)
            start_day = date - timedelta(days=day)
            try:
                result = conn.execute(f"SELECT DISTINCT time, lap, boss, damage, flag, battle_log_id FROM {self._table} WHERE time BETWEEN ? AND ? AND name = ? ORDER BY time asc", (
                    start_day.timestamp(), latest_time, name,)).fetchall()
                if not result:
                    return None
                return [{'time': r[0], 'lap':r[1], 'boss':r[2], 'damage':r[3], 'flag':r[4], 'history_id': str(r[5])} for r in result]
            except (sqlite3.DatabaseError) as e:
                raise
    
    def get_max_dao(self):
        latest_time = self.get_latest_time()
        with self._connect() as conn:
            date = pcr_date(latest_time)
            start_day = date - timedelta(days=5)
            result = conn.execute(f"SELECT MIN(time) FROM {self._table} WHERE time BETWEEN ? AND ?", (start_day.timestamp(), latest_time,)).fetchone()
            time = result[0] if result[0] else 0
            return (((latest_time - time) // (3600 *24) ) + 1) * 3
            
        
    def get_all_records(self):
        latest_time = self.get_latest_time()
        with self._connect() as conn:
            date = pcr_date(latest_time)
            start_day = date - timedelta(days=5)
            try:
                result = conn.execute(f"SELECT DISTINCT pcrid, name, lap, boss, damage, flag FROM {self._table} WHERE time BETWEEN ? AND ?", (
                    start_day.timestamp(), latest_time,)).fetchall()
                if not result:
                    return None
                return [{'pcrid': r[0], 'name': r[1], 'lap':r[2], 'boss':r[3], 'damage':r[4], 'flag':r[5]} for r in result]
            except (sqlite3.DatabaseError) as e:
                raise

    def get_latest_records(self, pcrid, time):
        with self._connect() as conn:
            try:
                start_day = pcr_date(datetime.now().timestamp())
                result = conn.execute(
                    f"SELECT flag FROM {self._table} WHERE pcrid = {pcrid} AND time between {start_day.timestamp()} AND {time-1} ORDER BY time desc").fetchone()
                return result[0] if result else 0
            except (sqlite3.DatabaseError) as e:
                raise

    def get_day_rcords(self, date: int):
        date = pcr_date(date)
        tomorrow = date + timedelta(days=1)
        with self._connect() as conn:
            try:
                result = conn.execute(f"SELECT DISTINCT pcrid, name, lap, boss, damage, flag FROM {self._table} WHERE time BETWEEN ? AND ?", (
                    date.timestamp(), tomorrow.timestamp())).fetchall()
                if not result:
                    return None
                return [{'pcrid': r[0], 'name': r[1], 'lap':r[2], 'boss':r[3], 'damage':r[4], 'flag':r[5]} for r in result]
            except (sqlite3.DatabaseError) as e:
                raise

    def get_past_damage(self, lap, boss, pcrid):
        with self._connect() as conn:  # 尾刀前造成的伤害
            created_damage_db = conn.execute(
                f"SELECT sum(damage) FROM {self._table} WHERE lap = {lap} AND boss = {boss} AND pcrid = {pcrid}").fetchone()
            return created_damage_db[0] if created_damage_db[0] is not None else 0

    def refresh(self):
        with self._connect() as conn:
            date = pcr_date(datetime.now().timestamp())
            time = date - timedelta(days=28)
            conn.execute(f"DELETE FROM {self._table} where time < {time.timestamp()}")

    def get_latest_time(self):
        with self._connect() as conn:
            result = conn.execute(f'SELECT MAX(time) FROM {self._table}').fetchone()
            return result[0] if result[0] else 0
    
    def correct_dao(self, dao_id,  item):
        with self._connect() as conn:
            result = conn.execute(f'SELECT * FROM {self._table} where battle_log_id = {dao_id}').fetchone()
            if result:
                conn.execute(f"UPDATE {self._table} SET flag = {item} where battle_log_id = {dao_id}")
                return 1
            else:
                return 0

    async def bigfun_check(self, records):
        with self._connect() as conn:
            try:
                for record in records:
                    for member in record:
                        for record in member['damage_list']:
                            time = record['datetime']
                            flag = 0.5 if record['reimburse'] == 1 else record['kill']
                            damage = record['damage']
                            result = conn.execute(f'SELECT time, flag FROM {self._table} where time = {time}').fetchone()
                            if result:
                                conn.execute(f"UPDATE {self._table} SET flag = {flag}, damage = {damage} where time = {time}")
            except (sqlite3.DatabaseError) as e:
                raise

    async def member_check(self):
        config = await load_config(os.path.join(clan_path, f'{self.group_id}', "clanbattle.json"))
        member_dict = config["member"]
        with self._connect() as conn:
            try:
                result = conn.execute(f'SELECT MAX(time) FROM {self._table}').fetchone()
                latest_time = result[0] if result[0] else 0
                date = pcr_date(latest_time)
                start_day = date - timedelta(days=5)
                if result := conn.execute(f"SELECT pcrid, name FROM {self._table} WHERE time BETWEEN ? AND ?", (start_day.timestamp(), latest_time,)).fetchall():
                    for r in result:
                        if r[1] not in member_dict:
                            for name in member_dict:
                                if member_dict[name] == r[0]:
                                    conn.execute(f"UPDATE {self._table} SET name = {name} where pcrid = {member_dict[name]}")
                                    break
            except:
                raise


class MemberDict(SqliteDao):
    def __init__(self, groupid):
        super().__init__(
            table = 'memdict',
            columns = 'gid, gname, qid, qname',
            fields = '''
            gid INT NOT NULL,
            gname TEXT NOT NULL,
            qid INT NOT NULL,
            qname TEXT NOT NULL
            ''',
            groupid = groupid
        )

    def add_mem_pair(self, gid, gname, qid, qname):
        with self._connect() as conn:
            try:
                isExist = conn.execute(f'SELECT * FROM {self._table} where gid = {gid}').fetchone()
                if isExist:
                    conn.execute(f"UPDATE {self._table} SET gname = '{gname}', qid = {qid}, qname = '{qname}' where gid = {gid}")
                else:
                    conn.execute(f"INSERT INTO {self._table} (gid, gname, qid, qname) VALUES ({gid}, '{gname}', {qid}, '{qname}')")
            except:
                raise
    
    def search_member(self, gid = 0, gname = ""):
        mem_info = None
        with self._connect() as conn:
            try:
                if gid:
                    mem_info = conn.execute(f'SELECT * FROM {self._table} where gid = {gid}').fetchone()
                elif gname:
                    mem_info = conn.execute(f'SELECT * FROM {self._table} where gname = "{gname}"').fetchone()

                return mem_info
            except:
                raise