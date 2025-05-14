#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
WebSocket服务器和设备状态监控测试脚本
"""

import time
import threading
from datetime import datetime
from shared.websocket.server import get_server
from shared.websocket.handlers import init_websocket_handlers
from core.business.data_collection import DataCollector

def test_websocket_server():
    """测试WebSocket服务器初始化和运行"""
    print("启动WebSocket服务器测试...")
    
    # 初始化WebSocket服务器及处理程序
    server = get_server()
    print(f"获取WebSocket服务器实例: {server}")
    
    # 启动服务器
    print("启动WebSocket服务器...")
    server.start()
    print("等待服务器完全启动...")
    time.sleep(2)
    
    # 测试服务器是否正常运行
    if server._running:
        print("WebSocket服务器正在运行")
    else:
        print("警告: WebSocket服务器未运行!")
    
    # 初始化处理程序
    print("初始化WebSocket处理程序...")
    success = init_websocket_handlers()
    print(f"处理程序初始化结果: {'成功' if success else '失败'}")
    
    return server

def test_data_collection(cycles=1, interval=5):
    """测试数据收集和设备状态"""
    print("\n测试数据收集和设备状态...")
    
    # 创建数据收集器
    collector = DataCollector()
    
    # 运行多个周期的数据收集
    for i in range(cycles):
        print(f"\n==== 数据收集周期 {i+1}/{cycles} ====")
        start_time = datetime.now()
        
        # 收集数据
        stats = collector.collect_data()
        
        # 打印状态统计
        print(f"\n设备状态统计:")
        print(f"- 总设备数: {stats['total_devices']}")
        print(f"- 在线设备: {stats['online_devices']}")
        print(f"- 离线设备: {stats['offline_devices']}")
        
        # 检查状态分布
        status_counts = {}
        for status in stats['devices_status'].values():
            if status not in status_counts:
                status_counts[status] = 0
            status_counts[status] += 1
        
        print("\n状态分布:")
        for status, count in status_counts.items():
            print(f"- {status}: {count}设备")
        
        # 计算耗时
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        print(f"\n数据收集耗时: {duration:.2f}秒")
        
        # 如果还有更多周期，等待间隔时间
        if i < cycles - 1:
            print(f"等待 {interval} 秒后进行下一周期收集...")
            time.sleep(interval)

if __name__ == "__main__":
    start_time = datetime.now()
    print(f"测试开始: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # 测试WebSocket服务器
        server = test_websocket_server()
        
        # 测试数据收集
        test_data_collection(cycles=3, interval=5)
        
        # 保持脚本运行，等待WebSocket服务器接收连接
        print("\nWebSocket服务器已启动，可以使用浏览器或WebSocket客户端测试连接")
        print("地址: ws://localhost:8765")
        print("按Ctrl+C终止测试...")
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n收到终止信号...")
        
        # 停止WebSocket服务器
        print("停止WebSocket服务器...")
        server.stop()
        print("清理资源完成")
        
    except Exception as e:
        print(f"测试过程中发生错误: {str(e)}")
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    print(f"\n测试结束: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"总耗时: {duration:.2f}秒") 