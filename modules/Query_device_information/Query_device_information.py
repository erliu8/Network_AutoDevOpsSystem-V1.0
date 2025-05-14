# Query_device_information.py
import sys
import telnetlib
import time
import threading
from PyQt5.QtCore import QObject, pyqtSignal
from sqlalchemy.orm import sessionmaker
from core.business.db_manager import DatabaseManager
from core.models.device import Device
from core.services.device_service import DeviceService

# 创建数据库管理器实例
db_manager = DatabaseManager()

# 预定义命令集
PREDEFINED_COMMANDS = {
    "接口信息": "display interface brief",
    "IP路由信息": "display ip routing-table",
    "VPN内路由信息": "display ip routing-table vpn-instance",
    "协议邻居状态": "display ospf peer brief",
    "ARP信息": "display arp"
}

class DeviceConnector(QObject):
    # 定义信号
    connection_result = pyqtSignal(bool, str)
    command_result = pyqtSignal(str)
    
    def __init__(self, device_type, enterprise=""):
        super().__init__()
        self.device_type = device_type
        self.enterprise = enterprise
        self.connection = None
        
        # 从数据库获取设备信息
        self.device_info = self._get_device_from_db()
        
    def _get_device_from_db(self):
        """从数据库获取设备信息，使用DeviceService"""
        # 获取所有设备
        devices = DeviceService.get_all_devices()
        
        # 根据设备类型和企业查询
        for device in devices:
            # 如果设备类型包含企业信息，则直接按设备类型匹配
            if self.enterprise and self.enterprise in self.device_type:
                if device['type'] == self.device_type:
                    return device
            # 否则，结合设备类型和企业信息匹配
            elif self.enterprise:
                if device['type'] == self.device_type and self.enterprise in device.get('description', ''):
                    return device
            # 如果没有指定企业，则只匹配设备类型
            else:
                if device['type'] == self.device_type:
                    return device
        return None
    
    def get_device_ip(self):
        """根据设备类型和企业获取IP地址"""
        if self.device_info:
            return self.device_info["ip"]
        
        # 如果数据库中没有找到，尝试从设备数据字典中获取（兼容旧代码）
        device_data = DeviceService.get_device_data_dict()
        if self.device_type in device_data:
            if self.enterprise in device_data[self.device_type]:
                return device_data[self.device_type][self.enterprise]
        return None
        
    def connect(self):
        """连接到设备"""
        ip = self.get_device_ip()
        if not ip:
            self.connection_result.emit(False, f"未找到设备 {self.device_type} ({self.enterprise}) 的IP地址")
            return
            
        # 在线程中执行连接操作
        threading.Thread(target=self._connect_thread, args=(ip,), daemon=True).start()
        
    def _connect_thread(self, ip):
        """在线程中执行连接操作"""
        try:
            # 使用数据库中的凭据，如果有的话
            if self.device_info:
                device = {
                    'device_type': 'huawei_telnet',
                    'ip': ip,
                    'username': self.device_info["username"],
                    'password': self.device_info["password"],
                    'port': 23,
                    'timeout': 15,
                }
            else:
                # 使用默认凭据（兼容旧代码）
                device = {
                    'device_type': 'huawei_telnet',
                    'ip': ip,
                    'username': '1',
                    'password': '1',
                    'port': 23,
                    'timeout': 15,
                }
            
            from netmiko import ConnectHandler
            self.connection = ConnectHandler(**device)
            self.connection_result.emit(True, f"成功连接到 {self.device_type} ({ip})")
        except Exception as e:
            self.connection_result.emit(False, f"连接失败: {str(e)}")
            
    def execute_command(self, command):
        """执行命令并返回结果"""
        if not self.connection:
            self.command_result.emit("错误: 未连接到设备，请先连接")
            return
            
        # 在线程中执行命令
        threading.Thread(target=self._execute_command_thread, args=(command,), daemon=True).start()
            
    def _execute_command_thread(self, command):
        """在线程中执行命令"""
        try:
            output = self.connection.send_command(command)
            self.command_result.emit(output)
        except Exception as e:
            self.command_result.emit(f"执行命令失败: {str(e)}")
            
    def disconnect(self):
        """断开连接"""
        if self.connection:
            try:
                self.connection.disconnect()
                self.connection = None
                return True, "已断开连接"
            except Exception as e:
                return False, f"断开连接失败: {str(e)}"
        return False, "未连接到设备"

# 保留原有的设备数据字典，用于兼容旧代码，但初始化时会从DeviceService获取
DEVICE_DATA = {}

def get_all_devices_from_db():
    """从数据库获取所有设备信息，使用DeviceService"""
    return DeviceService.get_all_devices()

# 初始化设备数据
def init_device_data():
    """初始化设备数据字典，从DeviceService获取设备信息"""
    global DEVICE_DATA
    try:
        # 直接使用DeviceService获取设备数据字典
        device_data = DeviceService.get_device_data_dict()
        
        # 如果成功获取了设备数据，则替换原有数据
        if device_data:
            DEVICE_DATA = device_data
            print("已从数据库加载设备数据")
        else:
            print("数据库中没有设备数据，使用默认设备数据")
    except Exception as e:
        print(f"从数据库加载设备数据失败: {str(e)}")
        print("使用默认设备数据")

# 初始化设备数据
init_device_data()