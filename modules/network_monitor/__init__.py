import sys
from pathlib import Path

# 添加项目根目录到系统路径
sys.path.append(str(Path(__file__).parent.parent.parent))

from core.module_loader import ModuleInterface
from PyQt5.QtWidgets import QWidget
from .gui import AutoMaintainGUI

class Module(ModuleInterface):
    def __init__(self):
        super().__init__()
        self.name = "设备状态模块"  # 明确设置中文模块名称
        self.description = "网络设备实时状态监控"
        self.version = "2.1.0"
        self.icon_path = ":/icons/network.png"  # 确保资源存在

    def get_widget(self) -> QWidget:
        widget = get_main_widget()
        widget.setObjectName("network_monitor")  # 设置与元数据键一致
        return widget  # 返回实际的界面组件

    def get_menu_entry(self) -> dict:
        """自定义菜单项"""
        return {
            "text": "网络监控",
            "icon": self.icon_path,
            "shortcut": "Ctrl+N",
            "action": self._show_network_monitor
        }

    def _show_network_monitor(self):
        """自定义菜单动作"""
        widget = self.get_widget()
        widget.show()


def get_main_widget():
    return AutoMaintainGUI()