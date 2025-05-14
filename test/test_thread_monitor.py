#!/usr/bin/env python
# test_thread_monitor.py - 线程监控测试脚本
import sys
import threading
import time
from PyQt5.QtWidgets import QApplication

# 导入线程监控对话框
from core.thread_monitor import ThreadMonitorDialog
from core.business.thread_factory import ThreadFactory

def test_thread_function(name, sleep_time):
    """测试线程函数"""
    print(f"测试线程 {name} 启动, 休眠时间: {sleep_time}秒")
    # 模拟线程工作
    for i in range(10):
        print(f"线程 {name} 正在工作: {i+1}/10")
        time.sleep(sleep_time)
    print(f"测试线程 {name} 完成工作")

def create_test_threads():
    """创建测试线程"""
    thread_factory = ThreadFactory.get_instance()
    
    # 创建不同类型的测试线程
    modules = [
        "dhcp_configuration", 
        "vpn_deploy", 
        "route_configuration",
        "Batch_configuration_of_addresses", 
        "network_monitor"
    ]
    
    print("正在创建测试线程...")
    
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
        print(f"启动测试线程: {thread_name}, ID: {thread_id}")
    
    # 打印当前所有线程
    print("\n当前Python线程:")
    for t in threading.enumerate():
        print(f"- {t.name} (ID: {t.ident})")
    
    print("\n线程工厂注册的线程:")
    for thread_id, info in thread_factory.threads.items():
        print(f"- {info['name']} (ID: {thread_id}, 模块: {info['module']})")

if __name__ == "__main__":
    # 创建应用
    app = QApplication(sys.argv)
    
    # 先创建测试线程
    create_test_threads()
    
    # 显示线程监控对话框
    dialog = ThreadMonitorDialog()
    
    # 检查线程数量
    print(f"\n线程工厂中的线程数: {dialog.monitor_window.thread_monitor.thread_factory.get_thread_count()}")
    print(f"线程监控器中的线程数: {len(dialog.monitor_window.thread_monitor.threads)}")
    
    # 显示对话框
    dialog.exec_()
    
    # 退出应用
    sys.exit(0) 