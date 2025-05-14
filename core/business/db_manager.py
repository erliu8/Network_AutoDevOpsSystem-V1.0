# db_manager.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session
import sys
from pathlib import Path

# 添加项目根目录到系统路径
sys.path.append(str(Path(__file__).parent.parent.parent))
from config.database import get_connection_string

# 创建基类
Base = declarative_base()

class DatabaseManager:
    """数据库管理器，负责创建和管理数据库连接"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        # 创建数据库引擎
        self.engine = create_engine(
            get_connection_string(),
            pool_size=5,
            max_overflow=10,
            pool_recycle=3600,
            echo=False  # 设置为True可以查看SQL语句
        )
        
        # 创建会话工厂
        self.session_factory = sessionmaker(bind=self.engine)
        
        # 创建线程安全的会话
        self.Session = scoped_session(self.session_factory)
        
        self._initialized = True
    
    def get_session(self):
        """获取数据库会话"""
        return self.Session()
    
    def close_session(self, session):
        """关闭数据库会话"""
        if session:
            session.close()
    
    def create_all_tables(self):
        """创建所有表"""
        Base.metadata.create_all(self.engine)
    
    def drop_all_tables(self):
        """删除所有表"""
        Base.metadata.drop_all(self.engine)