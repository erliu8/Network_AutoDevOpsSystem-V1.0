import sys
import os
import time
import threading
from pathlib import Path

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 导入Flask应用
from api.app import create_app

# 导入WebSocket相关组件
from shared.websocket.server import get_server
from shared.websocket.handlers import DashboardDataHandler, init_websocket_handlers

# 导入监控服务和数据收集器
from core.business.monitor_service import MonitorService
from core.business.data_collection import DataCollector

def run_flask_app():
    """运行Flask应用"""
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)

def init_websocket():
    """初始化WebSocket服务器"""
    # 获取WebSocket服务器实例
    server = get_server()
    
    # 如果服务器未运行，启动它
    if not hasattr(server, '_running') or not server._running:
        print("启动WebSocket服务器...")
        server.start()
        time.sleep(2)  # 等待服务器启动
    
    # 初始化WebSocket处理程序
    init_websocket_handlers()

def init_monitor_service():
    """初始化监控服务"""
    monitor_service = MonitorService()
    
    # 检查设备列表
    devices = monitor_service.default_devices
    print(f"默认设备数量: {len(devices)}")
    
    # 检查是否有设备监控器
    device_count = len(monitor_service.device_monitors)
    print(f"活动监控器数量: {device_count}")
    
    # 如果没有活动的监控器，初始化它们
    if device_count == 0:
        print("初始化设备监控器...")
        monitor_service.init_monitors()
        time.sleep(2)
        new_count = len(monitor_service.device_monitors)
        print(f"初始化后的监控器数量: {new_count}")
        
    # 开启设备状态检查
    if devices:
        print("开始设备状态检查...")
        for device in devices:
            device_ip = device.get('ip')
            if device_ip:
                monitor_service.check_device_status(device_ip)
                print(f"已启动设备 {device_ip} 的状态检查")
    
    return monitor_service

def init_data_collector():
    """初始化数据收集器"""
    collector = DataCollector()
    
    # 创建一个线程周期性收集数据
    def collect_data_thread():
        while True:
            try:
                print("收集设备数据...")
                stats = collector.collect_data()
                if stats:
                    # 将数据推送到WebSocket
                    print("推送数据到WebSocket...")
                    DashboardDataHandler.update_dashboard_data(stats)
                time.sleep(15)  # 每15秒收集一次数据
            except Exception as e:
                print(f"数据收集错误: {str(e)}")
                time.sleep(5)
    
    # 启动数据收集线程
    thread = threading.Thread(target=collect_data_thread, daemon=True)
    thread.start()
    print("数据收集线程已启动")
    
    return collector

def main():
    """主函数"""
    print("====== 启动网络监控系统 ======")
    
    # 初始化WebSocket服务器
    print("\n=== 初始化WebSocket服务器 ===")
    init_websocket()
    
    # 初始化监控服务
    print("\n=== 初始化监控服务 ===")
    monitor_service = init_monitor_service()
    
    # 初始化数据收集器
    print("\n=== 初始化数据收集器 ===")
    collector = init_data_collector()
    
    # 运行Flask应用
    print("\n=== 启动Web服务器 ===")
    print("接口将在 http://localhost:5000/ 可用")
    print("仪表盘将在 http://localhost:5000/dashboard 可用")
    run_flask_app()

if __name__ == "__main__":
    main() 