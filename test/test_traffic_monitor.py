#!/usr/bin/env python
# test_traffic_monitor.py - 测试网络流量监控模块
import sys
import os
import time
import argparse
from pathlib import Path

# 添加项目根目录到系统路径
root_dir = str(Path(__file__).parent)
sys.path.append(root_dir)

def test_cli_mode(device_ip, username, password, duration=60, debug=False):
    """命令行测试模式，不启动GUI，直接测试ENSPMonitor功能"""
    from PyQt5.QtCore import QCoreApplication
    from modules.internet_traffic_monitor.internet_traffic_monitor import ENSPMonitor
    
    # 创建一个简单的应用程序来处理信号
    app = QCoreApplication(sys.argv)
    
    # 定义信号回调函数
    def on_traffic_data(data):
        if debug:
            print("\n收到流量数据:")
            for interface, stats in data.items():
                print(f"接口: {interface}")
                print(f"  - 入站: {stats['input']} bytes/sec")
                print(f"  - 出站: {stats['output']} bytes/sec")
            print("-" * 50)
    
    def on_status_change(device_ip, status):
        print(f"设备 {device_ip} 状态: {status}")
    
    def on_data_updated(data):
        print(f"\n数据更新信号: 收到 {len(data)} 个接口的流量数据")
        for interface, stats in data.items():
            print(f"接口: {interface}")
            print(f"  - 入站: {stats['input']} bytes/sec")
            print(f"  - 出站: {stats['output']} bytes/sec")
        print("-" * 50)
    
    # 创建监控实例
    print("创建ENSPMonitor实例...")
    monitor = ENSPMonitor(ip=device_ip, username=username, password=password)
    
    # 连接信号
    monitor.traffic_data.connect(on_traffic_data)
    monitor.status_signal.connect(on_status_change)
    monitor.data_updated.connect(on_data_updated)
    
    # 开始监控
    print(f"开始监控设备 {device_ip} 的流量...")
    monitor.start_monitoring()
    
    # 让监控运行一段时间
    try:
        print(f"监控已启动，将运行 {duration} 秒。按Ctrl+C提前停止...")
        # 运行指定秒数或直到中断
        interval = 5
        for i in range(duration // interval):
            time.sleep(interval)
            print(f"仍在监控中... ({(i+1)*interval}/{duration} 秒)")
    except KeyboardInterrupt:
        print("测试被用户中断")
    finally:
        # 停止监控
        print("停止流量监控...")
        monitor.stop_monitoring()
        print("测试完成.")

def test_gui_mode():
    """启动GUI测试模式"""
    from PyQt5.QtWidgets import QApplication
    from modules.internet_traffic_monitor.gui import TrafficMonitorApp
    
    # 创建QApplication实例
    app = QApplication(sys.argv)
    
    # 创建流量监控窗口
    window = TrafficMonitorApp()
    
    # 显示窗口
    window.show()
    
    # 打印提示
    print("测试界面已准备就绪。")
    print("请按照以下步骤测试:")
    print("1. 从下拉菜单中选择一个网络设备")
    print("2. 点击\"启动监控\"按钮开始监控设备接口流量")
    print("3. 观察图表动态更新，显示各接口的入站和出站流量")
    print("4. 测试完成后，点击\"停止监控\"按钮停止监控")
    
    # 执行应用程序主循环
    sys.exit(app.exec_())

def main():
    print("============================================")
    print("         网络流量监控模块测试程序")
    print("============================================")
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='测试网络流量监控模块')
    parser.add_argument('--ip', default='10.1.200.1', help='设备IP地址')
    parser.add_argument('--username', default='1', help='登录用户名')
    parser.add_argument('--password', default='1', help='登录密码')
    parser.add_argument('--duration', type=int, default=30, help='测试持续时间(秒)')
    parser.add_argument('--gui', action='store_true', help='使用GUI模式测试')
    parser.add_argument('--debug', action='store_true', help='显示调试信息')
    
    args = parser.parse_args()
    
    if args.gui:
        print("启动GUI测试模式...")
        test_gui_mode()
    else:
        print("启动命令行测试模式...")
        test_cli_mode(args.ip, args.username, args.password, args.duration, args.debug)

if __name__ == "__main__":
    main()