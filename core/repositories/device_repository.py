# device_repository.py
import sys
from pathlib import Path

# 添加项目根目录到系统路径
sys.path.append(str(Path(__file__).parent.parent.parent))
from core.business.db_manager import DatabaseManager
from core.models.device import Device

class DeviceRepository:
    """设备仓库类，负责设备的CRUD操作"""
    
    def __init__(self):
        self.db_manager = DatabaseManager()
    
    def get_all_devices(self):
        """获取所有设备"""
        session = self.db_manager.get_session()
        try:
            devices = session.query(Device).all()
            return [device.to_dict() for device in devices]
        finally:
            self.db_manager.close_session(session)
    
    def get_device_by_id(self, device_id):
        """根据ID获取设备"""
        session = self.db_manager.get_session()
        try:
            device = session.query(Device).filter(Device.id == device_id).first()
            return device.to_dict() if device else None
        finally:
            self.db_manager.close_session(session)
    
    def get_device_by_ip(self, ip):
        """根据IP获取设备"""
        session = self.db_manager.get_session()
        try:
            device = session.query(Device).filter(Device.ip == ip).first()
            return device.to_dict() if device else None
        finally:
            self.db_manager.close_session(session)
    
    def create_device(self, device_data):
        """创建设备"""
        session = self.db_manager.get_session()
        try:
            device = Device(**device_data)
            session.add(device)
            session.commit()
            return device.to_dict()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            self.db_manager.close_session(session)
    
    def update_device(self, device_id, device_data):
        """更新设备"""
        session = self.db_manager.get_session()
        try:
            device = session.query(Device).filter(Device.id == device_id).first()
            if not device:
                return None
            
            for key, value in device_data.items():
                if hasattr(device, key):
                    setattr(device, key, value)
            
            session.commit()
            return device.to_dict()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            self.db_manager.close_session(session)
    
    def delete_device(self, device_id):
        """删除设备"""
        session = self.db_manager.get_session()
        try:
            device = session.query(Device).filter(Device.id == device_id).first()
            if not device:
                return False
            
            session.delete(device)
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            raise e
        finally:
            self.db_manager.close_session(session)