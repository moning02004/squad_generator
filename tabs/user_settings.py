from datetime import datetime

from PyQt5.QtCore import Qt, QDate
from PyQt5.QtWidgets import QVBoxLayout, QTableWidgetItem, QTableWidget, QWidget, QButtonGroup, QRadioButton, \
    QHBoxLayout, QPushButton, QDialog, QLabel, QDialogButtonBox, QLineEdit, QDateEdit, QCheckBox, QSpinBox

from utils import convert_to_date


class UserSettingsTab(QWidget):
    def __init__(self, db):
        super().__init__()
        self.db = db  # 데이터베이스 객체

        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)

        # 상단 버튼 추가
        self.button_layout = QHBoxLayout()

        self.detail_button = QPushButton("상세")
        self.detail_button.clicked.connect(self.show_user_detail)
        self.detail_button.setFixedSize(50, 30)
        self.button_layout.addWidget(self.detail_button)

        self.modify_button = QPushButton("수정")
        self.modify_button.clicked.connect(self.edit_user)
        self.modify_button.setFixedSize(50, 30)
        self.button_layout.addWidget(self.modify_button)

        self.add_button = QPushButton("추가")
        self.add_button.clicked.connect(self.add_user)
        self.add_button.setFixedSize(50, 30)
        self.button_layout.addWidget(self.add_button)

        self.delete_button = QPushButton("삭제")
        self.delete_button.clicked.connect(self.delete_user)
        self.delete_button.setFixedSize(50, 30)
        self.button_layout.addWidget(self.delete_button)

        self.reload_button = QPushButton("새로고침")
        self.reload_button.clicked.connect(self.reload_users)
        self.reload_button.setFixedSize(100, 30)
        self.button_layout.addWidget(self.reload_button)
        self.button_layout.addStretch()

        self.main_layout.addLayout(self.button_layout)

        # 사용자 명단 테이블 추가
        self.user_table = QTableWidget()
        self.user_table.setColumnCount(5)
        self.user_table.setHorizontalHeaderLabels(["선택", "ID", "이름", "마지막 조장 날짜", "출력 그룹"])
        self.user_table.setEditTriggers(QTableWidget.NoEditTriggers)  # 기본적으로 편집 불가능
        self.main_layout.addWidget(self.user_table)
        self.user_table.verticalHeader().setVisible(False)

        # 사용자 목록 불러오기
        self.load_user_data()

    def load_user_data(self):
        user_data = self.db.select_users()  # 예시: DB에서 사용자 목록 불러오기
        self.user_table.setRowCount(len(user_data))
        self.user_table.cellClicked.connect(self.on_cell_clicked)
        self.user_table.verticalHeader().setVisible(True)

        self.radio_button_group = QButtonGroup(self.user_table)
        self.radio_button_group.setExclusive(True)
        for row_index, (user_id, name, last_date, enable_date, display_group) in enumerate(user_data):
            user_id_item = QTableWidgetItem(str(user_id))
            self.user_table.setItem(row_index, 0, user_id_item)

            radio_button_cell = self.create_radio_button_cell(self.radio_button_group, row_index)
            self.user_table.setCellWidget(row_index, 1, radio_button_cell)

            name_item = QTableWidgetItem(name)
            self.user_table.setItem(row_index, 2, name_item)

            last_date_item = QTableWidgetItem(str(last_date))
            self.user_table.setItem(row_index, 3, last_date_item)

            display_group_item = QTableWidgetItem(str(display_group))
            self.user_table.setItem(row_index, 4, display_group_item)
        self.user_table.setColumnHidden(0, True)

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
        self.user_table.setRowCount(0)

        # 사용자 데이터를 다시 로드
        self.load_user_data()

    def edit_user(self):
        selected_row = self.get_selected_row()
        if selected_row is not None:
            user_id = self.get_user_id(selected_row)
            name, enable_date, last_date, priority = list(self.db.select_user(user_id=user_id))
            dialog = UserEditDialog(name, enable_date, last_date, priority)
            if dialog.exec_() == QDialog.Accepted:
                user_input = dialog.get_user_input()
                self.db.update_user([user_id], **user_input)
                self.reload_users()

    def add_user(self):
        dialog = UserAddDialog()
        if dialog.exec_() == QDialog.Accepted:
            name, last_date, enable_date, priority = dialog.get_user_input()
            initial_users = [(name, last_date, enable_date, priority)]
            self.db.insert_users(initial_users)
            self.reload_users()

    def delete_user(self):
        selected_row = self.get_selected_row()
        if selected_row is not None:
            user_id = self.get_user_id(selected_row)
            self.db.delete_user(user_id)
            self.reload_users()

    def show_user_detail(self):
        selected_row = self.get_selected_row()
        if selected_row is not None:
            user_id = self.get_user_id(selected_row)
            name, enable_date, last_date, priority = list(self.db.select_user(user_id=user_id))
            self.display_user_info(name, enable_date, last_date, priority)

    def get_selected_row(self):
        for row in range(self.user_table.rowCount()):
            radio_button = self.user_table.cellWidget(row, 1)
            if radio_button and radio_button.isChecked():
                return row
        return None

    def get_user_id(self, row):
        user_id_item = self.user_table.item(row, 0)
        return user_id_item.text() if user_id_item else None

    def display_user_info(self, *user_info):
        dialog = UserDetailDialog(*user_info)
        dialog.exec_()


class UserDetailDialog(QDialog):
    def __init__(self, name, enable_date, last_date, priority):
        super().__init__()

        self.setWindowTitle("사용자 정보")
        self.setGeometry(150, 150, 500, 300)

        layout = QVBoxLayout()
        layout.setSpacing(5)

        # 세로로 표시할 항목들을 QLabel로 생성
        name_label = QLabel(f"이름: {name}", self)
        name_label.setAlignment(Qt.AlignLeft)
        layout.addWidget(name_label)

        date_label = QLabel(f"조장 가능 날짜: {enable_date}", self)
        date_label.setAlignment(Qt.AlignLeft)
        layout.addWidget(date_label)

        date_label = QLabel(f"마지막 조장 날짜: {last_date}", self)
        date_label.setAlignment(Qt.AlignLeft)
        layout.addWidget(date_label)

        date_label = QLabel(f"출력번호: {priority}", self)
        date_label.setAlignment(Qt.AlignLeft)
        layout.addWidget(date_label)
        layout.addStretch()

        self.setLayout(layout)


class UserAddDialog(QDialog):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("사용자 추가")
        self.setGeometry(100, 100, 400, 300)

        # 레이아웃 설정
        layout = QVBoxLayout()

        # 사용자 이름 입력
        name_label = QLabel("이름:")
        self.name_input = QLineEdit()
        layout.addWidget(name_label)
        layout.addWidget(self.name_input)

        # 조장 가능 날짜 선택
        date_label = QLabel("조장 가능 날짜:")
        self.enable_date = QDateEdit()
        self.enable_date.setCalendarPopup(True)
        self.enable_date.setDate(QDate.currentDate())
        layout.addWidget(date_label)
        layout.addWidget(self.enable_date)

        # 조장 가능 여부 체크박스
        self.leader_availability_checkbox = QCheckBox("조장 제외")
        layout.addWidget(self.leader_availability_checkbox)

        # 출력 순서 입력
        order_label = QLabel("출력 그룹:")
        self.order_input = QSpinBox()
        self.order_input.setMinimum(1)  # 최소값 1
        self.order_input.setMaximum(100)  # 최대값 100 (필요에 따라 조정 가능)
        self.order_input.setValue(100)
        layout.addWidget(order_label)
        layout.addWidget(self.order_input)

        # 확인 및 취소 버튼
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        layout.addWidget(button_box)
        layout.addStretch()

        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        self.setLayout(layout)

    def get_user_input(self):
        user_name = self.name_input.text().strip()
        enable_date = convert_to_date(self.enable_date.date().addDays(-self.enable_date.date().dayOfWeek() + 1))
        enable_date = "9999-12-31" if self.leader_availability_checkbox.isChecked() else enable_date
        priority = self.order_input.value()

        return user_name, enable_date, enable_date, priority


class UserEditDialog(QDialog):
    def __init__(self, name, enable_date, last_date, priority):
        super().__init__()

        self.setWindowTitle("사용자 수정")
        self.setGeometry(100, 100, 300, 200)

        # 레이아웃 설정
        layout = QVBoxLayout()

        name_layout = QHBoxLayout()
        name_label = QLabel("이름:")
        self.name_input = QLineEdit()
        self.name_input.setText(name)
        self.name_input.setPlaceholderText("이름을 입력하세요.")
        name_layout.addWidget(name_label)
        name_layout.addWidget(self.name_input)
        layout.addLayout(name_layout)

        # 날짜 선택 위젯
        date_label = QLabel("조장 가능일:")
        self.enable_date = QDateEdit()
        self.enable_date.setCalendarPopup(True)  # 캘린더 팝업 활성화
        self.enable_date.setDate(QDate.fromString(enable_date, "yyyy-MM-dd"))
        layout.addWidget(date_label)
        layout.addWidget(self.enable_date)

        # 날짜 선택 위젯
        date_label = QLabel("최근 조장일:")
        self.recent_date = QDateEdit()
        self.recent_date.setCalendarPopup(True)  # 캘린더 팝업 활성화
        self.recent_date.setDate(QDate.fromString(last_date, "yyyy-MM-dd"))
        layout.addWidget(date_label)
        layout.addWidget(self.recent_date)

        # 출력 순서 입력
        order_label = QLabel("출력 그룹:")
        self.order_input = QSpinBox()
        self.order_input.setMinimum(1)  # 최소값 1
        self.order_input.setMaximum(100)  # 최대값 100 (필요에 따라 조정 가능)
        self.order_input.setValue(priority)
        layout.addWidget(order_label)
        layout.addWidget(self.order_input)

        # 날짜 선택 도움말
        date_help_text = QLabel("※ 해당 일의 월요일이 입력됩니다.")
        date_help_text.setStyleSheet("color: gray; font-size: 10pt;")  # 스타일 지정
        layout.addWidget(date_help_text)
        layout.addStretch()
        self.leader_availability_label = QLabel("조장 가능 여부:")
        self.leader_availability_checkbox = QCheckBox("조장 제외")
        layout.addWidget(self.leader_availability_label)
        layout.addWidget(self.leader_availability_checkbox)

        self.setLayout(layout)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        layout.addWidget(button_box)

        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

    def get_user_input(self):
        user_name = self.name_input.text().strip()
        enable_date = convert_to_date(self.enable_date.date().addDays(-self.enable_date.date().dayOfWeek() + 1))
        recent_date = convert_to_date(self.recent_date.date().addDays(-self.recent_date.date().dayOfWeek() + 1))
        enable_date = "9999-12-31" if self.leader_availability_checkbox.isChecked() else enable_date
        recent_date = "9999-12-31" if self.leader_availability_checkbox.isChecked() else recent_date

        return {
            "name": user_name,
            "enable_date": enable_date,
            "last_date": recent_date,
            "priority": self.order_input.value()
        }
