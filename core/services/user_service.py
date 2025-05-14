# user_service.py
import json
import os
from pathlib import Path
import sys

# 添加项目根目录到系统路径
sys.path.append(str(Path(__file__).parent.parent.parent))

from core.business.db_manager import DatabaseManager, Base
from sqlalchemy import Column, Integer, String, DateTime, Text, func

class User(Base):
    """用户模型类"""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), nullable=False, unique=True)
    password = Column(String(100), nullable=False)
    email = Column(String(100), nullable=False, unique=True)
    role = Column(String(20), nullable=False, default='user')
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<User(username='{self.username}', role='{self.role}')>"

class UserService:
    """用户服务类，提供用户相关的操作"""
    
    @staticmethod
    def init_db():
        """初始化数据库，创建用户表"""
        try:
            # 创建数据库管理器实例
            db_manager = DatabaseManager()
            
            session = db_manager.get_session()
            
            try:
                # 检查是否有用户
                user_count = session.query(User).count()
                
                if user_count == 0:
                    # 插入默认用户
                    admin_user = User(
                        username='admin',
                        password='admin123',
                        role='admin',
                        email='admin@example.com'
                    )
                    
                    regular_user = User(
                        username='user',
                        password='user123',
                        role='user',
                        email='user@example.com'
                    )
                    
                    session.add(admin_user)
                    session.add(regular_user)
                    session.commit()
                    print("添加了默认用户")
                    return True
                return True
            except Exception as e:
                session.rollback()
                print(f"初始化数据库失败: {str(e)}")
                return False
            finally:
                db_manager.close_session(session)
        except Exception as e:
            print(f"连接数据库失败: {str(e)}")
            return False
    
    @staticmethod
    def get_user_by_username(username):
        """
        根据用户名获取用户信息
        
        参数:
            username (str): 用户名
            
        返回:
            dict: 用户信息字典，如果用户不存在则返回None
        """
        # 确保数据库已初始化
        UserService.init_db()
        
        try:
            # 创建数据库管理器实例
            db_manager = DatabaseManager()
            session = db_manager.get_session()
            
            try:
                print(f"尝试查询用户: {username}")
                user_data = session.query(User).filter(User.username == username).first()
                
                if user_data:
                    print(f"找到用户: {user_data}")
                    user = {
                        "id": user_data.id,
                        "username": user_data.username,
                        "password": user_data.password,
                        "role": user_data.role,
                        "email": user_data.email
                    }
                    return user
                print(f"未找到用户: {username}")
                return None
            except Exception as e:
                print(f"获取用户信息失败: {str(e)}")
                return None
            finally:
                db_manager.close_session(session)
        except Exception as e:
            print(f"连接数据库失败: {str(e)}")
            return None
    
    @staticmethod
    def authenticate_user(username, password):
        """
        验证用户凭据
        
        参数:
            username (str): 用户名
            password (str): 密码
            
        返回:
            tuple: (bool, dict) 验证是否成功和用户信息
        """
        user = UserService.get_user_by_username(username)
        
        if user and user["password"] == password:
            return True, user
        
        return False, None
    
    @staticmethod
    def get_all_users():
        """
        获取所有用户
        
        返回:
            list: 用户列表
        """
        # 确保数据库已初始化
        UserService.init_db()
        
        try:
            # 创建数据库管理器实例
            db_manager = DatabaseManager()
            session = db_manager.get_session()
            
            try:
                users_data = session.query(User).all()
                
                users = []
                for user_data in users_data:
                    user = {
                        "id": user_data.id,
                        "username": user_data.username,
                        "password": user_data.password,
                        "role": user_data.role,
                        "email": user_data.email
                    }
                    users.append(user)
                
                return users
            except Exception as e:
                print(f"获取所有用户失败: {str(e)}")
                return []
            finally:
                db_manager.close_session(session)
        except Exception as e:
            print(f"连接数据库失败: {str(e)}")
            return []
    
    @staticmethod
    def debug_print_all_users():
        """打印所有用户信息（调试用）"""
        try:
            # 创建数据库管理器实例
            db_manager = DatabaseManager()
            session = db_manager.get_session()
            
            try:
                users = session.query(User).all()
                print("数据库中的所有用户:")
                for user in users:
                    print(f"ID: {user.id}, 用户名: {user.username}, 角色: {user.role}")
                return True
            except Exception as e:
                print(f"查询所有用户失败: {str(e)}")
                return False
            finally:
                db_manager.close_session(session)
        except Exception as e:
            print(f"连接数据库失败: {str(e)}")
            return False