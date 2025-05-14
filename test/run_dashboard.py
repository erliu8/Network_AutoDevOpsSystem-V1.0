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

def init_websocket():
    """初始化WebSocket服务器"""
    print("初始化WebSocket服务器...")
    
    # 启动WebSocket服务器
    server = get_server()
    server.start()
    
    # 等待服务器启动
    time.sleep(1)
    
    # 创建初始演示数据
    demo_data = {
        'device_status': {
            'test_device_1': {
                'hostname': '测试设备1',
                'ip_address': '192.168.1.1',
                'network_layer': 'core',
                'device_type': 'Router',
                'status': True,
                'cpu_usage': 45,
                'memory_usage': 60,
                'active_interfaces': 4,
                'total_interfaces': 8
            },
            'test_device_2': {
                'hostname': '测试设备2',
                'ip_address': '192.168.1.2',
                'network_layer': 'distribution',
                'device_type': 'Switch',
                'status': True,
                'cpu_usage': 30,
                'memory_usage': 50,
                'active_interfaces': 12,
                'total_interfaces': 24
            }
        },
        'device_count': 2,
        'online_count': 2,
        'offline_count': 0,
        'last_update': time.strftime('%Y-%m-%d %H:%M:%S')
    }
    
    # 更新初始数据
    server.update_data(**demo_data)
    
    # 初始化WebSocket处理程序
    init_websocket_handlers()
    
    return server

def init_monitor_service():
    """初始化监控服务"""
    print("初始化监控服务...")
    monitor_service = MonitorService()
    
    # 检查设备列表
    devices = monitor_service.default_devices
    print(f"默认设备数量: {len(devices)}")
    
    # 如果没有活动的监控器，初始化它们
    device_count = len(monitor_service.device_monitors)
    if device_count == 0:
        print("初始化设备监控器...")
        try:
            monitor_service.init_monitors()
            new_count = len(monitor_service.device_monitors)
            print(f"初始化后的监控器数量: {new_count}")
        except Exception as e:
            print(f"初始化监控器出错: {str(e)}")
    
    return monitor_service

def run_data_collector(monitor_service):
    """运行数据收集器"""
    print("初始化数据收集器...")
    collector = DataCollector()
    
    # 创建一个线程周期性收集和更新数据
    def collect_data_thread():
        count = 0
        while True:
            try:
                count += 1
                print(f"收集数据 #{count}...")
                
                # 收集数据
                stats = collector.collect_data()
                
                # 如果收集到数据，推送到WebSocket
                if stats:
                    print(f"推送数据到WebSocket... (设备总数: {stats.get('total_devices', 0)})")
                    DashboardDataHandler.update_dashboard_data(stats)
                
                # 等待15秒
                time.sleep(15)
            except Exception as e:
                print(f"数据收集错误: {str(e)}")
                time.sleep(5)
    
    # 启动数据收集线程
    thread = threading.Thread(target=collect_data_thread, daemon=True)
    thread.start()
    print("数据收集线程已启动")
    
    return collector

def run_flask_app():
    """运行Flask应用"""
    print("\n启动Web服务器...")
    app = create_app()
    
    # 打印访问地址
    print("\n=== 网络监控仪表盘已启动 ===")
    print("访问地址:")
    print("  - 主页: http://localhost:5000/")
    print("  - 仪表盘: http://localhost:5000/dashboard")
    print("\n按Ctrl+C停止服务器...")
    
    # 启动Flask应用
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

def main():
    """主函数"""
    print("====== 启动网络监控系统 ======\n")
    
    try:
        # 初始化WebSocket服务器
        websocket_server = init_websocket()
        
        # 初始化监控服务
        monitor_service = init_monitor_service()
        
        # 运行数据收集器
        data_collector = run_data_collector(monitor_service)
        
        # 运行Flask应用
        run_flask_app()
    except KeyboardInterrupt:
        print("\n接收到中断，正在停止服务...")
    except Exception as e:
        print(f"\n发生错误: {str(e)}")
        import traceback
        print(traceback.format_exc())
    finally:
        print("\n====== 系统已停止 ======")

if __name__ == "__main__":
    main() 