#!/usr/bin/env python
# test_direct_ensp_monitor.py - 直接测试ENSPMonitor连接
import sys
import time
from pathlib import Path

# 添加项目根目录到系统路径
root_dir = str(Path(__file__).parent)
sys.path.append(root_dir)

from PyQt5.QtCore import QCoreApplication
from modules.internet_traffic_monitor.internet_traffic_monitor import ENSPMonitor

def main():
    print("============================================")
    print("      ENSPMonitor直接测试程序 (Telnet)      ")
    print("============================================")
    
    # 创建QApplication实例
    app = QCoreApplication(sys.argv)
    
    # 使用命令行参数或者默认值
    if len(sys.argv) > 1:
        device_ip = sys.argv[1]
    else:
        device_ip = "192.168.10.1"  # 默认IP
    
    username = "1"
    password = "1"
    
    print(f"测试设备: {device_ip}")
    print(f"用户名: {username}")
    print(f"密码: {password}")
    print(f"连接类型: Telnet")
    print("============================================")
    
    # 定义信号回调函数
    def on_traffic_data(data):
        print("\n收到流量数据:")
        for interface, stats in data.items():
            print(f"接口: {interface}")
            print(f"  - 入站: {stats['input']} bytes/sec")
            print(f"  - 出站: {stats['output']} bytes/sec")
        print("-" * 50)
    
    def on_status_change(device_ip, status):
        print(f"设备 {device_ip} 状态: {status}")
    
    # 创建监控实例
    print("创建ENSPMonitor实例...")
    monitor = ENSPMonitor(ip=device_ip, username=username, password=password)
    
    # 连接信号
    monitor.traffic_data.connect(on_traffic_data)
    monitor.status_signal.connect(on_status_change)
    
    # 直接测试连接
    print("直接测试连接...")
    if monitor.connect_device():
        print("连接成功!")
        
        # 查看接口列表
        print("获取接口列表...")
        interfaces = monitor._get_interfaces()
        if interfaces:
            print(f"设备 {device_ip} 接口列表:")
            for i, interface in enumerate(interfaces):
                print(f"  {i+1}. {interface}")
                
            # 对每个接口获取流量统计
            print("\n获取接口流量统计...")
            for interface in interfaces:
                print(f"接口 {interface} 的流量统计:")
                stats = monitor._get_interface_traffic(interface)
                if stats:
                    print(f"  - 输入速率: {stats.get('input_rate', 0) // 8} bytes/sec")
                    print(f"  - 输出速率: {stats.get('output_rate', 0) // 8} bytes/sec")
                    print(f"  - 输入包数: {stats.get('in_packets', 0)}")
                    print(f"  - 输出包数: {stats.get('out_packets', 0)}")
                else:
                    print("  未获取到流量统计")
                print("")
        else:
            print("没有获取到接口列表")
        
        # 断开连接
        print("断开连接...")
        monitor.connection.disconnect()
    else:
        print("连接失败!")
    
    print("测试完成.")

if __name__ == "__main__":
    main() 