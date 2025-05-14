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

def try_all_clear_commands(connection, interface_name):
    """尝试所有可能的清除命令"""
    print(f"\n===== 尝试清除接口 {interface_name} 上的所有NAT和Easy IP配置 =====")
    
    # 进入系统视图
    connection.send_command("system-view", expect_string=r"\[.*\]")
    
    # 进入接口
    connection.send_command(f"interface {interface_name}", expect_string=r"\[.*\]")
    
    # 可能的清除命令列表 - 基于Huawei设备的常见命令
    clear_commands = [
        "undo nat outbound",
        "undo nat server",
        "undo nat static",
        "undo nat easy-ip global",
        "undo nat easy-ip",
        "undo ip nat outbound",
        "undo ip nat server",
        "undo ip nat static",
        "undo ip nat easy-ip",
    ]
    
    # 尝试每个命令
    for cmd in clear_commands:
        print(f"\n尝试命令: {cmd}")
        result = connection.send_command(cmd, expect_string=r"\[.*\]")
        print(f"结果: {result}")
    
    # 检查清除后的配置
    output = connection.send_command("display this", expect_string=r"\[.*\]")
    print(f"\n清除后的接口配置:")
    print(output)
    
    # 退出接口配置
    connection.send_command("quit", expect_string=r"\[.*\]")
    
    # 退出系统视图
    connection.send_command("quit", expect_string=r">")

def check_global_nat(connection):
    """检查全局NAT配置"""
    print("\n===== 检查全局NAT配置 =====")
    
    # 进入系统视图
    connection.send_command("system-view", expect_string=r"\[.*\]")
    
    try:
        # 尝试不同的展示命令
        commands = [
            "display nat all",
            "display nat static",
            "display nat server",
            "display nat outbound",
            "display ip nat",
            "display current-configuration | include nat"
        ]
        
        for cmd in commands:
            print(f"\n执行: {cmd}")
            try:
                output = connection.send_command(cmd, expect_string=r"\[.*\]")
                print(f"结果:\n{output}")
            except Exception as e:
                print(f"命令 {cmd} 执行失败: {str(e)}")
    finally:
        # 退出系统视图
        connection.send_command("quit", expect_string=r">")

def try_add_nat_outbound(connection, interface_name, acl_number):
    """尝试添加NAT出站配置"""
    print(f"\n===== 尝试向接口 {interface_name} 添加NAT出站配置 =====")
    
    # 进入系统视图
    connection.send_command("system-view", expect_string=r"\[.*\]")
    
    # 进入接口
    connection.send_command(f"interface {interface_name}", expect_string=r"\[.*\]")
    
    # 尝试添加NAT outbound
    cmd = f"nat outbound {acl_number}"
    print(f"\n执行: {cmd}")
    result = connection.send_command(cmd, expect_string=r"\[.*\]")
    print(f"结果: {result}")
    
    # 检查配置结果
    output = connection.send_command("display this", expect_string=r"\[.*\]")
    print(f"\n配置后接口配置:")
    print(output)
    
    # 退出接口配置
    connection.send_command("quit", expect_string=r"\[.*\]")
    
    # 退出系统视图
    connection.send_command("quit", expect_string=r">")

def try_different_nat_types(connection, interface_name, acl_number):
    """尝试不同的NAT类型"""
    print(f"\n===== 尝试不同的NAT类型配置 =====")
    
    # 进入系统视图
    connection.send_command("system-view", expect_string=r"\[.*\]")
    
    # 尝试全局NAT静态配置
    print("\n尝试全局静态NAT配置:")
    cmd = "nat static global 192.168.100.1 inside 192.168.1.1"
    print(f"执行: {cmd}")
    result = connection.send_command(cmd, expect_string=r"\[.*\]")
    print(f"结果: {result}")
    
    # 进入接口
    connection.send_command(f"interface {interface_name}", expect_string=r"\[.*\]")
    
    # 尝试不同的NAT接口配置
    nat_commands = [
        f"nat server protocol tcp global 202.106.0.20 80 inside 192.168.1.100 8080",
        f"nat outbound 2000",
        f"nat easy-ip"
    ]
    
    for cmd in nat_commands:
        print(f"\n尝试命令: {cmd}")
        result = connection.send_command(cmd, expect_string=r"\[.*\]")
        print(f"结果: {result}")
    
    # 检查配置结果
    output = connection.send_command("display this", expect_string=r"\[.*\]")
    print(f"\n配置后接口配置:")
    print(output)
    
    # 退出接口配置
    connection.send_command("quit", expect_string=r"\[.*\]")
    
    # 退出系统视图
    connection.send_command("quit", expect_string=r">")

def main():
    """主函数"""
    # 设备地址
    ip = "10.1.200.1"
    interface_name = "GigabitEthernet0/0/1"
    acl_number = 2000
    
    try:
        # 连接设备
        connection = connect_device(ip)
        
        # 检查全局NAT配置
        check_global_nat(connection)
        
        # 尝试清除所有NAT和Easy IP配置
        try_all_clear_commands(connection, interface_name)
        
        # 尝试添加NAT出站配置
        try_add_nat_outbound(connection, interface_name, acl_number)
        
        # 如果还是失败，尝试不同的NAT类型
        try_different_nat_types(connection, interface_name, acl_number)
        
    except Exception as e:
        print(f"发生错误: {str(e)}")
    finally:
        if 'connection' in locals() and connection:
            connection.disconnect()
            print("\n连接已关闭")

if __name__ == "__main__":
    main() 