#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""设备仓库模块
提供从数据库获取设备列表和单个设备的功能
"""

import sys
import os
from pathlib import Path
import mysql.connector
import json

# 单例模式设备仓库类
class DeviceRepository:
    """设备仓库类，负责从数据库获取和管理设备信息"""
    
    _instance = None
    
    def __init__(self):
        """初始化设备仓库"""
        # 初始化设备列表缓存
        self.devices_cache = {}
        self.db_config = {
            'host': 'localhost',
            'user': 'root',
            'password': '000000',
            'database': 'autodevops'
        }
        
        # 如果有配置文件，从配置文件读取数据库配置
        try:
            config_file = Path(__file__).parent.parent.parent / "config" / "db_config.json"
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                    if 'database' in config_data:
                        self.db_config.update(config_data['database'])
        except Exception as e:
            print(f"读取数据库配置文件失败: {str(e)}")
        
        # 连接数据库
        self.connect()
        
    def connect(self):
        """连接到数据库"""
        try:
            self.conn = mysql.connector.connect(**self.db_config)
            return True
        except Exception as e:
            print(f"连接数据库失败: {str(e)}")
            # 创建一个带有测试数据的模拟设备
            self._create_mock_devices()
            return False
    
    def _create_mock_devices(self):
        """创建模拟设备数据用于测试"""
        self.devices_cache = {
            1: {
                "id": 1,
                "name": "测试设备1",
                "ip": "192.168.1.1",
                "username": "admin",
                "password": "admin123",
                "type": "huawei",
                "status": "online"
            },
            2: {
                "id": 2,
                "name": "测试设备2",
                "ip": "192.168.1.2",
                "username": "admin",
                "password": "admin123",
                "type": "cisco",
                "status": "online"
            }
        }
        print("已创建2个模拟设备用于测试")
    
    def get_all_devices(self):
        """获取所有设备"""
        # 如果已有缓存数据，直接返回
        if self.devices_cache:
            return list(self.devices_cache.values())
        
        try:
            if not hasattr(self, 'conn') or not self.conn.is_connected():
                self.connect()
                
            cursor = self.conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM devices")
            devices = cursor.fetchall()
            cursor.close()
            
            # 更新缓存
            self.devices_cache = {device['id']: device for device in devices}
            
            return devices
            
        except Exception as e:
            print(f"获取设备列表失败: {str(e)}")
            # 返回缓存中的模拟设备
            return list(self.devices_cache.values())
    
    def get_device_by_id(self, device_id):
        """
        根据ID获取设备
        
        Args:
            device_id: 设备ID
            
        Returns:
            dict: 设备信息
        """
        # 转换为整数
        try:
            if isinstance(device_id, str):
                device_id = int(device_id)
        except ValueError:
            print(f"设备ID格式错误: {device_id}")
            return None
        
        # 如果已有缓存数据，直接返回
        if device_id in self.devices_cache:
            return self.devices_cache[device_id]
        
        try:
            if not hasattr(self, 'conn') or not self.conn.is_connected():
                self.connect()
                
            cursor = self.conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM devices WHERE id = %s", (device_id,))
            device = cursor.fetchone()
            cursor.close()
            
            # 更新缓存
            if device:
                self.devices_cache[device_id] = device
            
            return device
            
        except Exception as e:
            print(f"获取设备信息失败: {str(e)}")
            # 如果缓存中有此设备，返回缓存数据
            return self.devices_cache.get(device_id)
    
    def get_device_by_ip(self, ip):
        """
        根据IP获取设备
        
        Args:
            ip: 设备IP地址
            
        Returns:
            dict: 设备信息
        """
        # 如果已有缓存数据，在缓存中查找
        for device in self.devices_cache.values():
            if device.get('ip') == ip:
                return device
        
        try:
            if not hasattr(self, 'conn') or not self.conn.is_connected():
                self.connect()
                
            cursor = self.conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM devices WHERE ip = %s", (ip,))
            device = cursor.fetchone()
            cursor.close()
            
            # 更新缓存
            if device:
                self.devices_cache[device['id']] = device
            
            return device
            
        except Exception as e:
            print(f"获取设备信息失败: {str(e)}")
            
            # 在缓存中查找
            for device in self.devices_cache.values():
                if device.get('ip') == ip:
                    return device
            
            return None

# 全局设备仓库实例
_device_repository = None

def get_device_repository():
    """获取设备仓库实例"""
    global _device_repository
    if _device_repository is None:
        _device_repository = DeviceRepository()
    return _device_repository 