import threading
from datetime import datetime, timedelta
from PyQt5.QtCore import QObject, pyqtSignal, QTimer
from core.business.monitor_service import MonitorService
from core.business.thread_factory import ThreadFactory
from core.services.device_service import DeviceService
import json
import mysql.connector
from mysql.connector import Error
import time
import traceback
import os
import asyncio

# 导入WebSocket处理程序
try:
    from shared.websocket.handlers import DashboardDataHandler
    WEBSOCKET_SUPPORT = True
except ImportError:
    print("WebSocket支持未启用 - 共享模块未找到")
    WEBSOCKET_SUPPORT = False

class DataCollector(QObject):
    """数据收集类，负责收集设备状态和流量数据"""
    
    # 定义信号
    data_collected = pyqtSignal(dict)  # 数据收集完成信号
    
    def __init__(self):
        super().__init__()
        self.monitor_service = MonitorService()
        self.thread_factory = ThreadFactory.get_instance()
        self.collection_timer = None
        self.timer_interval = 30  # 改为30秒更新一次，提高实时性
        self.devices_data = {}
        self.running = False
        self.collection_thread = None
        
        # 初始化数据库连接
        self.db_config = {
            'host': 'localhost',
            'user': 'root',
            'password': '000000',
            'database': 'autodevops'
        }
        
        # 检查并创建数据库和表
        self._initialize_database()
        
        # 连接监控服务的信号
        self.monitor_service.device_status_updated.connect(self._handle_device_status)
        self.monitor_service.traffic_data_updated.connect(self._handle_traffic_data)
        
        # 初始化WebSocket支持
        self.websocket_enabled = WEBSOCKET_SUPPORT
    
    def _initialize_database(self):
        """初始化数据库"""
        try:
            # 连接到MySQL服务器
            conn = mysql.connector.connect(
                host=self.db_config['host'],
                user=self.db_config['user'],
                password=self.db_config['password']
            )
            
            if conn.is_connected():
                cursor = conn.cursor()
                
                # 创建数据库（如果不存在）
                cursor.execute(f"CREATE DATABASE IF NOT EXISTS {self.db_config['database']}")
                
                # 使用数据库
                cursor.execute(f"USE {self.db_config['database']}")
                
                # 创建设备状态表
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS device_status (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        device_ip VARCHAR(255) NOT NULL,
                        status VARCHAR(50) NOT NULL,
                        cpu_usage FLOAT,
                        memory_usage FLOAT,
                        created_at DATETIME,
                        updated_at DATETIME,
                        UNIQUE KEY unique_device (device_ip)
                    )
                """)
                
                # 创建流量数据表
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS traffic_data (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        device_ip VARCHAR(255) NOT NULL,
                        interface VARCHAR(255) NOT NULL,
                        in_rate BIGINT,
                        out_rate BIGINT,
                        timestamp DATETIME,
                        INDEX idx_device_interface (device_ip, interface)
                    )
                """)
                
                print("数据库和表已初始化")
                
                # 保存数据库连接
                self.database = conn
                
                return True
                
            print("未能连接到MySQL服务器")
            return False
                
        except Error as e:
            print(f"数据库初始化错误: {e}")
            return False
    
    def save_to_database(self, stats):
        """保存收集到的数据到数据库"""
        if not hasattr(self, 'database') or not self.database:
            print("数据库连接不可用，跳过保存")
            return False
            
        try:
            # 重新连接（如果断开）
            if not self.database.is_connected():
                self.database.reconnect()
                
            cursor = self.database.cursor()
            
            # 获取当前时间
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # 保存设备状态
            for ip, status in stats['devices_status'].items():
                resources = stats['devices_resources'].get(ip, {})
                
                # 准备SQL
                sql = """
                    INSERT INTO device_status (device_ip, status, cpu_usage, memory_usage, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                    status = %s, cpu_usage = %s, memory_usage = %s, updated_at = %s
                """
                
                # 执行SQL
                cursor.execute(sql, (
                    ip, status, resources.get('cpu', 0), resources.get('memory', 0), current_time, current_time,
                    status, resources.get('cpu', 0), resources.get('memory', 0), current_time
                ))
            
            # 提交事务
            self.database.commit()
            cursor.close()
            
            return True
            
        except Error as e:
            print(f"保存数据到数据库失败: {e}")
            
            # 尝试回滚
            if hasattr(self, 'database') and self.database:
                try:
                    self.database.rollback()
                except Exception:
                    pass
                    
            return False

    def cleanup_database(self):
        """清理旧数据"""
        if not hasattr(self, 'database') or not self.database:
            return
            
        try:
            if not self.database.is_connected():
                self.database.reconnect()
                
            cursor = self.database.cursor()
            
            # 计算30天前的日期
            thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S')
            
            # 删除30天前的流量数据
            cursor.execute("DELETE FROM traffic_data WHERE timestamp < %s", (thirty_days_ago,))
            
            # 清理完成
            self.database.commit()
            cursor.close()
            
        except Error as e:
            print(f"清理数据库失败: {e}")
    
    def _start_timer(self):
        """启动定时器"""
        if self.collection_timer:
            self.collection_timer.cancel()
            
        # 创建定时器
        self.collection_timer = threading.Timer(self.timer_interval, self._timer_callback)
        self.collection_timer.daemon = True
        self.collection_timer.start()
        print(f"DC: 已启动数据收集定时器，间隔: {self.timer_interval}秒")

    def _timer_callback(self):
        """定时器回调函数，收集数据"""
        try:
            print("DC: 定时收集数据启动...")
            self.collect_data()
            
            # 重新启动定时器
            self._start_timer()
        except Exception as e:
            print(f"DC: 定时收集数据失败: {str(e)}")
    
    def start_collecting(self, interval=30):
        """
        开始数据收集
        
        参数:
            interval (int): 收集间隔，单位秒
        """
        if self.running:
            print("DC: 数据收集已在运行")
            return False
            
        # 保存间隔
        self.timer_interval = interval
        
        # 启动设备监控
        print("DC: 启动设备监控...")
        self.monitor_service.start_device_monitoring(interval)
        
        # 启动收集定时器
        self._start_timer()
        
        self.running = True
        print(f"DC: 数据收集已启动，间隔 {interval} 秒")
        return True
        
    def stop_collecting(self):
        """停止数据收集"""
        self.running = False
        
        # 停止定时器
        if self.collection_timer:
            self.collection_timer.cancel()
        
        # 停止设备监控
        self.monitor_service.stop_device_monitoring()
        
    def collect_data(self):
        """收集数据"""
        print("DC: 开始收集数据...")
        
        # 获取设备总数据
        devices = DeviceService.get_all_devices()
        
        # 统计数据
        stats = {
            'total_devices': len(devices),
            'online_devices': 0,
            'offline_devices': 0,
            'devices_status': {},
            'devices_resources': {},
            'devices_interfaces': {},
            'devices_info': {}
        }
        
        # 首先遍历设备列表，确保每个设备都有监控器
        for device in devices:
            device_ip = device.get('ip')
            if device_ip not in self.monitor_service.device_monitors:
                try:
                    print(f"DC: 添加监控 {device_ip}")
                    self.monitor_service.check_device_status(device_ip, device.get('username', '1'), device.get('password', '1'))
                    # 给一些时间让监控操作初始化
                    time.sleep(0.5)
                except Exception as e:
                    print(f"DC: 添加监控异常: {device_ip}, {str(e)}")
        
        # 强制检查一次所有设备状态
        print("DC: 强制检查所有设备状态")
        self.monitor_service.check_all_devices()
        
        # 给一些时间让检查操作完成
        time.sleep(2)
        
        # 计数器
        checked_count = 0
        
        # 输出当前监控设备列表，用于调试
        monitor_keys = list(self.monitor_service.device_monitors.keys())
        print(f"DC: 当前有 {len(monitor_keys)} 个设备监控器: {monitor_keys}")
        
        # 遍历设备收集数据
        for device in devices:
            device_ip = device.get('ip')
            
            # 获取设备监控数据
            device_monitor = self.monitor_service.device_monitors.get(device_ip)
            
            # 默认设备状态为unknown
            device_status = "unknown"
            cpu_usage = 0
            memory_usage = 0
            interfaces = []
            
            if device_monitor:
                print(f"DC: 检查设备 {device_ip} 的监控器")
                
                # 查看监控器是否有last_status_data
                has_data = hasattr(device_monitor, 'last_status_data') and device_monitor.last_status_data
                if has_data:
                    print(f"DC: 设备 {device_ip} 有状态数据")
                    # 使用最近一次的监控数据
                    print(f"DC: 设备 {device_ip} 获取监控数据 - 时间戳: {device_monitor.last_status_data.get('timestamp', 0)}")
                    time_diff = time.time() - device_monitor.last_status_data.get('timestamp', 0)
                    print(f"DC: 数据时间差: {int(time_diff)}秒")
                    
                    checked_count += 1
                    
                    # 如果检测设备状态间隔超过3分钟，则尝试再次获取
                    last_update = device_monitor.last_status_data.get('timestamp', 0)
                    if time.time() - last_update > 180:  # 3分钟
                        print(f"DC: 触发设备 {device_ip} 状态更新 - 数据过期")
                        try:
                            self.monitor_service.check_device_status(device_ip)
                            print(f"DC: 已请求更新设备 {device_ip} 状态")
                        except Exception as e:
                            print(f"DC: 更新设备状态异常: {device_ip}, {str(e)}")
                            
                    status_data = device_monitor.last_status_data
                    # 获取CPU和内存使用率
                    cpu_usage = status_data.get('cpu', 0)
                    memory_usage = status_data.get('mem', 0)
                    
                    # 获取接口状态
                    interfaces = status_data.get('interfaces', [])
                    
                    # 确定设备状态
                    # 如果有发送设备断连信号，则设备离线
                    if getattr(device_monitor, 'disconnected', False):
                        device_status = "disconnected"
                        print(f"DC: 设备 {device_ip} 标记为断开连接")
                    else:
                        # 默认连接状态为connected
                        device_status = "connected"
                        
                        # 检查资源使用率预警
                        if cpu_usage >= 80 or memory_usage >= 80:
                            device_status = "warning"
                            print(f"DC: 设备 {device_ip} 资源使用率过高: CPU={cpu_usage}%, MEM={memory_usage}%")
                        else:
                            print(f"DC: 设备 {device_ip} 状态正常: CPU={cpu_usage}%, MEM={memory_usage}%")
                else:
                    print(f"DC: 设备 {device_ip} 有监控器但没有状态数据")
                    # 尝试强制更新状态
                    try:
                        print(f"DC: 强制获取设备 {device_ip} 状态")
                        # 强制调用获取状态的方法
                        device_monitor.get_device_status()
                        # 等待一些时间让操作完成
                        time.sleep(1)
                        
                        # 再次检查是否有数据
                        if hasattr(device_monitor, 'last_status_data') and device_monitor.last_status_data:
                            print(f"DC: 成功获取设备 {device_ip} 的数据")
                            status_data = device_monitor.last_status_data
                            cpu_usage = status_data.get('cpu', 0)
                            memory_usage = status_data.get('mem', 0)
                            interfaces = status_data.get('interfaces', [])
                            device_status = getattr(device_monitor, 'last_status', 'unknown')
                            checked_count += 1
                        else:
                            print(f"DC: 强制获取后仍无数据: {device_ip}")
                    except Exception as e:
                        print(f"DC: 强制获取状态失败: {device_ip}, {str(e)}")
            else:
                # 没有监控数据时
                print(f"DC: 无法获取设备 {device_ip} 的状态数据 - 没有监控器或数据")
                
                # 尝试创建监控器并获取状态
                try:
                    print(f"DC: 尝试创建设备 {device_ip} 的监控器")
                    self.monitor_service.check_device_status(device_ip, device.get('username', '1'), device.get('password', '1'))
                    print(f"DC: 已请求创建设备 {device_ip} 的监控器")
                    # 给一些时间让操作完成
                    time.sleep(1)
                    
                    # 检查监控器是否创建成功
                    device_monitor = self.monitor_service.device_monitors.get(device_ip)
                    if device_monitor:
                        print(f"DC: 设备 {device_ip} 的监控器创建成功")
                    else:
                        print(f"DC: 设备 {device_ip} 的监控器创建失败")
                except Exception as e:
                    print(f"DC: 创建监控器失败: {device_ip}, {str(e)}")
            
            # 更新状态统计
            if device_status in ["connected", "warning"]:
                stats['online_devices'] += 1
            elif device_status in ["disconnected", "error"]:
                stats['offline_devices'] += 1
            
            # 保存设备状态
            stats['devices_status'][device_ip] = device_status
            
            # 保存资源使用率
            stats['devices_resources'][device_ip] = {
                'cpu': cpu_usage,
                'memory': memory_usage
            }
            
            # 保存接口信息
            stats['devices_interfaces'][device_ip] = interfaces
            
            # 保存设备详细信息
            stats['devices_info'][device_ip] = {
                'name': device.get('name', f"设备_{device_ip}"),
                'ip': device_ip,
                'type': device.get('type', 'Unknown'),
                'status': device_status,
                'cpu': cpu_usage,
                'memory': memory_usage,
                'interfaces': interfaces,
                'last_update': time.strftime('%Y-%m-%d %H:%M:%S')
            }
        
        # 总结数据收集情况
        print(f"DC: 数据收集完成 - 设备总数: {stats['total_devices']}, 在线: {stats['online_devices']}, 离线: {stats['offline_devices']}")
        print(f"DC: 详细统计: 检查设备={checked_count}")
        
        # 推送数据到WebSocket服务器
        if self.websocket_enabled:
            try:
                print("DC: 尝试推送数据到WebSocket服务器")
                
                # 确保在异步环境中使用正确的事件循环
                try:
                    # 尝试获取当前事件循环
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    # 如果当前线程没有事件循环，创建一个新的
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                # 使用线程执行WebSocket数据推送
                def push_data():
                    success = DashboardDataHandler.update_dashboard_data(stats)
                    if success:
                        print("DC: 数据已成功推送到WebSocket服务器")
                    else:
                        print("DC: 推送数据到WebSocket服务器失败")
                
                # 在独立线程中执行WebSocket更新
                thread = threading.Thread(target=push_data)
                thread.daemon = True
                thread.start()
                
            except Exception as e:
                print(f"DC: 推送数据到WebSocket服务器失败: {str(e)}")
                print(traceback.format_exc())
        
        # 保存数据到数据库
        if hasattr(self, 'database') and self.database:
            try:
                print("DC: 尝试保存数据到数据库")
                updated = self.save_to_database(stats)
                if updated:
                    print("DC: 数据已成功保存到数据库")
                else:
                    print("DC: 保存数据到数据库失败")
            except Exception as e:
                print(f"DC: 保存数据到数据库异常: {str(e)}")
        
        # 触发数据收集完成信号
        self.data_collected.emit(stats)
        
        return stats
        
    def _get_monitor_status(self, ip):
        """从监控服务获取设备状态"""
        if ip in self.monitor_service.device_monitors:
            monitor = self.monitor_service.device_monitors[ip]
            
            # 获取最新状态数据
            if hasattr(monitor, 'last_status_data') and monitor.last_status_data:
                # 获取报告的状态
                reported_status = getattr(monitor, 'last_status', 'unknown')
                
                # 返回组合状态数据
                return {
                    'status': reported_status,
                    'cpu': monitor.last_status_data.get('cpu', 0),
                    'mem': monitor.last_status_data.get('mem', 0),
                    'interfaces': monitor.last_status_data.get('interfaces', []),
                    'timestamp': monitor.last_status_data.get('timestamp', 0)
                }
        
        return None
        
    def _handle_device_status(self, ip, status, details):
        """处理设备状态更新"""
        # 创建设备数据条目（如果不存在）
        if ip not in self.devices_data:
            self.devices_data[ip] = {'status': 'unknown'}
        
        # 打印调试信息
        print(f"DC: 设备 {ip} 状态: {status}")
        
        # 处理状态逻辑
        actual_status = status
        
        # 从details中获取CPU和内存数据
        cpu_usage = details.get('cpu', 0)
        memory_usage = details.get('mem', 0)
        
        # 接口数据
        interfaces = details.get('interfaces', [])
        active_interfaces = [intf for intf in interfaces if intf.get('status') == 'up']
        
        # 如果有活动接口，记录数量但不打印详细信息
        if active_interfaces:
            print(f"DC: 活动接口: {len(active_interfaces)}/{len(interfaces)}")
        
        # 如果是断开连接或错误状态
        if status == "disconnected" or status == "error":
            actual_status = "error"
        # 如果是缓存状态，需要验证数据新鲜度
        elif status == "cached":
            current_time = time.time()
            timestamp = details.get('timestamp', 0)
            cache_age = current_time - timestamp if timestamp > 0 else 999999
            
            if cache_age > 900:  # 15分钟以上的缓存视为过期
                actual_status = "unknown"
            else:
                # 有活动接口的缓存数据视为正常连接，即使CPU/内存为0
                has_active_interfaces = len(active_interfaces) > 0
                if has_active_interfaces:
                    if cpu_usage > 80 or memory_usage > 85:
                        actual_status = "warning"
                    else:
                        actual_status = "connected"
                elif cpu_usage > 0 or memory_usage > 0:
                    # 无活动接口但有CPU或内存数据也视为连接
                    actual_status = "connected"
                else:
                    actual_status = "unknown"
        # 未知状态但有数据迹象，尝试推断状态
        elif status == "unknown":
            # 检查是否有活动接口或有效资源使用数据
            if len(active_interfaces) > 0 or cpu_usage > 0 or memory_usage > 0:
                if cpu_usage > 80 or memory_usage > 85:
                    actual_status = "warning"
                else:
                    actual_status = "connected"
        # 正常连接或普通状态
        elif status == "connected" or status == "normal":
            if cpu_usage > 80 or memory_usage > 85:
                actual_status = "warning"
            else:
                actual_status = "connected"
        
        # 最终状态与初始状态不同时，打印状态变更信息
        if actual_status != status:
            print(f"DC: 状态变更 {status} -> {actual_status}")
        
        # 更新设备数据
        self.devices_data[ip] = {
            'status': actual_status,
            'resources': {
                'cpu': cpu_usage,
                'memory': memory_usage
            },
            'interfaces': interfaces,
            'last_update': time.time()
        }
        
        # 更新实时数据缓存 (用于UI显示)
        self.last_update_time = time.time()
        self.last_collected_data = self.devices_data.copy()
        
        return actual_status
        
    def _handle_traffic_data(self, data):
        """处理流量数据更新"""
        for ip, traffic_info in data.items():
            if ip in self.devices_data:
                self.devices_data[ip]['traffic'] = traffic_info
                self.devices_data[ip]['last_traffic_update'] = datetime.now()

    def update_devices_status(self, devices_status, devices_resources, devices_interfaces):
        """更新设备状态数据"""
        try:
            # 数据更新时间
            update_time = datetime.now()
            
            # 计算统计信息
            total_devices = len(devices_status)
            online_devices = sum(1 for status in devices_status.values() if status in ['connected', 'normal', 'warning'])
            offline_devices = total_devices - online_devices
            
            # 统计数据
            stats = {
                'total_devices': total_devices,
                'online_devices': online_devices,
                'offline_devices': offline_devices,
                'devices_status': devices_status,
                'devices_resources': devices_resources,
                'devices_interfaces': devices_interfaces,
                'update_time': update_time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # 清理过期数据
            try:
                # 获取过期时间（默认24小时）
                expire_days = 1
                expire_time = update_time - timedelta(days=expire_days)
                expire_time_str = expire_time.strftime('%Y-%m-%d %H:%M:%S')
                
                # 删除过期数据
                cursor = self.conn.cursor()
                cursor.execute("DELETE FROM device_status WHERE timestamp < ?", (expire_time_str,))
                deleted_count = cursor.rowcount
                self.conn.commit()
                
                if deleted_count > 0:
                    print(f"DC: 已清理 {deleted_count} 条过期数据")
            except Exception as e:
                print(f"DC: 清理过期数据错误")
            
            # 保存每个设备的状态
            saved_count = 0
            updated_count = 0
            
            # 完全禁用无效数据判断，确保所有设备数据都保存
            # 无论设备状态如何，都保存数据，防止设备被错误标记为离线
            
            # 逐个保存设备数据
            for device_ip, status in devices_status.items():
                try:
                    # 查询设备最新记录
                    cursor = self.conn.cursor()
                    cursor.execute("""
                        SELECT id, timestamp, status FROM device_status 
                        WHERE device_ip = ? ORDER BY timestamp DESC LIMIT 1
                    """, (device_ip,))
                    row = cursor.fetchone()
                    
                    # 资源使用情况
                    resources = devices_resources.get(device_ip, {})
                    cpu = resources.get('cpu', 0)
                    memory = resources.get('memory', 0)
                    
                    # 接口情况
                    interfaces = devices_interfaces.get(device_ip, [])
                    interfaces_json = json.dumps(interfaces)
                    
                    # 判断是否需要更新
                    should_save = True
                    
                    # 如果有最近的记录，且状态相同且时间间隔较短，则不保存
                    if row:
                        last_id, last_time_str, last_status = row
                        
                        # 如果上次记录时间在5分钟内，且状态未变化，则不保存
                        try:
                            last_time = datetime.strptime(last_time_str, '%Y-%m-%d %H:%M:%S')
                            time_diff = (update_time - last_time).total_seconds()
                            
                            # 如果时间间隔小于10分钟且状态未变化，则更新现有记录而非新增
                            if time_diff < 600 and last_status == status:
                                # 更新现有记录
                                cursor.execute("""
                                    UPDATE device_status SET 
                                    cpu_usage = ?, memory_usage = ?, interfaces = ?,
                                    timestamp = ?
                                    WHERE id = ?
                                """, (cpu, memory, interfaces_json, update_time.strftime('%Y-%m-%d %H:%M:%S'), last_id))
                                self.conn.commit()
                                updated_count += 1
                                should_save = False
                        except Exception as e:
                            # 时间解析错误，仍然保存新记录
                            should_save = True
                    
                    # 保存新记录
                    if should_save:
                        cursor.execute("""
                            INSERT INTO device_status
                            (device_ip, status, cpu_usage, memory_usage, interfaces, timestamp)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (
                            device_ip,
                            status,
                            cpu,
                            memory,
                            interfaces_json,
                            update_time.strftime('%Y-%m-%d %H:%M:%S')
                        ))
                        self.conn.commit()
                        saved_count += 1
                except Exception as e:
                    print(f"DC: 更新设备 {device_ip} 数据错误 - {str(e)[:50]}")
                    continue
            
            try:
                # 尝试更新仪表盘数据（通过WebSocket）
                from shared.websocket.handlers import DashboardDataHandler
                DashboardDataHandler.update_dashboard_data(stats)
            except Exception as e:
                print(f"DC: 推送到WebSocket错误")
            
            print(f"DC: 保存 {saved_count} 条新数据，更新 {updated_count} 条现有数据")
            return stats
        except Exception as e:
            print(f"DC: 数据库操作错误")
            return {
                'total_devices': 0,
                'online_devices': 0,
                'offline_devices': 0,
                'devices_status': {},
                'devices_resources': {},
                'devices_interfaces': {},
                'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }

    def test_dashboard_data_source(self):
        """测试仪表盘数据来源（是缓存还是实时数据）"""
        print("=== 开始仪表盘数据来源测试 ===")
        
        # 获取设备列表
        devices = DeviceService.get_all_devices()
        if not devices:
            print("没有找到任何设备")
            return False
            
        # 选择第一个设备进行测试
        test_device = devices[0]
        test_ip = test_device.get('ip')
        
        print(f"测试设备: {test_ip} ({test_device.get('name', 'Unknown')})")
        
        # 1. 先正常获取一次数据作为基线
        print("\n第1步: 正常收集数据作为基线")
        baseline_stats = self.collect_data()
        baseline_cpu = baseline_stats['devices_resources'].get(test_ip, {}).get('cpu', 0)
        baseline_mem = baseline_stats['devices_resources'].get(test_ip, {}).get('memory', 0)
        print(f"基线数据: CPU={baseline_cpu}%, 内存={baseline_mem}%")
        
        # 等待3秒
        print("\n等待3秒...")
        time.sleep(3)
        
        # 2. 再次获取数据，检查是否使用缓存
        print("\n第2步: 再次收集数据，检查是否使用缓存")
        second_stats = self.collect_data()
        second_cpu = second_stats['devices_resources'].get(test_ip, {}).get('cpu', 0)
        second_mem = second_stats['devices_resources'].get(test_ip, {}).get('memory', 0)
        print(f"第二次数据: CPU={second_cpu}%, 内存={second_mem}%")
        
        # 检查数据是否变化
        is_same = (baseline_cpu == second_cpu) and (baseline_mem == second_mem)
        print(f"数据是否相同: {'是' if is_same else '否'}")
        
        # 3. 强制刷新设备状态
        print("\n第3步: 强制刷新设备状态")
        try:
            self.monitor_service.force_refresh_device(test_ip)
            print(f"已请求强制刷新设备 {test_ip}")
            
            # 等待5秒，让刷新操作完成
            print("等待5秒，让刷新操作完成...")
            time.sleep(5)
        except Exception as e:
            print(f"强制刷新设备失败: {e}")
        
        # 4. 再次获取数据，检查是否是最新数据
        print("\n第4步: 强制刷新后再次收集数据")
        refreshed_stats = self.collect_data()
        refreshed_cpu = refreshed_stats['devices_resources'].get(test_ip, {}).get('cpu', 0)
        refreshed_mem = refreshed_stats['devices_resources'].get(test_ip, {}).get('memory', 0)
        print(f"刷新后数据: CPU={refreshed_cpu}%, 内存={refreshed_mem}%")
        
        # 检查数据是否变化
        data_changed = (second_cpu != refreshed_cpu) or (second_mem != refreshed_mem)
        print(f"刷新后数据是否变化: {'是' if data_changed else '否'}")
        
        # 总结测试结果
        print("\n=== 测试结果汇总 ===")
        print(f"基线数据:   CPU={baseline_cpu}%, 内存={baseline_mem}%")
        print(f"第二次数据: CPU={second_cpu}%, 内存={second_mem}%")
        print(f"刷新后数据: CPU={refreshed_cpu}%, 内存={refreshed_mem}%")
        
        if is_same and not data_changed:
            print("\n结论: 仪表盘可能使用的是缓存数据，强制刷新后数据也没有变化。")
            return False
        elif is_same and data_changed:
            print("\n结论: 仪表盘使用的是缓存数据，但强制刷新后可获取新数据。")
            return True
        elif not is_same:
            print("\n结论: 仪表盘使用的是实时数据，数据会随时间变化。")
            return True
        
        return True