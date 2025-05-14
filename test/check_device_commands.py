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

def check_command_help(connection, command):
    """检查命令帮助信息"""
    print(f"\n====== 检查命令: {command} ======")
    try:
        output = connection.send_command(f"{command} ?", expect_string=r"[>#\]\-]")
        print(output)
        return output
    except Exception as e:
        print(f"执行命令错误: {str(e)}")
        return None

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
        
        # 检查NAT相关命令
        print("\n===== 检查NAT相关命令 =====")
        check_command_help(connection, "nat")
        check_command_help(connection, "display nat")
        
        # 检查接口NAT命令
        print("\n===== 检查接口NAT命令 =====")
        connection.send_command("interface GigabitEthernet0/0/1", expect_string=r"\[.*-.*\]")
        check_command_help(connection, "nat")
        connection.send_command("quit", expect_string=r"\[.*\]")
        
        # 检查STP相关命令
        print("\n===== 检查STP相关命令 =====")
        check_command_help(connection, "stp")
        check_command_help(connection, "display stp")
        
        # 检查接口STP命令
        print("\n===== 检查接口STP命令 =====")
        connection.send_command("interface GigabitEthernet0/0/1", expect_string=r"\[.*-.*\]")
        check_command_help(connection, "stp")
        connection.send_command("quit", expect_string=r"\[.*\]")
        
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