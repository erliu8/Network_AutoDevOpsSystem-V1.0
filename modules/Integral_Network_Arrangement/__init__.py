import sys
from pathlib import Path

# 动态添加项目根目录到系统路径
# 注意：这里的路径深度可能需要根据实际项目结构调整
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from core.module_loader import ModuleInterface
from PyQt5.QtWidgets import QWidget
# 修正导入，使用正确的类名
from .NetworkTopology import NetworkTopologyView

class Module(ModuleInterface):
    def __init__(self):
        super().__init__()
        self.name = "整体网络编排"  # 模块的显示名称
        self.description = "提供网络拓扑可视化和监控功能"
        self.version = "1.0.0"
        # 你可以为模块指定一个图标，确保资源文件已正确配置
        self.icon_path = ":/icons/topology.png" # 假设图标路径，如果不存在请修改或移除

    def get_widget(self) -> QWidget:
        """返回模块的主界面组件"""
        # 实例化并返回主窗口部件
        widget = NetworkTopologyView()
        # 为 widget 设置一个 objectName，方便识别和管理
        widget.setObjectName("integral_network_arrangement")
        return widget

    def get_menu_entry(self) -> dict:
        """返回要在菜单中显示的条目信息（如果需要在菜单中添加）"""
        # 如果你希望在菜单栏（例如"工具"菜单）中添加一个入口点，
        # 可以取消注释下面的代码并实现 _show_module 方法。
        # 如果只想在主界面的标签页中显示，可以返回 None 或一个空字典。
        return {
           "text": self.name,
           "icon": self.icon_path,
           "shortcut": "Ctrl+Shift+T", # 可选快捷键
           "action": self._show_module # 点击菜单项时执行的方法
        }
        # return None # 如果不需要菜单项

    def _show_module(self):
        """显示模块窗口（如果通过菜单触发）"""
        # 这个方法通常用于独立窗口或特殊显示逻辑
        # 对于标签页模式，主程序会自动处理 get_widget() 返回的组件
        widget = self.get_widget()
        # 如果希望它作为独立窗口显示，可以调用 show()
        # widget.show()
        # 但在当前标签页模式下，通常不需要在这里做什么
        print(f"通过菜单启动 {self.name}...")
        # 你可能需要通知主窗口将这个 widget 添加到标签页或以其他方式显示
        # 这取决于主窗口的设计

# 导出主窗口类，如果其他地方需要直接导入
__all__ = ['NetworkTopologyView']