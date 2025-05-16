# 导入必要的模块
import pymysql
import sys
from pathlib import Path

# 添加项目根目录到系统路径
sys.path.append(str(Path(__file__).parent.parent.parent))
from config.database import get_connection_string, DB_CONFIG

class DeviceService:
    @staticmethod
    def get_all_devices():
        """获取所有设备"""
        try:
            # 从配置中获取数据库连接信息
            config = DB_CONFIG['default']
            conn = pymysql.connect(
                host=config['HOST'],
                user=config['USER'],
                password=config['PASSWORD'],
                database=config['NAME'],
                port=int(config['PORT'])
            )
            
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute("SELECT * FROM devices")
            devices = cursor.fetchall()
            
            result = []
            for device in devices:
                device_dict = {
                    "id": device['id'],
                    "name": device['name'],
                    "ip": device['ip'],
                    "username": device['username'],
                    "password": device['password'],
                    "type": device['device_type'],
                    "enterprise": device['enterprise'],
                    "description": device['description'],
                    "network_level": DeviceService.get_device_network_level(device['device_type'])
                }
                result.append(device_dict)
            
            cursor.close()
            conn.close()
            return result
        except Exception as e:
            print(f"获取所有设备失败: {str(e)}")
            return []
    
    @staticmethod
    def get_device_network_level(device_type):
        """根据设备类型判断网络层级
        
        参数:
            device_type: 设备类型名称
            
        返回:
            网络层级: 'core'(核心层), 'distribution'(汇聚层), 'access'(接入层), 'unknown'(未知)
        """
        device_type = str(device_type).lower() if device_type else ""
        
        # 核心层设备
        if any(keyword in device_type for keyword in ['核心', '骨干', 'core', '出口']):
            return 'core'
        
        # 汇聚层设备
        elif any(keyword in device_type for keyword in ['汇聚', '二级', 'distribution']):
            return 'distribution'
        
        # 接入层设备
        elif any(keyword in device_type for keyword in ['接入', '边缘', 'access', '终端']):
            return 'access'
        
        # 默认未知层级
        else:
            return 'unknown'
    
    @staticmethod
    def get_device_data_dict():
        """获取设备数据字典，按设备类型和企业分组"""
        try:
            devices = DeviceService.get_all_devices()
            result = {}
            
            for device in devices:
                device_type = device.get("type", "")
                enterprise = device.get("enterprise", "")
                
                if device_type and enterprise:  # 只处理有效的设备数据
                    if device_type not in result:
                        result[device_type] = {}
                    result[device_type][enterprise] = device.get("ip", "")
            
            return result
        except Exception as e:
            print(f"获取设备数据字典失败: {str(e)}")
            return {}