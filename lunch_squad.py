import os
import os
import shutil
import sys
from datetime import datetime

import yaml
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, QAction)

from database import LunchSquadDB
from tabs.squad_settings import SquadSettingsTab
from tabs.team_creation import TeamCreationTab
from tabs.user_settings import UserSettingsTab
from utils import show_dialog, Cache


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # 창 크기 설정
        self.setGeometry(100, 100, 800, 300)

        # 기본 위젯
        self.widget = QWidget()
        self.setCentralWidget(self.widget)

        # 메뉴바 생성
        menu_bar = self.menuBar()

        # "파일" 메뉴 추가
        file_menu = menu_bar.addMenu("Settings")

        # "사용자 내보내기" 액션 추가
        export_action = QAction("사용자 내보내기", self)
        export_action.triggered.connect(self.export_users)  # 연결된 동작

        # "사용자 가져오기" 액션 추가
        import_action = QAction("사용자 가져오기", self)
        import_action.triggered.connect(self.import_users)  # 연결된 동작

        # 파일 메뉴에 액션 추가
        file_menu.addAction(export_action)
        file_menu.addAction(import_action)

        # 상단에 탭 위젯 추가
        self.tabs = QTabWidget(self)
        self.widget.setLayout(QVBoxLayout())
        self.widget.layout().addWidget(self.tabs)

        try:
            with open("./settings.txt", "r", encoding="utf-8") as file:
                data = yaml.safe_load(file)
        except FileNotFoundError:
            data = {}

        Cache.team_member = data.get("team_member", 4)
        Cache.leader_display_row = data.get("leader_display_row", 3)
        Cache.leader_cycle = data.get("leader_cycle", 3)

        running_db = "lunch_squad.dat"
        self.db = LunchSquadDB(running_db)

        # 탭 추가
        self.tab1 = TeamCreationTab(self.db)
        self.tab2 = UserSettingsTab(self.db)
        self.tab3 = SquadSettingsTab(self.db)
        self.tabs.addTab(self.tab1, "소통런치 조편성")
        self.tabs.addTab(self.tab2, "사용자 설정")
        self.tabs.addTab(self.tab3, "조편성 설정")
        self.setWindowTitle("소통런치 조편성 프로그램")

    def export_users(self):
        users = self.db.select_users()
        current_time = str(int(datetime.now().timestamp() * 1000))
        filename = f"users_{current_time}.txt"

        export_data = list()
        for x in users:
            export_data.append(f"{x[1]}: {list(x[2:])}")

        with open(f"./{filename}", "w") as file:
            file.write("\n".join(export_data))
        show_dialog("사용자 내보내기", f"완료되었습니다.\n(file: {filename})")

    def import_users(self):
        try:
            with open("./users.txt", "r") as file:
                users = yaml.safe_load(file)
            self.db.initial_data(users, force=True)
            show_dialog("사용자 가져오기", f"완료되었습니다.")
        except FileNotFoundError:
            show_dialog("사용자 가져오기", f"users.json 파일이 없습니다. 파일을 생성하시거나 요청해주세요.\n"
                                    '{"이름": ["조장가능날짜", "마지막조장날짜", 출력그룹(number)]')


if __name__ == '__main__':
    application = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(application.exec_())
