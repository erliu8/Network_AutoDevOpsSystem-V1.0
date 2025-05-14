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
        
        # 检查接口GigabitEthernet0/0/1的配置
        interface_name = "GigabitEthernet0/0/1"
        print(f"\n===== 检查接口 {interface_name} 配置 =====")
        connection.send_command(f"interface {interface_name}", expect_string=r"\[.*\]")
        
        # 查看接口当前配置
        print("\n当前接口配置:")
        output = connection.send_command("display this", expect_string=r"\[.*\]")
        print(output)
        
        # 寻找NAT相关配置行
        nat_lines = []
        for line in output.split("\n"):
            if "nat " in line.lower():
                nat_lines.append(line.strip())
        
        print("\nNAT相关配置行:")
        for line in nat_lines:
            print(line)
        
        # 尝试清除所有NAT配置
        print("\n===== 尝试清除NAT配置 =====")
        for nat_line in nat_lines:
            cmd = nat_line.strip()
            # 构建undo命令
            undo_cmd = "undo " + cmd
            print(f"执行: {undo_cmd}")
            output = connection.send_command(undo_cmd, expect_string=r"\[.*\]")
            print(f"结果: {output}")
        
        # 再次检查接口配置确认是否清除
        print("\n清除后接口配置:")
        output = connection.send_command("display this", expect_string=r"\[.*\]")
        print(output)
        
        # 尝试添加新的NAT配置
        print("\n===== 尝试添加新的NAT配置 =====")
        
        # 添加NAT outbound配置
        print("\n添加: nat outbound 2000")
        output = connection.send_command("nat outbound 2000", expect_string=r"\[.*\]")
        print(f"结果: {output}")
        
        # 检查是否添加成功
        print("\n添加后接口配置:")
        output = connection.send_command("display this", expect_string=r"\[.*\]")
        print(output)
        
        # 退出接口配置
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