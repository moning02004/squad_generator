import random
import sqlite3
from collections import defaultdict
from datetime import datetime, timedelta

from utils import Cache


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
        cursor.execute(f"select * from users {where_clause} order by last_date")
        users = cursor.fetchall()
        cursor.close()
        return users

    def select_user(self, user_id):
        cursor = self.connect.cursor()
        cursor.execute(f"select name, enable_date, last_date, priority from users where id = {user_id}")
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
        cursor.execute(f"select name, enable_date, last_date, priority from users where id in ({user_ids})")
        users = cursor.fetchone()
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
        cursor.execute(f"select {column} from team_history {where_clause} order by id desc;")
        histories = cursor.fetchall()
        cursor.close()

        return histories

    def insert_team_history(self, date_label, date_text):
        history = self.select_team_history(date_label=date_label)
        if history:
            team = history[0]
            return team, None, None

        team, leader_ids = self.generate_team(date_text)
        leader = team.pop(1)
        team.insert(Cache.leader_display_row, leader)

        data = "\n".join(team)
        cursor = self.connect.cursor()
        leader_ids_text = ", ".join(map(str, leader_ids))
        cursor.execute(
            f"INSERT INTO team_history (date_label, date_text, team_data, leader_ids) VALUES ('{date_label}', '{date_text}', '{data.strip()}', '{leader_ids_text}')")
        self.logging_message(cursor, message=f"{date_label} 소통런치 조편성이 생성되었습니다.")
        self.connect.commit()
        cursor.close()
        return team, leader_ids

    def clone_team_history(self, date_label, date_text):
        history = self.select_team_history(date_text=date_text)
        if not history:
            return None, None

        team, leader_ids = history[0]
        cursor = self.connect.cursor()
        leader_ids_text = ", ".join(map(str, leader_ids))
        cursor.execute(
            f"INSERT INTO team_history (date_label, date_text, team_data, leader_ids) VALUES ('{date_label}', '{date_text}', '{team.strip()}', '{leader_ids_text}')")
        self.logging_message(cursor, message=f"{date_label} 소통런치 조편성이 복제되었습니다.")
        self.connect.commit()
        cursor.close()
        return team, leader_ids

    def delete_team_history(self, date_label):
        where_clause = f"where date_label = '{date_label}'"

        cursor = self.connect.cursor()
        cursor.execute(f"delete from team_history {where_clause}")
        self.logging_message(cursor, message=f"{date_label} 소통런치 조편성이 삭제되었습니다.")
        self.connect.commit()
        cursor.close()

    def generate_team(self, date_text):
        cursor = self.connect.cursor()
        cursor.execute(f"select id, name, last_date, enable_date, priority from users;")
        users = cursor.fetchall()
        cursor.close()
        order_by = {x[1]: x[-1] or 100 for x in users}

        selected_date = datetime.strptime(date_text, "%Y-%m-%d")
        this_week_date = (selected_date - timedelta(days=selected_date.weekday())).strftime("%Y-%m-%d")
        candidate_date1 = (selected_date - timedelta(days=selected_date.weekday()) -
                           timedelta(weeks=Cache.leader_cycle)).strftime("%Y-%m-%d")
        candidate_date2 = (selected_date - timedelta(days=selected_date.weekday()) -
                           timedelta(weeks=2)).strftime("%Y-%m-%d")

        candidates1 = [(user_id, name, priority) for user_id, name, last_date, enable_date, priority in users
                       if enable_date < this_week_date and last_date <= candidate_date1]
        candidates2 = [(user_id, name, priority) for user_id, name, last_date, enable_date, priority in users
                       if enable_date < this_week_date and last_date <= candidate_date2]
        candidates = list(set(candidates1 + candidates2[:len(candidates1) - self.team_number]))

        candidate_leader_ids = [x[0] for x in candidates]
        all_users = [(user_id, name, priority) for user_id, name, last_date, enable_date, priority in users if
                     enable_date < this_week_date if user_id not in candidate_leader_ids]
        random.shuffle(all_users)
        candidates = list(set(candidates + all_users[:len(candidates) - self.team_number]))

        team_leaders = random.sample(candidates, self.team_number)
        team_leader_names = [(x[1], x[2]) for x in team_leaders]
        random.shuffle(team_leader_names)
        left_members = list(set([(name, priority) for _, name, _, _, priority in users]) -
                            set(team_leader_names))
        workers = sorted(left_members, key=lambda x: order_by.get(x[0], 100))[:self.team_number * 2]
        left_members = list(set(left_members) - set(workers))
        left_users = defaultdict(lambda: list())
        ordered_priority = list()
        for x, _priority in left_members:
            left_users[_priority].append(x)
            ordered_priority.append(_priority)
            random.shuffle(left_users[_priority])
        left_members = [x[0] for x in workers]
        [left_members.extend(left_users[x]) for x in sorted(set(ordered_priority))]

        team_leader_names = [f"#{x[0]}" for x in team_leader_names]
        teams = [", ".join([f"{x}조" for x in range(1, self.team_number + 1)]), ", ".join(team_leader_names)]
        for index in range(0, len(users), self.team_number):
            row = ", ".join(left_members[index:index + self.team_number])
            teams.append(row.strip())
        teams = [x.strip() for x in teams if x.strip()]
        return teams, [x[0] for x in team_leaders]

    def logging_message(self, cursor, message):
        cursor.execute(f"INSERT INTO log (text) VALUES ({repr(message)})")
