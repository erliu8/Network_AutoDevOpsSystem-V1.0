#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试设备模块
提供FakeDevice类替代真实网络设备，用于测试命令执行
"""

import time
import sys
import os

class FakeDevice:
    """模拟网络设备的类，用于测试"""
    
    def __init__(self, ip, username, password, device_type='huawei', port=23, **kwargs):
        """初始化模拟设备
        
        参数:
            ip: 设备IP
            username: 用户名
            password: 密码
            device_type: 设备类型，默认'huawei'
            port: 端口号，默认23
            **kwargs: 其他参数
        """
        self.ip = ip
        self.username = username
        self.password = password
        self.device_type = device_type
        self.port = port
        self.options = kwargs
        
        # 记录发送的命令
        self.sent_commands = []
        
        # 设备的当前模式
        self.current_mode = "normal"  # normal, system-view, config-specific
        
        # 当前配置上下文
        self.current_context = None
        
        # 定义命令响应
        self.command_responses = {
            # 通用命令
            "system-view": "System view, return user view with Ctrl+Z.",
            "quit": "Quit successful.",
            
            # 特定配置命令的响应将动态生成
        }
        
        print(f"[TEST] 已创建模拟设备: {ip}, 用户名: {username}, 设备类型: {device_type}")
    
    def send_command_timing(self, command):
        """模拟发送命令到设备
        
        参数:
            command: 要发送的命令
            
        返回:
            命令的输出结果
        """
        # 记录命令
        self.sent_commands.append(command)
        print(f"[TEST] 发送命令: '{command}'")
        
        # 生成命令响应
        response = self._generate_response(command)
        print(f"[TEST] 命令响应: '{response}'")
        
        # 模拟命令执行延迟
        time.sleep(0.2)
        
        return response
    
    def _generate_response(self, command):
        """根据命令生成响应
        
        参数:
            command: 要执行的命令
            
        返回:
            命令的输出结果
        """
        # 处理模式转换命令
        if command == "system-view":
            self.current_mode = "system-view"
            return self.command_responses.get(command, "")
        
        elif command == "quit":
            # 从特定配置返回系统视图，或从系统视图返回普通模式
            if self.current_mode == "config-specific":
                self.current_mode = "system-view"
                self.current_context = None
            elif self.current_mode == "system-view":
                self.current_mode = "normal"
            return self.command_responses.get(command, "")
        
        # 处理DHCP池配置命令
        elif command.startswith("ip pool"):
            if self.current_mode == "system-view":
                self.current_mode = "config-specific"
                self.current_context = command.split()[2]  # 获取池名称
                return f"Enter DHCP pool {self.current_context} view."
            else:
                return "Error: Not in system view."
        
        # 处理网关配置
        elif command.startswith("gateway-list"):
            if self.current_mode == "config-specific" and self.current_context:
                gateway = command.split()[1]
                return f"Gateway {gateway} configured for pool {self.current_context}."
            else:
                return "Error: Not in DHCP pool view."
        
        # 处理网络配置
        elif command.startswith("network"):
            if self.current_mode == "config-specific" and self.current_context:
                parts = command.split()
                if len(parts) >= 4 and parts[2] == "mask":
                    network = parts[1]
                    mask = parts[3]
                    return f"Network {network} mask {mask} configured for pool {self.current_context}."
                else:
                    return f"Network {parts[1]} configured."
            else:
                return "Error: Not in DHCP pool view."
        
        # 处理DNS配置
        elif command.startswith("dns-list"):
            if self.current_mode == "config-specific" and self.current_context:
                dns = command.split()[1]
                return f"DNS server {dns} configured for pool {self.current_context}."
            else:
                return "Error: Not in DHCP pool view."
        
        # 处理租约时间配置
        elif command.startswith("lease"):
            if self.current_mode == "config-specific" and self.current_context:
                days = command.split()[1]
                return f"Lease time {days} days configured for pool {self.current_context}."
            else:
                return "Error: Not in DHCP pool view."
        
        # 对于未知命令，返回默认响应
        return f"Command '{command}' executed successfully."
    
    def disconnect(self):
        """断开与设备的连接"""
        print(f"[TEST] 断开连接: {self.ip}")
        # 输出所有已发送的命令
        print(f"[TEST] 总共发送了 {len(self.sent_commands)} 条命令:")
        for i, cmd in enumerate(self.sent_commands):
            print(f"[TEST]   {i+1}. {cmd}")

# 用于替换netmiko的连接处理器
_original_connect_handler = None

def patch_netmiko():
    """替换netmiko的连接处理器为FakeDevice"""
    global _original_connect_handler
    
    # 需要修补的模块
    try:
        from netmiko import ConnectHandler as OriginalConnectHandler
        
        # 保存原始处理器
        _original_connect_handler = OriginalConnectHandler
        
        # 替换为模拟设备
        def fake_connect_handler(*args, **kwargs):
            print(f"[TEST] 创建模拟连接: {kwargs.get('ip', 'unknown-ip')}")
            return FakeDevice(**kwargs)
        
        # 将假处理器替换为真实处理器
        import netmiko
        netmiko.ConnectHandler = fake_connect_handler
        
        # 确认已替换
        print("[TEST] Netmiko ConnectHandler已被模拟设备替代")
        
        return OriginalConnectHandler
    except ImportError as e:
        print(f"[ERROR] 无法修补netmiko模块: {str(e)}")
        return None

def unpatch_netmiko(original_handler):
    """恢复原始的netmiko连接处理器"""
    if original_handler:
        try:
            import netmiko
            netmiko.ConnectHandler = original_handler
            print("[TEST] Netmiko ConnectHandler已恢复")
        except ImportError as e:
            print(f"[ERROR] 无法恢复netmiko模块: {str(e)}")
    else:
        print("[WARNING] 无法恢复netmiko模块: 原始处理器为空")

# 测试代码
if __name__ == "__main__":
    # 测试修补
    original = patch_netmiko()
    
    # 测试连接
    try:
        from netmiko import ConnectHandler
        
        # 创建连接
        device = ConnectHandler(
            device_type="huawei",
            ip="10.1.0.3",
            username="test",
            password="test"
        )
        
        # 发送测试命令
        commands = [
            "system-view",
            "ip pool TEST_POOL",
            "network 192.168.100.0 mask 255.255.255.0",
            "gateway-list 192.168.100.1",
            "dns-list 8.8.8.8",
            "quit",
            "quit"
        ]
        
        for cmd in commands:
            output = device.send_command_timing(cmd)
            print(f"命令: {cmd}")
            print(f"输出: {output}")
            print("=" * 50)
        
        # 断开连接
        device.disconnect()
        
    except Exception as e:
        print(f"测试失败: {str(e)}")
    
    # 恢复原始连接处理器
    unpatch_netmiko(original)