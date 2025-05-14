#!/usr/bin/env python
# thread_monitor_launcher.py - 启动线程监控对话框
import sys
import os
from pathlib import Path

# 确保可以导入核心模块
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.append(root_dir)

from PyQt5.QtWidgets import QApplication
from core.business.thread_monitor_dialog import ThreadMonitorDialog
from core.business.thread_factory import ThreadFactory

def launch_thread_monitor(parent=None):
    """启动线程监控对话框"""
    # 初始化线程工厂（如果尚未初始化）
    thread_factory = ThreadFactory.get_instance()
    
    # 创建并显示线程监控对话框
    dialog = ThreadMonitorDialog(parent)
    dialog.show()
    return dialog

if __name__ == "__main__":
    # 直接运行此脚本时，启动线程监控对话框
    app = QApplication(sys.argv)
    window = launch_thread_monitor()
    sys.exit(app.exec_()) 