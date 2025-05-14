# monitor_record.py
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Float, JSON
from sqlalchemy.orm import relationship
import datetime
import sys
from pathlib import Path

# 添加项目根目录到系统路径
sys.path.append(str(Path(__file__).parent.parent.parent))
from core.business.db_manager import Base

class MonitorRecord(Base):
    """监控记录模型"""
    
    __tablename__ = 'monitor_records'
    
    id = Column(Integer, primary_key=True)
    device_id = Column(Integer, ForeignKey('devices.id'), nullable=False)
    cpu_usage = Column(Float, nullable=True)
    memory_usage = Column(Float, nullable=True)
    status = Column(String(20), nullable=False)
    details = Column(JSON, nullable=True)  # 存储详细信息，如接口状态
    created_at = Column(DateTime, default=datetime.datetime.now)
    
    # 关联的设备
    device = relationship("Device", back_populates="monitor_records")
    
    def __repr__(self):
        return f"<MonitorRecord(device_id={self.device_id}, status='{self.status}')>"
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'device_id': self.device_id,
            'cpu_usage': self.cpu_usage,
            'memory_usage': self.memory_usage,
            'status': self.status,
            'details': self.details,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None
        }