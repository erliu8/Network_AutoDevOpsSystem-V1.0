import sys
import time
import threading
from pathlib import Path
from PyQt5.QtCore import QObject, pyqtSignal, QTimer

# 添加模块路径
sys.path.append(str(Path(__file__).parent.parent.parent))
# 导入线程工厂
from core.business.thread_factory import ThreadFactory

class MonitorService(QObject):
    """
    监控服务类
    负责设备状态监控和流量监控
    """
    # 定义信号
    device_status_updated = pyqtSignal(str, str, dict)  # 设备状态更新信号：设备IP, 状态, 详细信息
    device_repair_result = pyqtSignal(str, bool)        # 设备修复结果信号：设备IP, 是否成功
    traffic_data_updated = pyqtSignal(dict)             # 流量数据更新信号：流量数据
    traffic_connection_status = pyqtSignal(str, bool)   # 连接状态信号：设备IP, 是否连接成功

    def __init__(self):
        super().__init__()
        self.device_monitors = {}  # 存储设备监控实例 {ip: HuaweiNetmikoOperator}
        self.traffic_monitors = {} # 存储流量监控实例 {ip: ENSPMonitor}
        
        # 获取线程工厂实例
        self.thread_factory = ThreadFactory.get_instance()
        
        # 默认设备列表
        self.default_devices = [
            {"ip": "10.1.0.3", "username": "1", "name": "LSW1", "password": "1", "type": "地域1核心交换机"},
            {"ip": "10.1.200.1", "username": "1", "name": "AR5", "password": "1", "type": "地域1出口路由器"},
            {"ip": "10.1.18.1", "username": "1", "name": "AR1", "password": "1", "type": "地域2出口路由器"},
            {"ip": "22.22.22.22", "username": "1", "name": "LSW2", "password": "1", "type": "地域1汇聚交换机(企业A)"},
            {"ip": "10.1.18.8", "username": "1", "name": "LSW8", "password": "1", "type": "地域2核心交换机(企业A)"},
        ]
        
        # 监控定时器
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.check_all_devices)
        
        # 流量监控定时器
        self.traffic_timer = QTimer()
        self.traffic_timer.timeout.connect(self.update_traffic_data)
    
    def start_device_monitoring(self, interval=300):
        """
        启动设备状态监控
        
        参数:
            interval (int): 监控间隔，单位秒
        """
        # 导入设备状态监控类
        from modules.network_monitor.network_monitor import HuaweiNetmikoOperator
        
        # 停止现有定时器
        if self.status_timer.isActive():
            self.status_timer.stop()
        
        # 设置新的间隔并启动
        self.status_timer.setInterval(interval * 1000)  # 转换为毫秒
        self.status_timer.start()
        
        # 立即执行一次检查
        self.check_all_devices()
        
        return True
    
    def stop_device_monitoring(self):
        """停止设备状态监控"""
        if self.status_timer.isActive():
            self.status_timer.stop()
        
        # 清理资源
        for ip, monitor in list(self.device_monitors.items()):
            if monitor:
                try:
                    # 断开连接
                    if hasattr(monitor, 'connection') and monitor.connection:
                        monitor.connection.disconnect()
                except:
                    pass
        
        self.device_monitors.clear()
        return True
    
    def check_device_status(self, ip, username="1", password="1"):
        """
        检查单个设备状态
        
        参数:
            ip (str): 设备IP地址
            username (str): 用户名
            password (str): 密码
            
        返回:
            bool: 是否成功启动检查
        """
        # 导入设备状态监控类
        from modules.network_monitor.network_monitor import HuaweiNetmikoOperator
        
        # 创建或获取监控实例
        if ip not in self.device_monitors:
            print(f"MonitorService: 为设备 {ip} 创建新的监控实例")
            monitor = HuaweiNetmikoOperator(ip, username, password)
            # 连接信号
            monitor.status_signal.connect(self._forward_status_signal)
            monitor.repair_result.connect(self._forward_repair_result)
            self.device_monitors[ip] = monitor
        else:
            monitor = self.device_monitors[ip]
            print(f"MonitorService: 使用设备 {ip} 的现有监控实例")
        
        # 使用线程工厂创建线程
        self.thread_factory.start_thread(
            target=monitor.get_device_status,
            name=f"DeviceStatus-{ip}",
            module="网络监控模块"
        )
        return True
    
    def repair_device(self, ip, repair_type="reboot"):
        """
        修复设备
        
        参数:
            ip (str): 设备IP地址
            repair_type (str): 修复类型，可选值：reboot, interface
            
        返回:
            bool: 是否成功启动修复
        """
        if ip not in self.device_monitors:
            return False
        
        monitor = self.device_monitors[ip]
        
        if repair_type == "reboot":
            # 使用线程工厂创建线程
            self.thread_factory.start_thread(
                target=monitor.reboot_device,
                name=f"DeviceReboot-{ip}",
                module="网络监控模块"
            )
            return True
        
        return False
    
    def repair_interface(self, ip, interface_name):
        """
        修复指定接口
        
        参数:
            ip (str): 设备IP地址
            interface_name (str): 接口名称
            
        返回:
            bool: 是否成功启动修复
        """
        if ip not in self.device_monitors:
            print(f"设备 {ip} 未在监控列表中")
            return False
        
        monitor = self.device_monitors[ip]
        try:
            print(f"开始修复设备 {ip} 的接口 {interface_name}")
            # 使用线程工厂创建线程
            self.thread_factory.start_thread(
                target=monitor.repair_interface,
                args=(interface_name,),
                name=f"InterfaceRepair-{ip}-{interface_name}",
                module="网络监控模块"
            )
            return True
        except Exception as e:
            print(f"启动修复接口线程失败: {str(e)}")
            return False
    
    def check_all_devices(self):
        """检查所有默认设备的状态"""
        for device in self.default_devices:
            self.check_device_status(device["ip"], device["username"], device["password"])
            
    def monitor_all_devices(self, devices):
            """
            监控指定的设备列表
            
            参数:
                devices (list): 设备列表，每个设备应包含 ip, username, password 字段
            """
            for device in devices:
                self.check_device_status(device["ip"], device.get("username", "1"), device.get("password", "1"))
    
    def _forward_status_signal(self, ip, status, details):
        """转发设备状态信号"""
        # 保存最新状态信号
        if ip in self.device_monitors:
            self.device_monitors[ip].last_status = status
        
        self.device_status_updated.emit(ip, status, details)
    
    def _forward_repair_result(self, ip, success):
        """转发设备修复结果信号"""
        self.device_repair_result.emit(ip, success)
    
    def start_traffic_monitor(self, ip, username="1", password="1"):
        """
        启动流量监控
        
        参数:
            ip (str): 设备IP地址
            username (str): 用户名
            password (str): 密码
            
        返回:
            bool: 是否成功启动监控
        """
        print(f"MonitorService: 开始启动对设备 {ip} 的流量监控")
        # 导入流量监控类
        from modules.internet_traffic_monitor.internet_traffic_monitor import ENSPMonitor
        
        # 先停止所有现有监控，确保只有一个设备在被监控
        self.stop_traffic_monitor()
        
        try:
            # 创建新的监控实例
            monitor = ENSPMonitor(ip, username, password)
            
            # 连接信号
            monitor.data_updated.connect(lambda data: self._handle_traffic_data(ip, data))
            monitor.status_signal.connect(self._handle_traffic_status)
            
            # 保存实例
            self.traffic_monitors[ip] = monitor
            
            # 先尝试连接设备
            print(f"MonitorService: 尝试连接设备 {ip}")
            connection_success = monitor.connect_device()
            if not connection_success:
                print(f"MonitorService: 连接设备 {ip} 失败")
                self.traffic_connection_status.emit(ip, False)
                # 清理资源
                self.traffic_monitors.pop(ip, None)
                return False
            
            # 连接成功后启动监控
            print(f"MonitorService: 设备 {ip} 连接成功，启动监控")
            monitor_success = monitor.start_monitoring()
            if not monitor_success:
                print(f"MonitorService: 启动设备 {ip} 的监控失败")
                self.traffic_connection_status.emit(ip, False)
                # 清理资源
                monitor.stop_monitoring()  # 确保停止监控
                self.traffic_monitors.pop(ip, None)
                return False
            
            # 启动定时器（如果未启动）
            if not self.traffic_timer.isActive():
                self.traffic_timer.start(5000)  # 5秒更新一次UI
            
            print(f"MonitorService: 成功启动对设备 {ip} 的流量监控")
            self.traffic_connection_status.emit(ip, True)
            
            return True
        except Exception as e:
            import traceback
            print(f"MonitorService: 启动流量监控异常: {str(e)}")
            print(traceback.format_exc())
            self.traffic_connection_status.emit(ip, False)
            # 确保清理资源
            if ip in self.traffic_monitors:
                monitor = self.traffic_monitors[ip]
                if monitor:
                    monitor.stop_monitoring()
                self.traffic_monitors.pop(ip, None)
            return False
    
    def stop_traffic_monitor(self, ip=None):
        """
        停止流量监控
        
        参数:
            ip (str, 可选): 设备IP地址，如果为None则停止所有
            
        返回:
            bool: 是否成功停止监控
        """
        print(f"MonitorService: 停止流量监控 - IP: {ip if ip else '所有'}")
        
        if ip is None:
            # 停止所有监控
            for monitor_ip, monitor in list(self.traffic_monitors.items()):
                if monitor:
                    print(f"MonitorService: 停止设备 {monitor_ip} 的监控")
                    monitor.stop_monitoring()
            # 清空所有监控器
            self.traffic_monitors.clear()
            
            # 停止定时器
            if self.traffic_timer.isActive():
                self.traffic_timer.stop()
        elif ip in self.traffic_monitors:
            # 停止指定IP的监控
            monitor = self.traffic_monitors[ip]
            if monitor:
                print(f"MonitorService: 停止设备 {ip} 的监控")
                monitor.stop_monitoring()
            # 从监控列表中移除
            self.traffic_monitors.pop(ip)
            
            # 如果没有监控实例了，停止定时器
            if not self.traffic_monitors and self.traffic_timer.isActive():
                self.traffic_timer.stop()
        
        return True
    
    def _handle_traffic_data(self, ip, data):
        """处理和转发流量数据"""
        try:
            if not data:
                print(f"从设备 {ip} 收到空流量数据")
                return
                
            print(f"收到 {ip} 的流量数据: {len(data)} 个接口")
            
            # 发送流量数据信号
            self.traffic_data_updated.emit(data)
            
        except Exception as e:
            import traceback
            print(f"处理流量数据异常: {str(e)}")
            print(traceback.format_exc())
    
    def update_traffic_data(self):
        """更新流量数据（由定时器触发）"""
        # 这个方法由定时器调用，但实际数据更新由ENSPMonitor的信号触发
        pass
    
    def get_monitored_devices(self):
        """获取所有被监控的设备"""
        devices = []
        
        # 添加设备状态监控的设备
        for ip, monitor in self.device_monitors.items():
            device = {
                "ip": ip,
                "type": "status",
                "connected": monitor.connection is not None
            }
            devices.append(device)
        
        # 添加流量监控的设备
        for ip, monitor in self.traffic_monitors.items():
            # 检查是否已添加
            existing = next((d for d in devices if d["ip"] == ip), None)
            if existing:
                existing["type"] += "+traffic"
            else:
                device = {
                    "ip": ip,
                    "type": "traffic",
                    "connected": monitor.connected
                }
                devices.append(device)
        
        return devices
    
    def cleanup(self):
        """清理所有资源"""
        # 停止设备状态监控
        self.stop_device_monitoring()
        
        # 停止流量监控
        self.stop_traffic_monitor()
    
    def _handle_traffic_status(self, ip, status):
        """处理流量监控状态信号"""
        # 检查设备是否在监控列表中
        if ip not in self.traffic_monitors:
            print(f"MonitorService: 忽略非监控设备 {ip} 的状态信号: {status}")
            return
            
        print(f"MonitorService: 设备 {ip} 状态: {status}")
        if status == "connected":
            self.traffic_connection_status.emit(ip, True)
        elif "disconnected" in status or status == "error" or status == "stopped":
            self.traffic_connection_status.emit(ip, False)
            # 如果是错误或停止状态，清理资源
            if status == "error" or status == "stopped":
                print(f"MonitorService: 设备 {ip} 出现错误或停止，清理资源")
                if ip in self.traffic_monitors:
                    self.traffic_monitors.pop(ip, None)
                
                # 如果没有监控实例了，停止定时器
                if not self.traffic_monitors and self.traffic_timer.isActive():
                    self.traffic_timer.stop()
    
    def force_refresh_device(self, ip):
        """
        强制刷新设备状态（测试用）
        
        参数:
            ip (str): 设备IP地址
            
        返回:
            bool: 是否成功启动刷新
        """
        print(f"MonitorService: [TEST] 强制刷新设备 {ip} 状态")
        
        if ip not in self.device_monitors:
            print(f"MonitorService: [TEST] 设备 {ip} 未在监控列表中")
            return False
        
        monitor = self.device_monitors[ip]
        
        # 使用线程工厂创建线程
        self.thread_factory.start_thread(
            target=monitor.force_refresh,
            name=f"ForceRefresh-{ip}",
            module="网络监控模块"
        )
        
        return True

    def init_monitors(self):
        """初始化所有设备监控器"""
        print("初始化所有设备监控器...")
        
        # 确保设备列表已加载
        if not self.default_devices:
            self.load_devices()
        
        # 为每个设备创建监控器
        for device in self.default_devices:
            device_ip = device.get('ip')
            if device_ip and device_ip not in self.device_monitors:
                # 创建设备监控器
                self._create_device_monitor(device_ip)
                print(f"为设备 {device_ip} 创建了监控器")
        
        # 返回监控器数量
        return len(self.device_monitors)

    def _create_device_monitor(self, ip):
        """创建设备监控器
        
        参数:
            ip: 设备IP地址
        """
        try:
            # 查找设备配置
            device_config = None
            for device in self.default_devices:
                if device.get('ip') == ip:
                    device_config = device
                    break
            
            if not device_config:
                print(f"找不到设备 {ip} 的配置")
                return None
            
            # 获取设备类型
            device_type = device_config.get('type', 'huawei')
            username = device_config.get('username', '1')
            password = device_config.get('password', '1')
            
            # 确定连接方式
            if 'cisco' in device_type.lower():
                connect_type = 'cisco_ios_telnet'
            else:
                connect_type = 'huawei_telnet'
            
            # 导入网络监控器模块
            from modules.network_monitor.network_monitor import HuaweiNetmikoOperator
            
            # 创建监控器实例
            monitor = HuaweiNetmikoOperator(ip, username, password, connect_type)
            
            # 连接监控器的信号
            monitor.status_signal.connect(self._on_device_status_update)
            
            # 保存到监控器字典
            self.device_monitors[ip] = monitor
            
            print(f"已创建设备 {ip} 的监控器")
            return monitor
        except Exception as e:
            print(f"创建监控器时出错: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return None