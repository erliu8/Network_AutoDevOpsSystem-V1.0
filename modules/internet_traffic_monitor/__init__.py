import sys
from pathlib import Path

# 动态添加项目根目录到系统路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.module_loader import ModuleInterface
from PyQt5.QtWidgets import QWidget
from .gui import TrafficMonitorApp

class Module(ModuleInterface):
    def __init__(self):
        super().__init__()
        self.name = "流量监控模块"
        self.description = "网络接口流量实时监控"
        self.version = "2.0.0"
        self.icon_path = ":/icons/traffic.png"

    def get_widget(self) -> QWidget:
        return TrafficMonitorApp()

    def get_menu_entry(self):
        return {
            "text": "流量监控",
            "icon": self.icon_path,
            "shortcut": "Ctrl+T",
            "action": self._show_traffic_monitor
        }

    def _show_traffic_monitor(self):
        widget = self.get_widget()
        widget.show()  # 修改为直接调用show方法


__all__ = ['TrafficMonitorApp']
# 删除这一行，避免循环导入
# __all__ = ['ENSPMonitor']