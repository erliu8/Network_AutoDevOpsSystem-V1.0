from core.module_loader import ModuleInterface
from PyQt5.QtWidgets import QWidget

class Module(ModuleInterface):
    def __init__(self):
        super().__init__()
        self.name = "任务审批模块"
        self.description = "审批来自Web界面的任务请求"
        self.version = "1.0.0"
        self.icon_path = ":/icons/approve.png"

    def get_widget(self) -> QWidget:
        from .gui import ApprovalWindow
        return ApprovalWindow()

    def get_menu_entry(self):
        return {
            "text": "任务审批",
            "icon": self.icon_path,
            "shortcut": "Ctrl+A",
            "action": self._show_approval
        }

    def _show_approval(self):
        self.get_widget().show() 