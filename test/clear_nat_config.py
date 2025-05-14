#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
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

def check_nat_commands(connection):
    """检查设备支持的NAT命令"""
    print("\n===== 检查NAT命令 =====")
    
    # 进入系统视图
    connection.send_command("system-view", expect_string=r"\[.*\]")
    
    # 进入接口
    interface_name = "GigabitEthernet0/0/1"
    connection.send_command(f"interface {interface_name}", expect_string=r"\[.*\]")
    
    # 显示所有NAT相关帮助
    print("\n查看NAT命令帮助:")
    output = connection.send_command("nat ?", expect_string=r"\[.*\]")
    print(output)
    
    # 退出接口视图
    connection.send_command("quit", expect_string=r"\[.*\]")
    
    # 退出系统视图
    connection.send_command("quit", expect_string=r">")

def detect_nat_config(connection, interface_name):
    """检测接口上的NAT配置"""
    print(f"\n===== 检测接口 {interface_name} 的NAT配置 =====")
    
    # 进入系统视图
    connection.send_command("system-view", expect_string=r"\[.*\]")
    
    # 进入接口
    connection.send_command(f"interface {interface_name}", expect_string=r"\[.*\]")
    
    # 显示当前配置
    output = connection.send_command("display this", expect_string=r"\[.*\]")
    print(f"\n接口 {interface_name} 的当前配置:")
    print(output)
    
    # 查找NAT相关配置
    nat_configs = []
    for line in output.split("\n"):
        line = line.strip()
        if line.startswith("nat ") or "easy ip" in line.lower():
            nat_configs.append(line)
    
    if nat_configs:
        print("\n找到以下NAT配置:")
        for config in nat_configs:
            print(f"  - {config}")
    else:
        print("\n未找到NAT配置")
    
    # 退出接口视图
    connection.send_command("quit", expect_string=r"\[.*\]")
    
    # 退出系统视图
    connection.send_command("quit", expect_string=r">")
    
    return nat_configs

def clear_nat_configs(connection, interface_name, nat_configs):
    """清除接口上的NAT配置"""
    if not nat_configs:
        print(f"\n接口 {interface_name} 上没有需要清除的NAT配置")
        return True
    
    print(f"\n===== 清除接口 {interface_name} 的NAT配置 =====")
    
    # 进入系统视图
    connection.send_command("system-view", expect_string=r"\[.*\]")
    
    # 进入接口
    connection.send_command(f"interface {interface_name}", expect_string=r"\[.*\]")
    
    success = True
    
    # 尝试清除每个NAT配置
    for config in nat_configs:
        cmd = config.strip()
        # 从配置行提取命令类型
        if cmd.startswith("nat "):
            cmd_parts = cmd.split()
            if len(cmd_parts) >= 2:
                cmd_type = cmd_parts[1]  # 例如"outbound", "server"等
                undo_cmd = f"undo nat {cmd_type}"
                
                print(f"\n执行: {undo_cmd}")
                result = connection.send_command(undo_cmd, expect_string=r"\[.*\]")
                print(f"结果: {result}")
                
                if "Error" in result:
                    success = False
                    print(f"清除命令失败: {undo_cmd}")
    
    # 查看清除后的配置
    output = connection.send_command("display this", expect_string=r"\[.*\]")
    print(f"\n清除后接口 {interface_name} 的配置:")
    print(output)
    
    # 检查是否还有NAT配置
    remaining_nat = False
    for line in output.split("\n"):
        if line.strip().startswith("nat ") or "easy ip" in line.lower():
            remaining_nat = True
            print(f"警告: 仍存在NAT配置: {line.strip()}")
    
    if not remaining_nat:
        print("所有NAT配置已成功清除")
    
    # 退出接口视图
    connection.send_command("quit", expect_string=r"\[.*\]")
    
    # 退出系统视图
    connection.send_command("quit", expect_string=r">")
    
    return not remaining_nat

def add_nat_outbound(connection, interface_name, acl_number):
    """添加NAT Outbound配置"""
    print(f"\n===== 向接口 {interface_name} 添加NAT Outbound配置 =====")
    
    # 进入系统视图
    connection.send_command("system-view", expect_string=r"\[.*\]")
    
    # 进入接口
    connection.send_command(f"interface {interface_name}", expect_string=r"\[.*\]")
    
    # 添加NAT Outbound配置
    cmd = f"nat outbound {acl_number}"
    print(f"\n执行: {cmd}")
    result = connection.send_command(cmd, expect_string=r"\[.*\]")
    print(f"结果: {result}")
    
    success = "Error" not in result
    
    # 查看配置结果
    output = connection.send_command("display this", expect_string=r"\[.*\]")
    print(f"\n配置后接口 {interface_name} 的配置:")
    print(output)
    
    # 退出接口视图
    connection.send_command("quit", expect_string=r"\[.*\]")
    
    # 退出系统视图
    connection.send_command("quit", expect_string=r">")
    
    return success

def main():
    """主函数"""
    # 设备地址
    ip = "10.1.200.1"
    interface_name = "GigabitEthernet0/0/1"
    acl_number = 2000
    
    try:
        # 连接设备
        connection = connect_device(ip)
        
        # 检查NAT命令
        check_nat_commands(connection)
        
        # 检测NAT配置
        nat_configs = detect_nat_config(connection, interface_name)
        
        # 清除NAT配置
        clear_success = clear_nat_configs(connection, interface_name, nat_configs)
        
        if clear_success:
            print("\nNAT配置清除成功，现在尝试添加新的NAT配置")
            # 添加NAT Outbound配置
            add_success = add_nat_outbound(connection, interface_name, acl_number)
            
            if add_success:
                print("\n成功添加NAT Outbound配置")
            else:
                print("\n添加NAT Outbound配置失败")
        else:
            print("\n无法完全清除NAT配置，不尝试添加新配置")
        
    except Exception as e:
        print(f"发生错误: {str(e)}")
    finally:
        if 'connection' in locals() and connection:
            connection.disconnect()
            print("\n连接已关闭")

if __name__ == "__main__":
    main() 