# test_db_operations.py
import sys
from pathlib import Path

# 添加项目根目录到系统路径
sys.path.append(str(Path(__file__).parent.parent))

try:
    # 导入数据库配置
    from config.database import get_connection_string
    
    # 导入 SQLAlchemy
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker
    
    # 导入模型 - 直接从SQLAlchemy导入基类，而不是从db_manager
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy import Column, Integer, String, DateTime, Text
    import datetime
    
    # 创建基类
    Base = declarative_base()
    
    # 定义简化版的Device模型（没有关系）
    class Device(Base):
        __tablename__ = 'devices'
        
        id = Column(Integer, primary_key=True)
        name = Column(String(50), nullable=False)
        ip = Column(String(50), nullable=False, unique=True)
        username = Column(String(50), nullable=False)
        password = Column(String(100), nullable=False)
        device_type = Column(String(50), nullable=False)
        description = Column(Text)
        created_at = Column(DateTime, default=datetime.datetime.now)
        updated_at = Column(DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now)
        
        def __repr__(self):
            return f"<Device(name='{self.name}', ip='{self.ip}')>"
    
    # 获取连接字符串
    connection_string = get_connection_string()
    print(f"连接字符串: {connection_string}")
    
    # 创建引擎
    engine = create_engine(connection_string)
    
    # 创建会话
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # 删除现有表并重新创建
    print("删除现有表并重新创建...")
    
    # 使用原始SQL语句先删除monitor_records表，再删除devices表
    with engine.connect() as conn:
        try:
            conn.execute(text("SET FOREIGN_KEY_CHECKS=0"))
            conn.execute(text("DROP TABLE IF EXISTS monitor_records"))
            conn.execute(text("DROP TABLE IF EXISTS devices"))
            conn.execute(text("SET FOREIGN_KEY_CHECKS=1"))
            conn.commit()
            print("已删除现有表")
        except Exception as e:
            print(f"删除表失败: {e}")
    
    # 创建新表
    Base.metadata.create_all(engine)
    print("表结构已重新创建")
    
    # 测试插入数据
    try:
        # 检查设备是否已存在
        existing_device = session.query(Device).filter(Device.ip == '192.168.1.1').first()
        
        if not existing_device:
            # 创建测试设备
            test_device = Device(
                name='TestRouter',
                ip='192.168.1.1',
                username='admin',
                password='admin123',
                device_type='router',
                description='测试路由器'
            )
            
            # 添加到会话
            session.add(test_device)
            
            # 提交事务
            session.commit()
            
            print("测试设备已添加")
        else:
            print("测试设备已存在")
        
        # 查询所有设备
        devices = session.query(Device).all()
        
        print("数据库中的设备:")
        for device in devices:
            print(f"- {device.name} ({device.ip})")
        
    except Exception as e:
        # 回滚事务
        session.rollback()
        print(f"操作失败: {e}")
    
    finally:
        # 关闭会话
        session.close()
    
except ImportError as e:
    print(f"导入错误: {e}")
    print("请确保已安装所需的包: pip install SQLAlchemy pymysql")
except Exception as e:
    print(f"连接失败: {e}")
    print("请检查数据库配置和服务器状态")