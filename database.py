import json
import random
import sqlite3
import time
from collections import defaultdict
from datetime import datetime, timedelta
from itertools import zip_longest

from utils import Cache


def check_divide_members(squad, divide_members, user_order):
    last_squad = list(squad[-1])

    for index in range(len(squad)):
        squad[index] = list(squad[index])
        if len(set(squad[index]) & set(divide_members)) == len(divide_members):
            squad[index].append(last_squad.pop(-1))
            last_squad.append(squad[index].pop(squad[index].index(divide_members[1])))
    squad[-1] = last_squad

    for index in range(len(squad)):
        squad[index][1:] = sorted(squad[index][1:], key=lambda _x: user_order.get(_x, 100))


class LunchSquadDB:
    def __init__(self, db_name):
        self.connect = sqlite3.connect(db_name)
        self.create_tables()
        self.team_number = Cache.team_member

    def create_tables(self):
        cursor = self.connect.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                last_date TEXT NULL,
                enable_date TEXT NULL,
                priority INTEGER NULL
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS team_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date_label TEXT NOT NULL,
                date_text TEXT NOT NULL,
                team_data TEXT NOT NULL,
                leader_ids TEXT NOT NULL
            )
        ''')
        self.logging_message(cursor, message=f"프로그램이 실행되었습니다.")
        self.connect.commit()

    def initial_data(self, data, force=False):
        cursor = self.connect.cursor()
        if force:
            self.logging_message(cursor, message=f"데이터가 초기화 되었습니다.")
            cursor.execute(f"delete from users")

        cursor.execute(f"select 1 from users")
        exists_user = cursor.fetchone()

        if exists_user is None:
            initial_users = list()
            for name, init_data in data.items():
                last_date, enable_date, fixed_squad = init_data
                initial_users.append((name,
                                      last_date or (datetime.now() - timedelta(days=datetime.now().weekday())).strftime(
                                          "%Y-%m-%d"), enable_date, fixed_squad))
            self.insert_users(initial_users)
        cursor.close()

    def select_users(self, enable_leader=None):
        where_clause = ""
        if enable_leader is not None:
            where_clause = f"where enable_leader = {where_clause}"

        cursor = self.connect.cursor()
        cursor.execute(f"select id, name, enable_date, "
                       f"(select date_text from team_history "
                       f"where leader_ids like '' || a.id ||',%' "
                       f"or leader_ids like '%, ' || a.id || ',%' "
                       f"or leader_ids like '%, ' || a.id || ''"
                       f"order by date_text desc limit 1) as recent_date, "
                       f"priority "
                       f"from users a {where_clause} order by priority desc, enable_date, recent_date")
        users = cursor.fetchall()
        cursor.close()
        return users

    def select_user(self, user_id):
        cursor = self.connect.cursor()
        cursor.execute(f"select name, enable_date, "
                       f"(select date_text from team_history "
                       f"where leader_ids like '' || {user_id} ||',%' "
                       f"or leader_ids like '%, ' || {user_id} || ',%' "
                       f"or leader_ids like '%, ' || {user_id} || ''"
                       f"order by date_text desc limit 1) as recent_date, "
                       f"priority from users where id = {user_id}")
        users = cursor.fetchone()
        cursor.close()
        return users

    def insert_users(self, users):
        cursor = self.connect.cursor()
        cursor.executemany(
            'INSERT INTO users (name, last_date, enable_date, priority) VALUES (?, ?, ?, ?)', users)
        self.connect.commit()
        self.logging_message(cursor, message=f"사용자가 추가되었습니다 ({len(users)} 명)")
        cursor.close()

    def update_user(self, user_ids, **kwargs):
        values = ", ".join([f"{x}={repr(y)}" for x, y in kwargs.items() if y is not None])
        user_ids = ",".join(map(str, user_ids))

        cursor = self.connect.cursor()
        cursor.execute(f"UPDATE users SET {values} WHERE id in ({user_ids})")
        self.connect.commit()
        self.logging_message(cursor, message=f"사용자 정보가 변경되었습니다. ({values})")
        cursor.close()

    def delete_user(self, user_id):
        cursor = self.connect.cursor()
        cursor.execute(f"delete from users where id = {user_id}")
        self.logging_message(cursor, message=f"사용자 정보가 삭제되었습니다. ({user_id})")
        self.connect.commit()
        cursor.close()

    def select_team_history(self, date_text="", date_label=""):
        where_clauses = list()
        if date_label:
            where_clauses.append(f"date_label = '{date_label}'")
        if date_text:
            where_clauses.append(f"date_text = '{date_text}'")

        where_clause = ""
        columns = []
        if where_clauses:
            where_clause = " and ".join(where_clauses)
            where_clause = f"where {where_clause}"
            columns = ["team_data", "leader_ids"]
        else:
            columns = ["id", "date_label", "leader_ids"]

        cursor = self.connect.cursor()
        column = ",".join(columns)
        cursor.execute(f"select {column} from team_history {where_clause} order by date_text desc;")
        histories = cursor.fetchall()
        cursor.close()

        return histories

    def insert_team_history(self, date_label, date_text):
        history = self.select_team_history(date_label=date_label)
        if history:
            team = history[0]
            return team, None, None

        new_squad, leader_ids = self.generate_team(date_text)
        for x in new_squad:
            leader = x.pop(0)
            x.insert(Cache.leader_display_row - 1, leader)

        team_json_data = json.dumps(new_squad, ensure_ascii=False)
        cursor = self.connect.cursor()
        leader_ids_text = ", ".join(map(str, leader_ids))
        cursor.execute(
            f"INSERT INTO team_history (date_label, date_text, team_data, leader_ids) VALUES ('{date_label}', '{date_text}', '{team_json_data}', '{leader_ids_text}')")
        self.logging_message(cursor, message=f"{date_label} 소통런치 조편성이 생성되었습니다.")
        self.connect.commit()
        cursor.close()
        return team_json_data, leader_ids

    def clone_team_history(self, date_label, date_text, clone_data):
        history = self.select_team_history(date_text=clone_data)
        if not history:
            return None, None

        team_json_data, leader_ids_text = history[0]
        cursor = self.connect.cursor()
        cursor.execute(
            f"INSERT INTO team_history (date_label, date_text, team_data, leader_ids) VALUES ('{date_label}', '{date_text}', '{team_json_data}', '{leader_ids_text}')")
        self.logging_message(cursor, message=f"{date_label} 소통런치 조편성이 복제되었습니다.")
        self.connect.commit()
        cursor.close()

        print(leader_ids_text)
        return team_json_data, leader_ids_text

    def delete_team_history(self, date_label):
        where_clause = f"where date_label = '{date_label}'"

        cursor = self.connect.cursor()
        cursor.execute(f"delete from team_history {where_clause}")
        self.logging_message(cursor, message=f"{date_label} 소통런치 조편성이 삭제되었습니다.")
        self.connect.commit()
        cursor.close()

    def generate_team(self, date_text):
        cursor = self.connect.cursor()

        cursor.execute(f"select a.id, name, enable_date, "
                       f"(select date_text from team_history "
                       f"where leader_ids like '' || a.id ||',%' "
                       f"or leader_ids like '%, ' || a.id || ',%' "
                       f"or leader_ids like '%, ' || a.id || ''"
                       f"order by date_text desc limit 1) as recent_date, "
                       f"priority from users a")
        users = cursor.fetchall()
        cursor.close()
        order_by = {x[1]: x[-1] or 100 for x in users}

        selected_date = datetime.strptime(date_text, "%Y-%m-%d")
        this_week_date = (selected_date - timedelta(days=selected_date.weekday())).strftime("%Y-%m-%d")
        candidate_date1 = (selected_date - timedelta(days=selected_date.weekday()) -
                           timedelta(weeks=Cache.leader_cycle)).strftime("%Y-%m-%d")
        candidate_date2 = (selected_date - timedelta(days=selected_date.weekday()) -
                           timedelta(weeks=2)).strftime("%Y-%m-%d")

        candidates1 = [(user_id, name, priority) for user_id, name, enable_date, last_date, priority in users
                       if enable_date < this_week_date and (last_date is None or last_date <= candidate_date1)]
        random.shuffle(candidates1)
        candidates1 = candidates1[:self.team_number]

        candidate1_leader_ids = [x[0] for x in candidates1]
        candidates2 = [(user_id, name, priority) for user_id, name, enable_date, last_date, priority in users
                       if enable_date < this_week_date and (last_date is None or last_date <= candidate_date2)
                       and user_id not in candidate1_leader_ids]
        random.shuffle(candidates2)
        candidates = candidates1 + candidates2[:self.team_number - len(candidates1)]

        candidate_leader_ids = [x[0] for x in candidates]
        all_users = [(user_id, name, priority) for user_id, name, enable_date, last_date, priority in users
                     if enable_date < this_week_date and user_id not in candidate_leader_ids]
        random.shuffle(all_users)
        candidates = list(set(candidates + all_users[:self.team_number - len(candidates)]))

        team_leaders = random.sample(candidates, self.team_number)
        team_leader_names = [(x[1], x[2]) for x in team_leaders]
        random.shuffle(team_leader_names)
        left_members = list(set([(name, priority) for _, name, _, _, priority in users]) -
                            set(team_leader_names))

        left_users = defaultdict(lambda: list())
        ordered_priority = list()
        left_member = list()
        for x, _priority in left_members:
            random.seed(time.time_ns())
            left_users[_priority].append(x)
            ordered_priority.append(_priority)
            random.shuffle(left_users[_priority])
        [left_member.extend(left_users[x]) for x in sorted(set(ordered_priority))]
        team_leader_names = [x[0] for x in team_leader_names]

        teams = [team_leader_names]
        for index in range(0, len(left_member), Cache.team_member):
            teams.append(left_member[index:index + Cache.team_member])

        squad = list(zip_longest(*teams))
        check_divide_members(squad, ['김도윤', '이민우 팀장'], order_by)
        return squad, [x[0] for x in team_leaders]

    def logging_message(self, cursor, message):
        cursor.execute(f"INSERT INTO log (text) VALUES ({repr(message)})")
