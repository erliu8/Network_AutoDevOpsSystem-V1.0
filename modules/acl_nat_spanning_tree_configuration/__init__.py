import sys
from pathlib import Path

# 动态添加项目根目录到系统路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.module_loader import ModuleInterface
from PyQt5.QtWidgets import QWidget

class Module(ModuleInterface):
    def __init__(self):
        super().__init__()
        self.name = "ACL/NAT/生成树配置模块"
        self.description = "配置ACL、NAT和生成树协议"
        self.version = "1.0.0"
        self.icon_path = ":/icons/config.png"

    def get_widget(self) -> QWidget:
        # 延迟导入，避免循环导入
        from .gui import ConfigurationWindow
        return ConfigurationWindow()

    def get_menu_entry(self):
        return {
            "text": "ACL/NAT/生成树配置",
            "icon": self.icon_path,
            "shortcut": "Ctrl+A",
            "action": self._show_config_window
        }

    def _show_config_window(self):
        widget = self.get_widget()
        widget.show()

# 导出类，便于其他模块导入
__all__ = ['ConfigurationWindow']