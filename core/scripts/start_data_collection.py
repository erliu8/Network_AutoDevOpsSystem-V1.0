from core.business.data_collection import DataCollector
import signal
import sys
import time
import traceback
from datetime import datetime
import os

def handle_collected_data(stats):
    """处理收集到的数据"""
    print("\n" + "="*60)
    print(f"数据收集时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"设备总数: {stats['total_devices']} | 在线: {stats['online_devices']} | 离线: {stats['offline_devices']}")
    print("="*60)
    
    # 输出设备状态表格
    print(f"{'IP地址':<15} {'名称':<18} {'状态':<10} {'CPU':<6} {'内存':<6} {'接口':<6} {'活动接口':<9}")
    print("-"*70)
    
    # 按状态排序 - 优先显示有问题的设备
    status_priority = {'warning': 0, 'error': 1, 'unknown': 2, 'connected': 3, 'normal': 3}
    sorted_devices = sorted(
        [(ip, info, stats['devices_status'].get(ip, 'unknown'), stats['devices_resources'].get(ip, {}), 
          stats['devices_interfaces'].get(ip, [])) 
         for ip, info in stats['devices_info'].items()],
        key=lambda x: status_priority.get(x[2], 4)
    )
    
    # 显示设备
    for ip, info, status, resources, interfaces in sorted_devices:
        # 状态显示
        status_display = {
            'connected': '在线',
            'normal': '在线',
            'warning': '警告',
            'error': '离线',
            'unknown': '未知',
            'cached': '缓存'
        }.get(status, '未知')
        
        # 状态颜色
        if status in ['connected', 'normal']:
            status_display = f"\033[92m{status_display}\033[0m"  # 绿色
        elif status == 'warning':
            status_display = f"\033[93m{status_display}\033[0m"  # 黄色
        elif status == 'error':
            status_display = f"\033[91m{status_display}\033[0m"  # 红色
        elif status == 'cached':
            status_display = f"\033[94m{status_display}\033[0m"  # 蓝色
        else:
            status_display = f"\033[90m{status_display}\033[0m"  # 灰色
        
        # 资源显示
        cpu = resources.get('cpu', 0)
        memory = resources.get('memory', 0)
        
        # 处理CPU和内存显示
        if cpu > 0:
            cpu_display = f"{cpu:<6}"
        else:
            cpu_display = f"{'-':<6}"
            
        if memory > 0:
            memory_display = f"{memory:<6}"
        else:
            memory_display = f"{'-':<6}"
        
        # 接口数量
        interface_count = len(interfaces)
        
        # 活动接口数量
        active_interfaces = [i for i in interfaces if i.get('status') == 'up']
        active_count = len(active_interfaces)
        
        # 设备名称
        name = info.get('name', '')
        
        # 输出设备信息
        print(f"{ip:<15} {name:<18} {status_display:<20} {cpu_display} {memory_display} {interface_count:<6} {active_count:<9}")
    
    print("-"*70)
    # 使用固定值作为收集间隔
    collect_interval = 180
    print(f"数据收集完成，下次收集还有 {collect_interval} 秒")

def main():
    """启动数据收集服务"""
    # 创建数据收集器实例
    collector = DataCollector()
    running = True
    
    def signal_handler(signum, frame):
        nonlocal running
        print("\n正在停止数据收集服务...")
        running = False
    
    # 注册信号处理
    signal.signal(signal.SIGINT, signal_handler)
    
    print("\n" + "="*60)
    print("网络设备监控数据收集服务")
    print("="*60)
    
    try:
        # 创建日志目录
        log_dir = "logs"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        # 连接数据收集信号
        collector.data_collected.connect(handle_collected_data)
        
        # 检查数据库连接
        try:
            import mysql.connector
            conn = mysql.connector.connect(
                host='localhost',
                user='root',
                password='000000'
            )
            conn.close()
        except Exception as e:
            print(f"数据库连接失败: {e}")
            print("请确保MySQL服务已启动")
        
        # 设置收集间隔
        collection_interval = 180  # 3分钟
        
        # 启动数据收集
        print(f"启动数据收集 (间隔: {collection_interval}秒)")
        collector.start_collecting(interval=collection_interval)
        
        print("数据收集服务已启动，按Ctrl+C停止")
        
        # 保持程序运行
        while running:
            time.sleep(1)
            elapsed = int(time.time()) % collection_interval
            remaining = collection_interval - elapsed
            
            # 每30秒显示一次，或者在倒计时最后10秒内每秒显示
            if elapsed % 30 == 0 or remaining <= 10:
                print(f"下次收集还有 {remaining} 秒", end="\r")
            
    except Exception as e:
        print(f"发生错误: {str(e)}")
        traceback.print_exc()
    finally:
        # 停止数据收集
        collector.stop_collecting()
        print("数据收集服务已停止")

if __name__ == "__main__":
    main()