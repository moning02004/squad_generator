from dataclasses import dataclass

from PyQt5.QtWidgets import QMessageBox


def convert_to_date(selected_date):
    return f"{selected_date.year()}-{str(selected_date.month()).zfill(2)}-{str(selected_date.day()).zfill(2)}"


def show_dialog(title, content):
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Information)
    msg.setWindowTitle(title)
    msg.setText(content)
    msg.setStandardButtons(QMessageBox.Ok)
    msg.exec_()


@dataclass
class Cache:
    team_member: int
    leader_display_row: int
    leader_cycle: int
