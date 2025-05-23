import json
import os
from datetime import datetime, timedelta

from PyQt5.QtCore import Qt, QDate, QRect
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QPushButton, QLabel, QHBoxLayout, QWidget, QVBoxLayout, QCalendarWidget

from utils import convert_to_date, show_dialog, Cache


class TeamResultLayout(QVBoxLayout):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.setSpacing(0)
        self.setContentsMargins(0, 0, 0, 0)
        self.data = None

    def clear_layout(self):
        """ 레이아웃에 추가된 모든 위젯과 하위 레이아웃을 삭제합니다. """
        while self.count():
            child = self.takeAt(0)  # 레이아웃에서 항목을 가져옵니다.

            # 위젯이면 삭제
            if child.widget():
                child.widget().deleteLater()  # 위젯 메모리에서 삭제
            # 하위 레이아웃이 있는 경우 (재귀적으로 삭제)
            elif child.layout():
                self._clear_sub_layout(child.layout())

    def _clear_sub_layout(self, layout):
        """재귀적으로 하위 레이아웃의 모든 위젯과 레이아웃을 삭제합니다."""
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
            elif child.layout():
                self._clear_sub_layout(child.layout())
        layout.deleteLater()

    def select_team_member(self, date_label="", date_text=""):
        self.clear_layout()  # 레이아웃 정리
        self.data = []  # 데이터 초기화

        result = self.db.select_team_history(date_label=date_label, date_text=date_text)
        try:
            self.data = json.loads(result[0][0])
            if self.data:
                self.show_team_member()
        except IndexError:
            self.data = list()

    def insert_team_member(self, date_label, selected_date, clone_date=None):
        self.clear_layout()  # 레이아웃 정리
        self.data = []  # 데이터 초기화

        if clone_date:
            team_json_data, leader_ids = self.db.clone_team_history(date_label=date_label,
                                                                    date_text=selected_date,
                                                                    clone_data=clone_date)
            leader_ids = [int(x.strip()) for x in leader_ids.split(",") if x.strip()]
        else:
            team_json_data, leader_ids = self.db.insert_team_history(date_label, selected_date)

        print(team_json_data, leader_ids)
        if leader_ids:
            self.db.update_user(leader_ids, last_date=selected_date)

        self.data = json.loads(team_json_data)
        if self.data:
            self.show_team_member()

    def show_team_member(self):
        [x.insert(0, f"{index + 1} 조") for index, x in enumerate(self.data)]
        for index, row_data in enumerate(zip(*self.data)):
            row_layout = QHBoxLayout()
            row_layout.setSpacing(0)
            for x in row_data:
                x = x or ""

                stylesheet = ["background-color: white;"]
                if index == 0:
                    stylesheet.append("color: #3333ff; border-bottom: 1px solid blue;")
                elif x and index == Cache.leader_display_row:
                    stylesheet = ["background-color: #ffff55;"]

                label_number = QLabel(x.strip())
                label_number.setAlignment(Qt.AlignCenter)
                label_number.setStyleSheet("".join(stylesheet))
                row_layout.addWidget(label_number)

            self.addLayout(row_layout)

    def select_last_week_data(self, last_week):
        try:
            data = self.db.select_team_history(date_text=last_week)[0]
            return data
        except IndexError:
            return None


class TeamCreationTab(QWidget):
    week_label = None
    first_monday = None
    week_number = None
    selected_date = None
    last_week_date = None

    def __init__(self, db):
        super().__init__()
        self.main_layout = QHBoxLayout()
        self.main_layout.setSpacing(5)  # 좌우 간격
        self.main_layout.setContentsMargins(10, 10, 10, 10)  # 외부 여백

        self.left_widget = QWidget()
        self.left_widget.setObjectName("main")  # objectName을 main으로 설정
        self.left_widget.setStyleSheet("""#main {background-color: #3e3e3e; border-radius: 4px;}""")
        self.left_layout = QVBoxLayout(self.left_widget)
        self.left_layout.setContentsMargins(3, 3, 3, 3)  # 외부 여백
        self.result_layout = TeamResultLayout(db)
        self.left_layout.addLayout(self.result_layout)

        self.right_widget = QWidget()
        self.right_layout = QVBoxLayout(self.right_widget)
        self.right_layout.setSpacing(10)

        # 달력 추가 (QCalendarWidget) - 오른쪽 상단에 위치
        self.calendar = QCalendarWidget()
        self.calendar.setGridVisible(True)
        self.calendar.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader)  # 주 번호를 제거
        self.calendar.clicked.connect(self.on_date_selected)

        next_sunday = QDate.currentDate().addDays(21)
        while next_sunday.dayOfWeek() != 7:
            next_sunday = next_sunday.addDays(1)
        self.calendar.setMaximumDate(next_sunday)
        self.right_layout.addWidget(self.calendar)

        self.date_label = QLabel("선택한 날짜: 없음")
        self.date_label.setAlignment(Qt.AlignCenter)
        self.right_layout.addWidget(self.date_label)  # 레이블 추가

        self.save_button = QPushButton("조 편성하기", self)
        self.save_button.setEnabled(False)
        self.save_button.setFixedHeight(30)
        self.save_button.clicked.connect(self.generate_team)
        self.right_layout.addWidget(self.save_button, alignment=Qt.AlignTop)

        self.extra_button = QPushButton("지난 주와 동일하게 편성하기", self)
        self.extra_button.setEnabled(False)
        self.extra_button.setFixedHeight(30)
        self.extra_button.clicked.connect(self.generate_team_as_same)
        self.right_layout.addWidget(self.extra_button, alignment=Qt.AlignTop)

        self.capture_button = QPushButton("캡쳐", self)
        self.capture_button.setEnabled(False)
        self.capture_button.setFixedHeight(30)
        self.capture_button.clicked.connect(self.capture_squad)
        self.right_layout.addWidget(self.capture_button, alignment=Qt.AlignTop)

        self.right_layout.addStretch()

        self.main_layout.addWidget(self.left_widget, 3)
        self.main_layout.addWidget(self.right_widget, 1)
        self.setLayout(self.main_layout)

    def on_date_selected(self, date):
        self.selected_date = date
        self.get_week_number(date)
        self.week_label = f"{self.first_monday.year()}년 {self.first_monday.month()}월 {self.week_number}주차"
        self.date_label.setText(self.week_label)
        self.result_layout.select_team_member(date_label=self.week_label)

        if convert_to_date(self.selected_date) < (datetime.now() - timedelta(days=datetime.now().weekday())).strftime(
                "%Y-%m-%d"):
            self.save_button.setEnabled(False)
            self.capture_button.setEnabled(False)
        else:
            self.save_button.setEnabled(not self.result_layout.data)
            self.capture_button.setEnabled(bool(self.result_layout.data))

        _selected_date = datetime.strptime(convert_to_date(date), "%Y-%m-%d")
        _selected_date = (_selected_date - timedelta(days=_selected_date.weekday() + 7)).strftime("%Y-%m-%d")
        data = self.result_layout.select_last_week_data(_selected_date)
        self.extra_button.setEnabled(bool(not self.result_layout.data and data))
        self.last_week_date = _selected_date

    def generate_team(self):
        if self.week_label:
            self.result_layout.insert_team_member(date_label=self.week_label, selected_date=self.this_week_date)

    def generate_team_as_same(self):
        if self.week_label:
            self.result_layout.insert_team_member(date_label=self.week_label, selected_date=self.this_week_date,
                                                  clone_date=self.last_week_date)

    def capture_squad(self):
        parent_widget = self.left_layout.parentWidget()
        if not parent_widget:
            raise ValueError("Layout must be set to a parent widget.")

        # 레이아웃의 영역(Rect)을 계산
        layout_rect = QRect()
        for i in range(self.left_layout.count()):
            item = self.left_layout.itemAt(i)
            widget = item.widget()
            if widget:
                layout_rect = layout_rect.united(widget.geometry())

        # 부모 위젯에서 레이아웃 부분 캡처
        pixmap = QPixmap(parent_widget.size())
        parent_widget.render(pixmap)
        cropped_pixmap = pixmap.copy(layout_rect)
        os.makedirs("./output", exist_ok=True)
        cropped_pixmap.save(f"./output/{self.week_label}.png")
        show_dialog("완료", "캡쳐가 완료되었습니다!")

    def get_week_number(self, date):
        year, month = date.year(), date.month()
        first_of_month = QDate(year, month, 1)

        first_monday = first_of_month
        while first_monday.dayOfWeek() != 1:
            first_monday = first_monday.addDays(1)

        if first_monday > date:
            last_date = QDate(year, month, 1).addDays(-1)
            last_of_month = QDate(last_date.year(), last_date.month(), 1)

            first_monday = last_of_month
            while first_monday.dayOfWeek() != 1:
                first_monday = first_monday.addDays(1)

        days_diff = first_monday.daysTo(date)
        self.week_number = (days_diff // 7) + 1
        self.first_monday = first_monday

        _date = datetime.strptime(convert_to_date(date), "%Y-%m-%d")
        self.this_week_date = (_date - timedelta(days=_date.weekday())).strftime("%Y-%m-%d")
