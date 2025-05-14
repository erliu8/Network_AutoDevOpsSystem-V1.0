from core.module_loader import ModuleInterface
from PyQt5.QtWidgets import QWidget
from .gui import VPNConfigApp

class Module(ModuleInterface):
    def __init__(self):
        super().__init__()
        self.name = "VPN配置模块"
        self.description = "配置VPN实例和接口"
        self.version = "1.0.0"
        self.icon_path = ":/icons/vpn.png"  # 请确保有对应的图标资源

    def get_widget(self) -> QWidget:
        return VPNConfigApp()

    def get_menu_entry(self):
        return {
            "text": "VPN配置",
            "icon": self.icon_path,
            "shortcut": "Ctrl+V",
            "action": self._show_vpn_config
        }

    def _show_vpn_config(self):
        widget = self.get_widget()
        widget.show()

__all__ = ['VPNConfigApp']