# device.py
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship
from core.business.db_manager import Base
import datetime

class Device(Base):
    """设备模型类"""
    __tablename__ = 'devices'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False)
    ip = Column(String(50), nullable=False, unique=True)
    username = Column(String(50), nullable=False)
    password = Column(String(100), nullable=False)
    device_type = Column(String(50), nullable=False)
    enterprise = Column(String(50))
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.datetime.now)
    updated_at = Column(DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now)
    
    # Define the relationship after both classes are defined
    # monitor_records = relationship("MonitorRecord", back_populates="device")
    
    def __repr__(self):
        return f"<Device(name='{self.name}', ip='{self.ip}')>"
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'ip': self.ip,
            'username': self.username,
            'password': self.password,
            'device_type': self.device_type,
            'enterprise': self.enterprise,
            'description': self.description,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None
        }

# Define MonitorRecord class after Device class
class MonitorRecord(Base):
    """监控记录模型类"""
    __tablename__ = 'monitor_records'
    
    id = Column(Integer, primary_key=True)
    device_id = Column(Integer, ForeignKey('devices.id'), nullable=False)
    cpu_usage = Column(Float)
    memory_usage = Column(Float)
    status = Column(String(20), nullable=False)
    details = Column(Text)
    created_at = Column(DateTime, default=datetime.datetime.now)
    
    # Define the relationship to Device
    device = relationship("Device", back_populates="monitor_records")
    
    def __repr__(self):
        return f"<MonitorRecord(device_id='{self.device_id}', status='{self.status}')>"
    
    def to_dict(self):
        return {
            'id': self.id,
            'device_id': self.device_id,
            'cpu_usage': self.cpu_usage,
            'memory_usage': self.memory_usage,
            'status': self.status,
            'details': self.details,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None
        }

# Now that both classes are defined, we can add the relationship to Device
Device.monitor_records = relationship("MonitorRecord", back_populates="device")