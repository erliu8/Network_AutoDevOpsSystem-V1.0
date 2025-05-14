import sys
from pathlib import Path

# 动态添加项目根目录到系统路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.module_loader import ModuleInterface
from PyQt5.QtWidgets import QWidget
from .gui import DeviceInfoQueryWindow
from .Query_device_information import DeviceConnector, DEVICE_DATA, PREDEFINED_COMMANDS

class Module(ModuleInterface):
    def __init__(self):
        super().__init__()
        self.name = "设备信息查询模块"
        self.description = "查询网络设备信息和执行命令"
        self.version = "1.0.0"
        self.icon_path = ":/icons/query.png"  # 确保有对应的图标资源

    def get_widget(self) -> QWidget:
        return DeviceInfoQueryWindow()

    def get_menu_entry(self):
        return {
            "text": "设备信息查询",
            "icon": self.icon_path,
            "shortcut": "Ctrl+Q",
            "action": self._show_device_query
        }

    def _show_device_query(self):
        widget = self.get_widget()
        widget.show()

# 导出类，便于其他模块导入
__all__ = ['DeviceInfoQueryWindow', 'DeviceConnector', 'DEVICE_DATA', 'PREDEFINED_COMMANDS']