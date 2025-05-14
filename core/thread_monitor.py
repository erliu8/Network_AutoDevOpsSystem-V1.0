# thread_monitor.py - 线程监控模块入口
import sys
import os
from pathlib import Path
import threading
import time

# 添加项目根目录到系统路径
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from PyQt5.QtWidgets import QApplication, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTabWidget, QWidget, QComboBox, QTableWidget, QHeaderView, QTextEdit
from PyQt5.QtCore import Qt

# 导入线程监控类
from core.business.thread_monitor import ThreadMonitor, ThreadMonitorWindow

class ThreadMonitorDialog(QDialog):
    """线程监控对话框，用于展示线程监控信息"""
    
    def __init__(self, thread_factory=None, parent=None):
        """
        初始化线程监控对话框
        
        参数:
            thread_factory: 线程工厂实例
            parent: 父窗口
        """
        super().__init__(parent)
        self.setWindowTitle("线程监控")
        self.setMinimumSize(900, 600)
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint | Qt.WindowMinimizeButtonHint)
        
        if thread_factory is None:
            # 没有传入线程工厂实例，创建一个默认实例
            from core.business.thread_factory import ThreadFactory
            thread_factory = ThreadFactory.get_instance()
            print(f"使用默认线程工厂，ID: {id(thread_factory)}")
        else:
            print(f"使用传入的线程工厂，ID: {id(thread_factory)}")
        
        # 创建线程监控窗口
        self.monitor_window = ThreadMonitorWindow(self)
        
        # 设置线程工厂
        self.monitor_window.thread_monitor.thread_factory = thread_factory
        
        # 设置布局
        layout = QVBoxLayout(self)
        layout.addWidget(self.monitor_window)
        
        # 底部按钮
        bottom_layout = QHBoxLayout()
        
        # 创建测试线程按钮
        self.test_btn = QPushButton("创建测试线程")
        self.test_btn.clicked.connect(self.create_test_threads)
        bottom_layout.addWidget(self.test_btn)
        
        # 强制刷新按钮
        self.force_refresh_btn = QPushButton("强制刷新")
        self.force_refresh_btn.clicked.connect(self.force_refresh_threads)
        bottom_layout.addWidget(self.force_refresh_btn)
        
        # 显示所有线程按钮
        self.show_all_btn = QPushButton("显示所有线程")
        self.show_all_btn.clicked.connect(self.show_all_threads)
        bottom_layout.addWidget(self.show_all_btn)
        
        # 刷新按钮
        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.clicked.connect(self.monitor_window.refresh_threads)
        bottom_layout.addWidget(self.refresh_btn)
        
        # 关闭按钮
        self.close_btn = QPushButton("关闭")
        self.close_btn.clicked.connect(self.accept)
        bottom_layout.addWidget(self.close_btn)
        
        layout.addLayout(bottom_layout)
        
        # 强制刷新一次
        self.force_refresh_threads()
        
        # 立即进行一次全面的线程检查，确保捕获已有线程
        self.monitor_window.refresh_threads()
        
        # 开始监控
        self.monitor_window.monitor_btn.click()  # 自动点击开始监控按钮

    def create_test_threads(self):
        """创建测试线程"""
        # 使用已存在的线程工厂
        thread_factory = self.monitor_window.thread_monitor.thread_factory
        print(f"创建测试线程, 使用线程工厂ID: {id(thread_factory)}")
        
        import threading
        import time
        
        # 创建不同类型的测试线程
        modules = [
            "dhcp_configuration", 
            "vpn_deploy", 
            "route_configuration",
            "Batch_configuration_of_addresses", 
            "network_monitor"
        ]
        
        # 测试线程函数
        def test_thread_function(name, sleep_time):
            print(f"测试线程 {name} 启动，系统线程ID: {threading.current_thread().ident}")
            for i in range(10):
                print(f"线程 {name} 正在工作: {i+1}/10")
                time.sleep(sleep_time)
            print(f"测试线程 {name} 完成")
        
        # 创建测试线程
        for i, module in enumerate(modules):
            thread_name = f"{module.capitalize()}_TestThread_{i+1}"
            thread_id = thread_factory.start_thread(
                target=test_thread_function,
                args=(thread_name, i+1),
                name=thread_name,
                daemon=True,
                module=module
            )
            print(f"已创建测试线程: {thread_name}, ID: {thread_id}")
        
        # 立即刷新显示
        self.force_refresh_threads()
    
    def force_refresh_threads(self):
        """强制刷新线程列表"""
        print("正在强制刷新线程列表...")
        # 获取当前所有线程
        import threading
        threads = threading.enumerate()
        print(f"当前系统中的线程数: {len(threads)}")
        for t in threads:
            print(f"- {t.name} (ID: {t.ident})")
        
        # 获取线程工厂注册的线程
        thread_factory = self.monitor_window.thread_monitor.thread_factory
        factory_threads = thread_factory.threads
        print(f"线程工厂中注册的线程数: {len(factory_threads)}")
        for thread_id, info in factory_threads.items():
            print(f"- {info['name']} (ID: {thread_id}, 模块: {info['module']})")
        
        # 执行一次完整的线程检查
        print("执行完整线程检查...")
        monitor = self.monitor_window.thread_monitor
        monitor.check_threads()
        
        # 刷新UI
        print("刷新UI显示...")
        self.monitor_window.refresh_threads()
        
        # 输出线程监控器中当前的线程
        monitor_threads = monitor.threads
        print(f"线程监控器中的线程数: {len(monitor_threads)}")
        for thread_id, info in monitor_threads.items():
            print(f"- {info.name} (ID: {thread_id}, 模块: {info.module})")

    def show_all_threads(self):
        """显示所有线程，不管模块"""
        self.monitor_window.module_combo.setCurrentIndex(0)  # "所有模块"
        self.monitor_window.filter_threads()
        
        # 强制刷新一次
        self.force_refresh_threads()

if __name__ == "__main__":
    # 单独运行时的测试代码
    app = QApplication(sys.argv)
    dialog = ThreadMonitorDialog()
    dialog.exec_() 