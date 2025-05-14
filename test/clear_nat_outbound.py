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

def clear_nat_outbound_global(connection):
    """清除全局NAT outbound配置"""
    print("\n===== 清除全局NAT outbound配置 =====")
    
    # 先查看当前NAT outbound配置
    print("\n当前NAT outbound配置:")
    connection.send_command("system-view", expect_string=r"\[.*\]")
    output = connection.send_command("display nat outbound", expect_string=r"\[.*\]")
    print(output)
    
    # 找出所有接口上的NAT outbound配置
    interfaces_with_nat = []
    for line in output.split("\n"):
        if "GigabitEthernet" in line:
            parts = line.strip().split()
            if len(parts) > 0:
                interfaces_with_nat.append(parts[0])
    
    print(f"\n找到以下接口配置了NAT outbound: {interfaces_with_nat}")
    
    # 尝试对每个接口清除NAT outbound配置
    for interface in interfaces_with_nat:
        print(f"\n===== 清除接口 {interface} 的NAT outbound配置 =====")
        connection.send_command(f"interface {interface}", expect_string=r"\[.*\]")
        
        # 1. 尝试直接的undo命令
        print("\n尝试: undo nat outbound")
        result = connection.send_command("undo nat outbound", expect_string=r"\[.*\]")
        print(f"结果: {result}")
        
        # 2. 尝试带ACL号的undo命令
        print("\n尝试: undo nat outbound 2000")
        result = connection.send_command("undo nat outbound 2000", expect_string=r"\[.*\]")
        print(f"结果: {result}")
        
        # 3. 尝试设置不同类型的NAT
        print("\n尝试: nat outbound 3000")
        result = connection.send_command("nat outbound 3000", expect_string=r"\[.*\]")
        print(f"结果: {result}")
        
        # 查看清除后的配置
        output = connection.send_command("display this", expect_string=r"\[.*\]")
        print(f"\n清除后接口配置:")
        print(output)
        
        # 退出接口视图
        connection.send_command("quit", expect_string=r"\[.*\]")
    
    # 再次检查NAT outbound配置
    print("\n清除后NAT outbound配置:")
    output = connection.send_command("display nat outbound", expect_string=r"\[.*\]")
    print(output)
    
    # 退出系统视图
    connection.send_command("quit", expect_string=r">")

def try_create_dynamic_nat(connection, interface_name="GigabitEthernet0/0/1", acl_number=2000):
    """尝试创建动态NAT配置"""
    print(f"\n===== 尝试在接口 {interface_name} 上创建动态NAT配置 =====")
    
    # 进入系统视图
    connection.send_command("system-view", expect_string=r"\[.*\]")
    
    # 确认ACL配置
    print("\n确认ACL配置:")
    connection.send_command(f"acl number {acl_number}", expect_string=r"\[.*\]")
    connection.send_command(f"rule 5 permit source 192.168.10.0 0.0.0.255", expect_string=r"\[.*\]")
    connection.send_command("quit", expect_string=r"\[.*\]")
    
    # 进入接口
    connection.send_command(f"interface {interface_name}", expect_string=r"\[.*\]")
    
    # 添加NAT outbound配置
    print("\n尝试添加NAT outbound配置:")
    result = connection.send_command(f"nat outbound {acl_number}", expect_string=r"\[.*\]")
    print(f"结果: {result}")
    
    # 查看结果
    output = connection.send_command("display this", expect_string=r"\[.*\]")
    print(f"\n接口配置:")
    print(output)
    
    # 退出接口视图
    connection.send_command("quit", expect_string=r"\[.*\]")
    
    # 查看全局NAT outbound
    output = connection.send_command("display nat outbound", expect_string=r"\[.*\]")
    print(f"\nNAT outbound配置:")
    print(output)
    
    # 退出系统视图
    connection.send_command("quit", expect_string=r">")

def main():
    """主函数"""
    # 设备地址
    ip = "10.1.200.1"
    
    try:
        # 连接设备
        connection = connect_device(ip)
        
        # 清除全局NAT outbound配置
        clear_nat_outbound_global(connection)
        
        # 尝试创建新的动态NAT配置
        try_create_dynamic_nat(connection)
        
    except Exception as e:
        print(f"发生错误: {str(e)}")
    finally:
        if 'connection' in locals() and connection:
            connection.disconnect()
            print("\n连接已关闭")

if __name__ == "__main__":
    main() 