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
        
        # 检查NAT地址组命令
        print("\n====== 检查NAT地址组命令 ======")
        output = connection.send_command("nat address-group ?", expect_string=r"\[.*\]")
        print(f"命令'nat address-group ?'输出:\n{output}")
        
        # 创建测试地址组
        group_name = "test-pool"
        print(f"\n====== 创建NAT地址组 {group_name} ======")
        output = connection.send_command(f"nat address-group {group_name}", expect_string=r"\[.*\]")
        print(f"创建地址组输出:\n{output}")
        
        # 检查地址组下的命令
        print("\n====== 检查地址组下可用命令 ======")
        output = connection.send_command("?", expect_string=r"\[.*\]")
        print(f"命令'?'输出:\n{output}")
        
        # 检查地址设置命令
        print("\n====== 尝试不同的地址设置格式 ======")
        
        # 方式1: 单地址
        print("\n尝试: address 192.168.30.100")
        output = connection.send_command("address 192.168.30.100", expect_string=r"\[.*\]")
        print(f"输出:\n{output}")
        
        # 方式2: 地址范围，使用-连接
        print("\n尝试: address 192.168.30.100-192.168.30.150")
        output = connection.send_command("address 192.168.30.100-192.168.30.150", expect_string=r"\[.*\]")
        print(f"输出:\n{output}")
        
        # 方式3: 地址范围，使用掩码
        print("\n尝试: address 192.168.30.0 mask 255.255.255.0")
        output = connection.send_command("address 192.168.30.0 mask 255.255.255.0", expect_string=r"\[.*\]")
        print(f"输出:\n{output}")
        
        # 查看已配置的地址组
        print("\n====== 查看配置的地址组 ======")
        connection.send_command("quit", expect_string=r"\[.*\]") # 退出地址组配置
        output = connection.send_command("display nat address-group", expect_string=r"\[.*\]")
        print(f"命令'display nat address-group'输出:\n{output}")
        
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