# query_service.py
import sys
import threading
from pathlib import Path
from PyQt5.QtCore import QObject, pyqtSignal

# 添加模块路径
sys.path.append(str(Path(__file__).parent.parent.parent))
from modules.Query_device_information.Query_device_information import DeviceConnector, DEVICE_DATA, PREDEFINED_COMMANDS
# 导入线程工厂
from core.business.thread_factory import ThreadFactory

class QueryService(QObject):
    """
    设备信息查询服务类
    作为GUI和底层查询逻辑之间的桥梁
    """
    # 定义信号
    connection_result = pyqtSignal(bool, str)  # 连接结果信号
    command_result = pyqtSignal(str)  # 命令结果信号

    def __init__(self):
        super().__init__()
        self.device_connectors = {}  # 存储设备连接实例 {device_type+enterprise: DeviceConnector}
        # 获取线程工厂实例
        self.thread_factory = ThreadFactory.get_instance()
        
    def connect_device(self, device_type, enterprise=""):
        """连接到设备"""
        key = f"{device_type}_{enterprise}"
        
        # 创建新的连接实例
        connector = DeviceConnector(device_type, enterprise)
        
        # 连接信号
        connector.connection_result.connect(self._forward_connection_result)
        connector.command_result.connect(self._forward_command_result)
        
        # 保存实例
        self.device_connectors[key] = connector
        
        # 使用线程工厂创建线程连接设备
        self.thread_factory.start_thread(
            target=connector.connect,
            name=f"DeviceConnect-{device_type}-{enterprise}",
            module="设备信息查询模块"
        )
        
        return connector
    
    def execute_command(self, device_type, enterprise, command):
        """执行命令"""
        key = f"{device_type}_{enterprise}"
        
        if key not in self.device_connectors:
            self.command_result.emit("错误: 未连接到设备，请先连接")
            return False
            
        connector = self.device_connectors[key]
        
        # 使用线程工厂创建线程执行命令
        self.thread_factory.start_thread(
            target=connector.execute_command,
            args=(command,),
            name=f"ExecuteCommand-{device_type}-{enterprise}",
            module="设备信息查询模块"
        )
        
        return True
    
    def disconnect_device(self, device_type, enterprise):
        """断开连接"""
        key = f"{device_type}_{enterprise}"
        
        if key in self.device_connectors:
            connector = self.device_connectors[key]
            result, message = connector.disconnect()
            del self.device_connectors[key]
            return result, message
            
        return False, "未连接到设备"
    
    def _forward_connection_result(self, success, message):
        """转发连接结果信号"""
        self.connection_result.emit(success, message)
    
    def _forward_command_result(self, result):
        """转发命令结果信号"""
        self.command_result.emit(result)
    
    def get_device_data(self):
        """获取设备数据"""
        return DEVICE_DATA
    
    def get_predefined_commands(self):
        """获取预定义命令"""
        return PREDEFINED_COMMANDS
    
    def cleanup(self):
        """清理所有连接资源"""
        for key in list(self.device_connectors.keys()):
            connector = self.device_connectors[key]
            connector.disconnect()
        
        self.device_connectors.clear()