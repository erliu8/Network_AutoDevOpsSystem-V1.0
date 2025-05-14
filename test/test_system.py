import os
import sys
import time
import json
import threading
import asyncio
import websockets

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 导入必要的组件
from core.business.monitor_service import MonitorService
from core.business.data_collection import DataCollector
from shared.websocket.server import get_server
from shared.websocket.handlers import DashboardDataHandler

def test_websocket_server():
    """测试WebSocket服务器是否正常工作"""
    print("=== 测试WebSocket服务器 ===")
    server = get_server()
    
    # 检查服务器是否已启动
    if not hasattr(server, '_running') or not server._running:
        print("WebSocket服务器未运行，现在启动...")
        server.start()
        time.sleep(2)  # 等待服务器启动
    
    # 检查服务器是否接受连接
    print(f"WebSocket服务器运行状态: {'运行中' if server._running else '已停止'}")
    print(f"当前连接的客户端数: {len(server.clients)}")
    
    # 更新测试数据
    test_data = {
        'device_status': {
            '192.168.1.1': {
                'hostname': '测试设备1',
                'ip_address': '192.168.1.1',
                'network_layer': 'core',
                'device_type': 'Router',
                'status': True,
                'cpu_usage': 45,
                'memory_usage': 60,
                'active_interfaces': 4,
                'total_interfaces': 8
            }
        },
        'device_count': 1,
        'online_count': 1,
        'offline_count': 0,
        'last_update': time.strftime('%Y-%m-%d %H:%M:%S')
    }
    
    # 尝试更新数据
    result = server.update_data(
        device_status=test_data['device_status'],
        device_count=test_data['device_count'],
        online_count=test_data['online_count'],
        offline_count=test_data['offline_count'],
        last_update=test_data['last_update']
    )
    
    print(f"数据更新结果: {'成功' if result else '失败'}")
    
    return server._running

def test_data_collector():
    """测试数据收集器是否正常工作"""
    print("\n=== 测试数据收集器 ===")
    collector = DataCollector()
    
    # 尝试收集数据
    print("正在收集数据...")
    stats = collector.collect_data()
    
    if stats:
        print(f"数据收集成功")
        print(f"设备总数: {stats.get('total_devices', 0)}")
        print(f"在线设备: {stats.get('online_devices', 0)}")
        print(f"离线设备: {stats.get('offline_devices', 0)}")
        
        # 打印每个设备的状态
        for ip, status in stats.get('devices_status', {}).items():
            print(f"设备 {ip}: {status}")
            
            # 查看资源利用率
            resources = stats.get('devices_resources', {}).get(ip, {})
            cpu = resources.get('cpu', 0)
            memory = resources.get('memory', 0)
            print(f"  - CPU: {cpu}%, 内存: {memory}%")
            
            # 查看接口信息
            interfaces = stats.get('devices_interfaces', {}).get(ip, [])
            print(f"  - 接口数量: {len(interfaces)}")
            
        # 测试DashboardDataHandler
        print("\n正在推送数据到WebSocket...")
        result = DashboardDataHandler.update_dashboard_data(stats)
        print(f"推送结果: {'成功' if result else '失败'}")
    else:
        print("数据收集失败")
    
    return stats is not None

def test_monitor_service():
    """测试监控服务是否正常工作"""
    print("\n=== 测试监控服务 ===")
    monitor_service = MonitorService()
    
    # 检查设备列表
    devices = monitor_service.default_devices
    print(f"默认设备数量: {len(devices)}")
    
    # 检查是否有设备监控器
    device_count = len(monitor_service.device_monitors)
    print(f"活动监控器数量: {device_count}")
    
    if device_count == 0:
        print("没有活动的设备监控器，尝试初始化...")
        monitor_service.init_monitors()
        time.sleep(2)
        new_count = len(monitor_service.device_monitors)
        print(f"初始化后的监控器数量: {new_count}")
    
    # 检查一个设备的状态
    if devices:
        test_device = devices[0]['ip']
        print(f"测试设备 {test_device} 的状态...")
        monitor_service.check_device_status(test_device)
        time.sleep(2)  # 等待检查完成
        
        # 检查是否有设备监控器
        if test_device in monitor_service.device_monitors:
            print(f"设备 {test_device} 有活动的监控器")
            monitor = monitor_service.device_monitors[test_device]
            if hasattr(monitor, 'last_status') and monitor.last_status:
                print(f"设备状态: {monitor.last_status}")
                return True
            else:
                print("设备状态未知")
        else:
            print(f"设备 {test_device} 没有活动的监控器")
    
    return device_count > 0

async def test_websocket_client():
    """测试WebSocket客户端连接"""
    print("\n=== 测试WebSocket客户端连接 ===")
    uri = "ws://localhost:8765"
    
    try:
        print(f"尝试连接到 {uri}...")
        async with websockets.connect(uri, ping_interval=None) as websocket:
            print("连接成功")
            
            # 等待初始数据
            print("等待数据...")
            message = await asyncio.wait_for(websocket.recv(), timeout=5)
            data = json.loads(message)
            
            print("接收到数据:")
            print(f"设备总数: {data.get('device_count', 0)}")
            print(f"在线设备: {data.get('online_count', 0)}")
            print(f"离线设备: {data.get('offline_count', 0)}")
            print(f"最后更新: {data.get('last_update', '')}")
            
            # 检查设备状态数据
            device_status = data.get('device_status', {})
            print(f"设备状态数量: {len(device_status)}")
            
            return True
    except asyncio.TimeoutError:
        print("超时：未在5秒内收到数据")
        return False
    except ConnectionRefusedError:
        print("连接被拒绝：WebSocket服务器可能未运行")
        return False
    except Exception as e:
        print(f"WebSocket客户端测试错误: {str(e)}")
        return False

def run_async_test(test_func):
    """运行异步测试函数"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(test_func())
    finally:
        loop.close()

def test_all():
    """运行所有测试"""
    print("====== 开始系统测试 ======\n")
    
    # 测试监控服务
    monitor_result = test_monitor_service()
    print(f"监控服务测试结果: {'通过' if monitor_result else '失败'}\n")
    
    # 测试数据收集器
    collector_result = test_data_collector()
    print(f"数据收集器测试结果: {'通过' if collector_result else '失败'}\n")
    
    # 测试WebSocket服务器
    server_result = test_websocket_server()
    print(f"WebSocket服务器测试结果: {'通过' if server_result else '失败'}\n")
    
    # 测试WebSocket客户端
    client_result = run_async_test(test_websocket_client)
    print(f"WebSocket客户端测试结果: {'通过' if client_result else '失败'}\n")
    
    # 总结测试结果
    all_passed = monitor_result and collector_result and server_result and client_result
    print("====== 测试完成 ======")
    print(f"总体结果: {'全部通过' if all_passed else '部分测试失败'}")
    
    # 如果有测试失败，打印建议
    if not all_passed:
        print("\n解决建议:")
        if not monitor_result:
            print("- 检查设备监控服务是否正常初始化")
            print("- 确保设备配置正确（IP、用户名、密码）")
        if not collector_result:
            print("- 检查数据收集器是否能够正常收集设备数据")
            print("- 确保监控服务已正确初始化并与数据收集器连接")
        if not server_result:
            print("- 检查WebSocket服务器是否能正常启动")
            print("- 查看是否有其他程序占用了8765端口")
        if not client_result:
            print("- 确保WebSocket服务器已经启动")
            print("- 检查连接参数是否正确（主机、端口）")
            print("- 查看防火墙是否阻止了WebSocket连接")

if __name__ == "__main__":
    test_all() 