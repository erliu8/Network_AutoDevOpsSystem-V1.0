#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import time
from pathlib import Path

# 添加项目根目录到系统路径
sys.path.append(str(Path(__file__).parent))

# 导入测试需要的模块
from core.business.data_collection import DataCollector
from core.services.device_service import DeviceService
from core.business.monitor_service import MonitorService

def main():
    """主函数"""
    print("启动仪表盘数据来源测试...")
    
    # 创建监控服务
    monitor_service = MonitorService()
    
    # 创建数据收集器
    try:
        collector = DataCollector()
        print("数据收集器已创建")
        
        # 检查是否有共享监控服务
        if collector.monitor_service:
            print("使用已有的监控服务进行测试")
        else:
            print("警告: 数据收集器没有监控服务")
            collector.monitor_service = monitor_service
            print("已手动设置监控服务")
    except Exception as e:
        print(f"创建数据收集器失败: {e}")
        return
    
    # 运行测试
    try:
        test_single_device_data(collector)
    except Exception as e:
        print(f"运行测试失败: {e}")
        import traceback
        print(traceback.format_exc())
    
    # 等待所有异步操作完成
    print("\n等待异步操作完成...")
    time.sleep(5)
    
    print("测试完成")

def test_single_device_data(collector):
    """测试单个设备数据获取"""
    print("=== 开始单个设备数据来源测试 ===")
    
    # 获取设备列表
    devices = DeviceService.get_all_devices()
    if not devices:
        print("没有找到任何设备")
        return False
        
    # 选择第一个设备进行测试
    test_device = devices[0]
    test_ip = test_device.get('ip')
    
    print(f"测试设备: {test_ip} ({test_device.get('name', 'Unknown')})")
    
    # 确保首先创建测试设备的监控器
    print(f"\n初始化: 确保设备 {test_ip} 有监控器")
    collector.monitor_service.check_device_status(
        test_ip, 
        test_device.get('username', '1'), 
        test_device.get('password', '1')
    )
    
    # 给一些时间让监控器初始化
    print("等待10秒钟，让监控器初始化...")
    time.sleep(10)
    
    # 1. 先正常获取一次数据作为基线
    print("\n第1步: 正常收集数据作为基线")
    baseline_stats = collector.collect_data()
    baseline_cpu = baseline_stats['devices_resources'].get(test_ip, {}).get('cpu', 0)
    baseline_mem = baseline_stats['devices_resources'].get(test_ip, {}).get('memory', 0)
    print(f"基线数据: CPU={baseline_cpu}%, 内存={baseline_mem}%")
    
    # 等待5秒
    print("\n等待5秒...")
    time.sleep(5)
    
    # 2. 再次获取数据，检查是否使用缓存
    print("\n第2步: 再次收集数据，检查是否使用缓存")
    second_stats = collector.collect_data()
    second_cpu = second_stats['devices_resources'].get(test_ip, {}).get('cpu', 0)
    second_mem = second_stats['devices_resources'].get(test_ip, {}).get('memory', 0)
    print(f"第二次数据: CPU={second_cpu}%, 内存={second_mem}%")
    
    # 检查数据是否变化
    is_same = (baseline_cpu == second_cpu) and (baseline_mem == second_mem)
    print(f"数据是否相同: {'是' if is_same else '否'}")
    
    # 3. 强制刷新设备状态
    print("\n第3步: 强制刷新设备状态")
    try:
        collector.monitor_service.force_refresh_device(test_ip)
        print(f"已请求强制刷新设备 {test_ip}")
        
        # 等待10秒，让刷新操作完成
        print("等待10秒，让刷新操作完成...")
        time.sleep(10)
    except Exception as e:
        print(f"强制刷新设备失败: {e}")
    
    # 4. 再次获取数据，检查是否是最新数据
    print("\n第4步: 强制刷新后再次收集数据")
    refreshed_stats = collector.collect_data()
    refreshed_cpu = refreshed_stats['devices_resources'].get(test_ip, {}).get('cpu', 0)
    refreshed_mem = refreshed_stats['devices_resources'].get(test_ip, {}).get('memory', 0)
    print(f"刷新后数据: CPU={refreshed_cpu}%, 内存={refreshed_mem}%")
    
    # 检查数据是否变化
    data_changed = (second_cpu != refreshed_cpu) or (second_mem != refreshed_mem)
    print(f"刷新后数据是否变化: {'是' if data_changed else '否'}")
    
    # 5. 检查监控器是否正常工作
    print("\n第5步: 检查监控器状态")
    monitor = collector.monitor_service.device_monitors.get(test_ip)
    if monitor:
        print(f"设备 {test_ip} 有监控器")
        
        if hasattr(monitor, 'last_status_data') and monitor.last_status_data:
            status_data = monitor.last_status_data
            last_timestamp = status_data.get('timestamp', 0)
            last_cpu = status_data.get('cpu', 0)
            last_mem = status_data.get('mem', 0)
            interfaces_count = len(status_data.get('interfaces', []))
            
            print(f"监控器状态数据:")
            print(f"  - 时间戳: {time.strftime('%H:%M:%S', time.localtime(last_timestamp))}")
            print(f"  - CPU: {last_cpu}%")
            print(f"  - 内存: {last_mem}%")
            print(f"  - 接口数: {interfaces_count}")
        else:
            print(f"监控器没有状态数据")
    else:
        print(f"设备 {test_ip} 没有监控器")
    
    # 总结测试结果
    print("\n=== 测试结果汇总 ===")
    print(f"基线数据:   CPU={baseline_cpu}%, 内存={baseline_mem}%")
    print(f"第二次数据: CPU={second_cpu}%, 内存={second_mem}%")
    print(f"刷新后数据: CPU={refreshed_cpu}%, 内存={refreshed_mem}%")
    
    if is_same and not data_changed:
        print("\n结论: 仪表盘可能使用的是缓存数据，强制刷新后数据也没有变化。")
        print("可能原因: 1) 连接问题导致无法获取实时数据 2) 监控器实例未正确创建或持久化")
        return False
    elif is_same and data_changed:
        print("\n结论: 仪表盘使用的是缓存数据，但强制刷新后可获取新数据。")
        return True
    elif not is_same:
        print("\n结论: 仪表盘使用的是实时数据，数据会随时间变化。")
        return True
    
    return True

if __name__ == "__main__":
    main() 