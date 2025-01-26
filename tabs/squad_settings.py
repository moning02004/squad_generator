from datetime import datetime

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
        self.squad_table.setColumnCount(3)
        self.squad_table.setHorizontalHeaderLabels(["선택", "date_label", "leaders"])
        self.squad_table.setEditTriggers(QTableWidget.NoEditTriggers)  # 기본적으로 편집 불가능
        self.main_layout.addWidget(self.squad_table)
        self.squad_table.verticalHeader().setVisible(False)

        # 사용자 목록 불러오기
        self.load_user_data()

    def load_user_data(self):
        user_data = self.db.select_team_history()
        self.squad_table.setRowCount(len(user_data))
        self.squad_table.cellClicked.connect(self.on_cell_clicked)
        self.squad_table.verticalHeader().setVisible(True)

        self.radio_button_group = QButtonGroup(self.squad_table)
        self.radio_button_group.setExclusive(True)
        for row_index, (squad_id, date_label, leader_ids) in enumerate(user_data):
            radio_button_cell = self.create_radio_button_cell(self.radio_button_group, row_index)
            self.squad_table.setCellWidget(row_index, 0, radio_button_cell)
            self.squad_table.setColumnWidth(0, 100)

            name_item = QTableWidgetItem(date_label)
            self.squad_table.setItem(row_index, 1, name_item)
            self.squad_table.setColumnWidth(1, 200)

            last_date_item = QTableWidgetItem(str(leader_ids))
            self.squad_table.setItem(row_index, 2, last_date_item)
            self.squad_table.setColumnWidth(2, 200)

    def on_cell_clicked(self, row, column):
        # 첫 번째 열(선택 칸)인 경우 라디오 버튼 선택
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
        selected_row = self.get_selected_row()
        if selected_row is not None:
            date_label = self.get_date_label(selected_row)
            self.db.delete_team_history(date_label)
            self.reload_users()

    def get_selected_row(self):
        for row in range(self.squad_table.rowCount()):
            radio_button = self.squad_table.cellWidget(row, 0)
            if radio_button and radio_button.isChecked():
                return row
        return None

    def get_date_label(self, row):
        id_item = self.squad_table.item(row, 1)
        return id_item.text() if id_item else None
