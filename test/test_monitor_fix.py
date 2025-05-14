#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import time
from datetime import datetime
from core.business.data_collection import DataCollector
from core.services.device_service import DeviceService

def test_device_status():
    """测试设备状态判断逻辑是否修复"""
    print("=== 测试设备状态判断修复 ===")
    
    # 创建数据收集器
    collector = DataCollector()
    
    # 获取设备列表
    devices = DeviceService.get_all_devices()
    print(f"系统中设备总数: {len(devices)}")
    
    # 打印所有设备基本信息
    for i, device in enumerate(devices):
        print(f"{i+1}. {device.get('name', 'Unknown')} ({device.get('ip', 'Unknown')})")
    
    # 收集设备状态数据
    print("\n正在收集设备数据...")
    stats = collector.collect_data()
    
    # 打印状态统计
    print(f"\n设备状态统计:")
    print(f"- 总设备数: {stats['total_devices']}")
    print(f"- 在线设备: {stats['online_devices']}")
    print(f"- 离线设备: {stats['offline_devices']}")
    
    # 检查设备状态明细
    print("\n各设备状态明细:")
    for device_ip, status in stats['devices_status'].items():
        # 获取设备名称
        device_name = "Unknown"
        for device in devices:
            if device.get('ip') == device_ip:
                device_name = device.get('name', 'Unknown')
                break
        
        # 获取设备资源数据
        resources = stats['devices_resources'].get(device_ip, {})
        cpu = resources.get('cpu', 0)
        memory = resources.get('memory', 0)
        
        # 获取接口数据
        interfaces = stats['devices_interfaces'].get(device_ip, [])
        active_interfaces = [intf for intf in interfaces if intf.get('status') == 'up']
        
        # 打印设备状态
        status_text = "在线" if status in ['connected', 'normal', 'warning'] else "离线"
        print(f"- {device_name} ({device_ip}): {status} [{status_text}]")
        print(f"  CPU: {cpu}%, 内存: {memory}%")
        print(f"  接口: {len(active_interfaces)}/{len(interfaces)} 活动")
    
    # 检查是否有无效数据被跳过
    print("\n检查是否有处理问题:")
    internal_data = collector.devices_data
    for device_ip, data in internal_data.items():
        if data.get('status') in ['unknown', 'error', 'disconnected']:
            print(f"- {device_ip}: 状态为 {data.get('status')}")
            print(f"  资源数据: CPU={data.get('resources', {}).get('cpu', 0)}%, "
                  f"内存={data.get('resources', {}).get('memory', 0)}%")
            active_intf = [i for i in data.get('interfaces', []) if i.get('status') == 'up']
            print(f"  接口状态: {len(active_intf)}/{len(data.get('interfaces', []))} 活动")

    return stats

if __name__ == "__main__":
    start_time = datetime.now()
    print(f"测试开始: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        stats = test_device_status()
        print("\n--- 设备状态数据测试完成 ---")
        
        # 测试WebSocket数据推送
        try:
            from shared.websocket.handlers import DashboardDataHandler
            print("\n测试WebSocket数据推送...")
            result = DashboardDataHandler.update_dashboard_data(stats)
            print(f"WebSocket推送结果: {'成功' if result else '失败'}")
        except Exception as e:
            print(f"WebSocket测试错误: {str(e)}")
    
    except Exception as e:
        print(f"测试过程中发生错误: {str(e)}")
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    print(f"\n测试结束: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"总耗时: {duration:.2f}秒") 