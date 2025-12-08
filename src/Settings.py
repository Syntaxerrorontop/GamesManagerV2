from PyQt5.QtWidgets import QWidget, QVBoxLayout, QCheckBox, QLabel
from .utility.utility_functions import load_json, save_json
from .utility.utility_vars import CONFIG_FOLDER
import os

class Settings(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.userconfig = load_json(os.path.join(CONFIG_FOLDER, "userconfig.json"))
        
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        title = QLabel("Settings")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(title)

        self.autoupdate_checkbox = QCheckBox("Enable Autoupdates")
        self.autoupdate_checkbox.setChecked(self.userconfig.get("autoupdates", False))
        self.autoupdate_checkbox.stateChanged.connect(self.autoupdate_changed)
        layout.addWidget(self.autoupdate_checkbox)

    def autoupdate_changed(self, state):
        self.userconfig["autoupdates"] = bool(state)
        save_json(os.path.join(CONFIG_FOLDER, "userconfig.json"), self.userconfig)
