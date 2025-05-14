#!/usr/bin/env python
# debug_thread_monitor.py - 线程监控调试脚本
import sys
import threading
import time
import os
from PyQt5.QtWidgets import QApplication, QPushButton, QVBoxLayout, QWidget, QLabel

# 导入线程监控对话框
from core.thread_monitor import ThreadMonitorDialog
from core.business.thread_factory import ThreadFactory
from core.business.thread_monitor import ThreadMonitor

class DebugWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("线程监控调试窗口")
        self.setGeometry(100, 100, 500, 300)
        
        # 创建布局
        layout = QVBoxLayout(self)
        
        # 获取线程工厂
        self.thread_factory = ThreadFactory.get_instance()
        
        # 线程工厂信息
        factory_label = QLabel(f"线程工厂ID: {id(self.thread_factory)}")
        layout.addWidget(factory_label)
        
        # 当前线程信息
        thread_info = QLabel(f"主线程ID: {threading.current_thread().ident}")
        layout.addWidget(thread_info)
        
        # 创建测试线程按钮
        create_thread_btn = QPushButton("创建测试线程")
        create_thread_btn.clicked.connect(self.create_test_threads)
        layout.addWidget(create_thread_btn)
        
        # 显示线程监控按钮
        show_monitor_btn = QPushButton("显示线程监控")
        show_monitor_btn.clicked.connect(self.show_monitor)
        layout.addWidget(show_monitor_btn)
        
        # 状态信息
        self.status_label = QLabel("准备就绪")
        layout.addWidget(self.status_label)
        
        # 保存对话框引用
        self.dialog = None
    
    def create_test_threads(self):
        """创建测试线程"""
        self.status_label.setText("正在创建测试线程...")
        
        # 创建不同类型的测试线程
        modules = [
            "dhcp_configuration", 
            "vpn_deploy", 
            "route_configuration",
            "Batch_configuration_of_addresses", 
            "network_monitor"
        ]
        
        # 创建测试线程
        for i, module in enumerate(modules):
            thread_name = f"{module.capitalize()}_TestThread_{i+1}"
            thread_id = self.thread_factory.start_thread(
                target=self.test_thread_function,
                args=(thread_name, i+1),
                name=thread_name,
                daemon=True,
                module=module
            )
            print(f"启动测试线程: {thread_name}, ID: {thread_id}")
        
        # 打印当前所有线程
        print("\n当前Python线程:")
        threads = threading.enumerate()
        for t in threads:
            print(f"- {t.name} (ID: {t.ident})")
        
        print("\n线程工厂注册的线程:")
        for thread_id, info in self.thread_factory.threads.items():
            print(f"- {info['name']} (ID: {thread_id}, 模块: {info['module']})")
        
        self.status_label.setText(f"已创建 {len(modules)} 个测试线程，当前总线程数: {len(threads)}")
    
    def test_thread_function(self, name, sleep_time):
        """测试线程函数"""
        print(f"测试线程 {name} 启动, 休眠时间: {sleep_time}秒")
        thread_id = threading.current_thread().ident
        print(f"线程 {name} 的系统ID: {thread_id}")
        
        # 模拟线程工作
        for i in range(10):
            print(f"线程 {name} 正在工作: {i+1}/10")
            time.sleep(sleep_time)
        print(f"测试线程 {name} 完成工作")
    
    def show_monitor(self):
        """显示线程监控对话框"""
        self.status_label.setText("正在打开线程监控...")
        
        # 检查线程工厂中的线程数
        thread_count = self.thread_factory.get_thread_count()
        print(f"打开监控前的线程工厂线程数: {thread_count}")
        print(f"线程工厂ID: {id(self.thread_factory)}")
        
        # 创建并显示对话框
        self.dialog = ThreadMonitorDialog(thread_factory=self.thread_factory)
        
        # 检查对话框中的线程监控器线程工厂ID
        monitor_factory_id = id(self.dialog.monitor_window.thread_monitor.thread_factory)
        print(f"对话框的线程工厂ID: {monitor_factory_id}")
        
        # 检查线程监控中的线程数
        monitor_thread_count = len(self.dialog.monitor_window.thread_monitor.threads)
        print(f"线程监控器中的线程数: {monitor_thread_count}")
        
        # 打印所有被监控的线程
        threads = self.dialog.monitor_window.thread_monitor.threads
        print("\n线程监控器中的线程:")
        for thread_id, thread_info in threads.items():
            print(f"- {thread_info.name} (ID: {thread_id}, 模块: {thread_info.module})")
        
        # 手动进行一次线程检查
        print("\n执行线程检查...")
        self.dialog.monitor_window.thread_monitor.check_threads()
        
        # 再次检查线程数
        monitor_thread_count = len(self.dialog.monitor_window.thread_monitor.threads)
        print(f"线程检查后的线程监控器中的线程数: {monitor_thread_count}")
        
        # 更新状态
        self.status_label.setText(f"线程监控已打开，检测到 {monitor_thread_count} 个线程")
        
        # 显示对话框
        self.dialog.exec_()

if __name__ == "__main__":
    # 创建应用
    app = QApplication(sys.argv)
    
    # 创建并显示调试窗口
    window = DebugWindow()
    window.show()
    
    # 退出应用
    sys.exit(app.exec_()) 