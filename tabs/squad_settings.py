from datetime import datetime, timedelta

from PyQt5.QtCore import Qt, QDate
from PyQt5.QtWidgets import QVBoxLayout, QTableWidgetItem, QTableWidget, QWidget, QButtonGroup, QRadioButton, \
    QHBoxLayout, QPushButton, QDialog, QLabel, QDialogButtonBox, QLineEdit, QDateEdit, QCheckBox, QSpinBox, QHeaderView

from utils import convert_to_date


class SquadSettingsTab(QWidget):
    def __init__(self, db):
        super().__init__()
        self.db = db  # 데이터베이스 객체

        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)

        # 상단 버튼 추가
        self.button_layout = QHBoxLayout()

        self.delete_button = QPushButton("삭제")
        self.delete_button.clicked.connect(self.delete_squad_data)
        self.delete_button.setFixedSize(50, 30)
        self.button_layout.addWidget(self.delete_button)

        self.reload_button = QPushButton("새로고침")
        self.reload_button.clicked.connect(self.reload_users)
        self.reload_button.setFixedSize(100, 30)
        self.button_layout.addWidget(self.reload_button)
        self.button_layout.addStretch()

        self.main_layout.addLayout(self.button_layout)

        # 사용자 명단 테이블 추가
        self.squad_table = QTableWidget()
        self.squad_table.setColumnCount(4)
        self.squad_table.setHorizontalHeaderLabels(["선택", "date_label", "leaders", "date_text"])
        self.squad_table.setEditTriggers(QTableWidget.NoEditTriggers)  # 기본적으로 편집 불가능
        self.main_layout.addWidget(self.squad_table)
        self.squad_table.verticalHeader().setVisible(False)

        # 사용자 목록 불러오기
        self.load_user_data()

    def load_user_data(self):
        self.delete_button.setEnabled(True)

        user_data = self.db.select_team_history()
        self.squad_table.setRowCount(len(user_data))
        self.squad_table.cellClicked.connect(self.on_cell_clicked)
        self.squad_table.verticalHeader().setVisible(True)

        self.radio_button_group = QButtonGroup(self.squad_table)
        self.radio_button_group.setExclusive(True)
        for row_index, (squad_id, date_label, leader_ids, date_text) in enumerate(user_data):
            radio_button_cell = self.create_radio_button_cell(self.radio_button_group, row_index)
            self.squad_table.setCellWidget(row_index, 0, radio_button_cell)
            self.squad_table.setColumnWidth(0, 100)

            name_item = QTableWidgetItem(date_label)
            self.squad_table.setItem(row_index, 1, name_item)
            self.squad_table.setColumnWidth(1, 200)

            last_date_item = QTableWidgetItem(str(leader_ids))
            self.squad_table.setItem(row_index, 2, last_date_item)
            self.squad_table.setColumnWidth(2, 200)

            date_text_item = QTableWidgetItem(str(date_text))
            self.squad_table.setItem(row_index, 3, date_text_item)
            self.squad_table.setColumnWidth(3, 200)

    def on_cell_clicked(self, row, column):
        if column == 0:
            radio_button = self.user_table.cellWidget(row, column)
            if radio_button:
                radio_button.setChecked(True)

    def create_radio_button_cell(self, button_group, row_index):
        radio_button = QRadioButton()
        radio_button.setStyleSheet("margin: auto;")
        button_group.addButton(radio_button, row_index)
        return radio_button

    def reload_users(self):
        # 테이블의 데이터를 초기화
        self.squad_table.setRowCount(0)

        # 사용자 데이터를 다시 로드
        self.load_user_data()

    def delete_squad_data(self):
        current_date = datetime.now()
        year, month = map(int, current_date.strftime("%Y %m").split(" "))
        first_of_month = QDate(year, month, 1)

        first_monday = first_of_month
        while first_monday.dayOfWeek() != 1:
            first_monday = first_monday.addDays(1)

        if first_monday > current_date:
            last_date = QDate(year, month, 1).addDays(-1)
            last_of_month = QDate(last_date.year(), last_date.month(), 1)

            first_monday = last_of_month
            while first_monday.dayOfWeek() != 1:
                first_monday = first_monday.addDays(1)
        this_week_date = (current_date - timedelta(days=current_date.weekday())).strftime("%Y-%m-%d")

        selected_row = self.get_selected_row()
        if selected_row is not None:
            self.delete_button.setEnabled(False)

            date_label, date_text = self.get_data(selected_row)
            if this_week_date <= date_text:
                self.db.delete_team_history(date_label)
                self.reload_users()

    def get_selected_row(self):
        for row in range(self.squad_table.rowCount()):
            radio_button = self.squad_table.cellWidget(row, 0)
            if radio_button and radio_button.isChecked():
                return row
        return None

    def get_data(self, row):
        id_item = self.squad_table.item(row, 1)
        date_text = self.squad_table.item(row, 3)
        return (id_item.text(), date_text.text()) if id_item else (None, None)
