import sys
from pathlib import Path

# 动态添加项目根目录到系统路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.module_loader import ModuleInterface
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel

class Module(ModuleInterface):
    def __init__(self):
        super().__init__()
        self.name = "批量配置地址模块"
        self.description = "批量配置地址"
        self.version = "2.0.0"
        self.icon_path = ":/icons/traffic.png"
        self._controller = None
        self._widget = None

    def get_widget(self) -> QWidget:
        """获取模块主界面
        
        采用延迟加载策略，避免循环导入问题
        """
        if self._widget is None:
            try:
                # 先导入控制器，后导入GUI，避免循环引用
                from .Batch_configuration_of_addresses import BatchConfigController
                self._controller = BatchConfigController()
                
                try:
                    from .gui import BatchConfigWindow
                    self._widget = BatchConfigWindow(self._controller)
                except Exception as e:
                    import traceback
                    print(f"加载批量配置地址窗口失败: {str(e)}")
                    traceback.print_exc()
                    # 创建一个空窗口作为后备
                    widget = QWidget()
                    layout = QVBoxLayout(widget)
                    label = QLabel("批量配置地址模块加载失败，请检查日志")
                    label.setStyleSheet("color: red; font-size: 14px;")
                    layout.addWidget(label)
                    self._widget = widget
            except Exception as e:
                import traceback
                print(f"加载批量配置地址控制器失败: {str(e)}")
                traceback.print_exc()
                # 创建一个空窗口作为后备
                widget = QWidget()
                layout = QVBoxLayout(widget)
                label = QLabel("批量配置地址模块加载失败，请检查日志")
                label.setStyleSheet("color: red; font-size: 14px;")
                layout.addWidget(label)
                self._widget = widget
                
        return self._widget

    def get_menu_entry(self):
        return {
            "text": "批量配置地址",
            "icon": self.icon_path,
            "shortcut": "Ctrl+T",
            "action": self._show_batch_config
        }

    def _show_batch_config(self):
        """显示批量配置地址窗口"""
        # 延迟导入，确保在调用时才导入
        if self._controller is None:
            try:
                from .Batch_configuration_of_addresses import BatchConfigController
                self._controller = BatchConfigController()
            except Exception as e:
                import traceback
                print(f"加载批量配置地址控制器失败: {str(e)}")
                traceback.print_exc()
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.critical(None, "错误", "无法加载批量配置地址模块")
                return
                
        self._controller.show_window()

# 不要在这里导入具体的模块实现
# __all__ = []