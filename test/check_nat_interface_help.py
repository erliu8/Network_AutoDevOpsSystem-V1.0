#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
from netmiko import ConnectHandler

def connect_device(ip, username="1", password="1", timeout=20):
    """连接设备"""
    print(f"正在连接设备 {ip}...")
    device = {
        'device_type': 'huawei_telnet',
        'ip': ip,
        'username': username,
        'password': password,
        'port': 23,
        'timeout': timeout,
    }
    
    connection = ConnectHandler(**device)
    print(f"成功连接到设备 {ip}")
    return connection

def main():
    """主函数"""
    # 设备地址
    ip = "10.1.200.1"
    
    try:
        # 连接设备
        connection = connect_device(ip)
        
        # 进入系统视图
        print("\n进入系统视图...")
        connection.send_command("system-view", expect_string=r"\[.*\]")
        
        # 进入接口
        interface_name = "GigabitEthernet0/0/1"
        print(f"\n进入接口 {interface_name}...")
        connection.send_command(f"interface {interface_name}", expect_string=r"\[.*\]")
        
        # 查看NAT命令帮助
        print("\n查看NAT命令帮助:")
        output = connection.send_command("nat ?", expect_string=r"\[.*\]")
        print(output)
        
        # 查看undo nat命令帮助
        print("\n查看UNDO NAT命令帮助:")
        output = connection.send_command("undo nat ?", expect_string=r"\[.*\]")
        print(output)
        
        # 查看当前接口配置的NAT信息
        print("\n查看当前接口NAT配置:")
        output = connection.send_command("display this | include nat", expect_string=r"\[.*\]")
        print(output)
        
        # 尝试查找Easy IP配置
        print("\n查找Easy IP配置:")
        output = connection.send_command("display this", expect_string=r"\[.*\]")
        for line in output.split("\n"):
            if "nat" in line.lower() or "easy" in line.lower() or "ip" in line.lower():
                print(line.strip())
        
        # 退出接口视图
        connection.send_command("quit", expect_string=r"\[.*\]")
        
        # 检查全局NAT配置
        print("\n查看全局NAT配置:")
        output = connection.send_command("display nat all", expect_string=r"\[.*\]")
        print(output)
        
        # 退出系统视图
        connection.send_command("quit", expect_string=r">")
        
    except Exception as e:
        print(f"发生错误: {str(e)}")
    finally:
        if 'connection' in locals() and connection:
            connection.disconnect()
            print("\n连接已关闭")

if __name__ == "__main__":
    main() 