from core.module_loader import ModuleInterface
from PyQt5.QtWidgets import QWidget

class Module(ModuleInterface):
    def __init__(self):
        super().__init__()
        self.name = "DHCP配置模块"
        self.description = "DHCP服务配置"
        self.version = "1.0.0"
        self.icon_path = ":/icons/dhcp.png"

    def get_widget(self) -> QWidget:
        from .gui import DHCPConfigWindow
        return DHCPConfigWindow()

    def get_menu_entry(self):
        return {
            "text": "DHCP配置",
            "icon": self.icon_path,
            "shortcut": "Ctrl+D",
            "action": self._show_config
        }

    def _show_config(self):
        self.get_widget().show()