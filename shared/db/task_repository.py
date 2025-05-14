#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
任务仓库类
用于管理数据库中的任务，提供CRUD操作接口
"""

import json
import uuid
import pymysql
import sys
import os
from pathlib import Path
from datetime import datetime
import traceback
import threading

# 添加项目根目录到系统路径
sys.path.append(str(Path(__file__).parent.parent.parent))

# 导入数据库配置
from config.database import DB_CONFIG

class TaskRepository:
    """任务仓库类，处理数据库中的任务数据"""
    
    def __init__(self):
        """初始化任务仓库"""
        self.db_config = DB_CONFIG['default']
        self.connection = None
        self._connection_lock = threading.Lock()
    
    def _get_connection(self):
        """获取数据库连接"""
        with self._connection_lock:
            try:
                if not self.connection or not self.connection.open:
                    self.connection = pymysql.connect(
                        host=self.db_config['HOST'],
                        port=int(self.db_config['PORT']),
                        user=self.db_config['USER'],
                        password=self.db_config['PASSWORD'],
                        database=self.db_config['NAME'],
                        charset='utf8mb4',
                        cursorclass=pymysql.cursors.DictCursor,  # 使用字典游标
                        autocommit=False  # 手动提交事务
                    )
                return self.connection
            except pymysql.Error as e:
                print(f"数据库连接错误: {str(e)}")
                # 如果之前的连接已经损坏，创建新的连接
                self.connection = None
                return self._get_new_connection()
    
    def _get_new_connection(self):
        """强制创建新的数据库连接"""
        try:
            if self.connection and self.connection.open:
                try:
                    self.connection.close()
                except:
                    pass
            
            # 创建新连接
            connection = pymysql.connect(
                host=self.db_config['HOST'],
                port=int(self.db_config['PORT']),
                user=self.db_config['USER'],
                password=self.db_config['PASSWORD'],
                database=self.db_config['NAME'],
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor,  # 使用字典游标
                autocommit=False  # 手动提交事务
            )
            self.connection = connection
            return connection
        except Exception as e:
            print(f"创建新数据库连接失败: {str(e)}")
            traceback.print_exc()
            return None
    
    def _close_connection(self):
        """关闭数据库连接"""
        with self._connection_lock:
            if self.connection and self.connection.open:
                try:
                    self.connection.close()
                except:
                    pass
                self.connection = None
    
    def add_task(self, task_type, params, task_id=None):
        """
        添加任务到数据库
        
        Args:
            task_type (str): 任务类型
            params (dict): 任务参数
            task_id (str, optional): 任务ID，如果为None则自动生成
            
        Returns:
            str: 任务ID
        """
        try:
            # 获取连接和游标
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # 生成任务ID（如果未提供）
            if task_id is None:
                task_id = str(uuid.uuid4())
            
            # 准备参数
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            params_json = json.dumps(params, ensure_ascii=False)
            
            # 执行插入
            cursor.execute('''
            INSERT INTO tasks (task_id, task_type, params, status, created_at)
            VALUES (%s, %s, %s, %s, %s)
            ''', (task_id, task_type, params_json, 'pending', now))
            
            # 记录状态变更历史
            cursor.execute('''
            INSERT INTO task_history (task_id, old_status, new_status, timestamp)
            VALUES (%s, %s, %s, %s)
            ''', (task_id, None, 'pending', now))
            
            # 提交事务
            conn.commit()
            
            return task_id
        
        except Exception as e:
            # 回滚事务
            if conn:
                conn.rollback()
            print(f"添加任务失败: {str(e)}")
            traceback.print_exc()
            raise
    
    def get_task(self, task_id):
        """
        获取任务信息
        
        Args:
            task_id (str): 任务ID
            
        Returns:
            dict: 任务信息，如果任务不存在则返回None
        """
        try:
            # 获取连接和游标
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # 执行查询
            cursor.execute('SELECT * FROM tasks WHERE task_id = %s', (task_id,))
            task = cursor.fetchone()
            
            if task:
                # 将JSON格式的参数转换为字典
                if task['params']:
                    task['params'] = json.loads(task['params'])
                
                # 将JSON格式的结果转换为字典（如果存在）
                if task['result']:
                    task['result'] = json.loads(task['result'])
            
            return task
        
        except Exception as e:
            print(f"获取任务失败: {str(e)}")
            traceback.print_exc()
            return None
    
    def update_task_status(self, task_id, status, result=None, error=None, by=None):
        """
        更新任务状态
        
        Args:
            task_id (str): 任务ID
            status (str): 新状态
            result (dict, optional): 任务结果
            error (str, optional): 错误信息
            by (str, optional): 更新人
            
        Returns:
            bool: 是否更新成功
        """
        conn = None
        try:
            # 获取连接和游标
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # 获取当前状态
            cursor.execute('SELECT status FROM tasks WHERE task_id = %s', (task_id,))
            task = cursor.fetchone()
            
            if not task:
                print(f"任务不存在: {task_id}")
                return False
            
            old_status = task['status']
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # 准备更新参数
            update_fields = ['status']
            update_values = [status]
            
            # 添加额外更新字段
            if status == 'running':
                update_fields.append('started_at')
                update_values.append(now)
            elif status in ['completed', 'failed']:
                update_fields.append('completed_at')
                update_values.append(now)
            
            if result is not None:
                update_fields.append('result')
                update_values.append(json.dumps(result, ensure_ascii=False))
            
            if error is not None:
                update_fields.append('error')
                update_values.append(error)
            
            # 构建SQL语句
            set_clause = ', '.join([f"{field} = %s" for field in update_fields])
            sql = f"UPDATE tasks SET {set_clause} WHERE task_id = %s"
            
            # 添加任务ID到参数列表
            update_values.append(task_id)
            
            # 执行更新
            cursor.execute(sql, update_values)
            
            # 记录状态变更历史
            cursor.execute('''
            INSERT INTO task_history (task_id, old_status, new_status, timestamp, changed_by)
            VALUES (%s, %s, %s, %s, %s)
            ''', (task_id, old_status, status, now, by))
            
            # 提交事务
            conn.commit()
            
            return True
        
        except Exception as e:
            # 回滚事务
            if conn:
                try:
                    conn.rollback()
                except Exception as rollback_error:
                    print(f"回滚事务失败: {str(rollback_error)}")
            print(f"更新任务状态失败: {str(e)}")
            traceback.print_exc()
            return False
        finally:
            # 确保关闭连接
            self._close_connection()
    
    def get_pending_tasks(self, task_type=None, limit=10):
        """
        获取待处理的任务
        
        Args:
            task_type (str, optional): 任务类型筛选
            limit (int, optional): 最大返回数量
            
        Returns:
            list: 任务列表
        """
        try:
            # 获取连接和游标
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # 构建SQL语句
            sql = "SELECT * FROM tasks WHERE status = 'pending'"
            params = []
            
            if task_type:
                sql += " AND task_type = %s"
                params.append(task_type)
            
            sql += " ORDER BY priority DESC, created_at ASC LIMIT %s"
            params.append(limit)
            
            # 执行查询
            cursor.execute(sql, params)
            tasks = cursor.fetchall()
            
            # 处理结果
            for task in tasks:
                if task['params']:
                    task['params'] = json.loads(task['params'])
                if task['result']:
                    task['result'] = json.loads(task['result'])
            
            return tasks
        
        except Exception as e:
            print(f"获取待处理任务失败: {str(e)}")
            traceback.print_exc()
            return []
    
    def get_tasks_by_status(self, status, task_type=None, limit=10):
        """
        获取指定状态的任务
        
        Args:
            status (str): 任务状态
            task_type (str, optional): 任务类型筛选
            limit (int, optional): 最大返回数量
            
        Returns:
            list: 任务列表
        """
        conn = None
        try:
            # 获取连接和游标
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # 构建SQL语句
            sql = "SELECT * FROM tasks WHERE status = %s"
            params = [status]
            
            if task_type:
                sql += " AND task_type = %s"
                params.append(task_type)
            
            sql += " ORDER BY created_at DESC LIMIT %s"
            params.append(limit)
            
            # 执行查询
            cursor.execute(sql, params)
            tasks = cursor.fetchall()
            
            # 处理结果
            for task in tasks:
                if task['params']:
                    task['params'] = json.loads(task['params'])
                if task['result']:
                    task['result'] = json.loads(task['result'])
            
            return tasks
        
        except Exception as e:
            print(f"获取指定状态任务失败: {str(e)}")
            traceback.print_exc()
            return []
        finally:
            # 确保关闭连接
            self._close_connection()
    
    def get_all_tasks(self, limit=100):
        """
        获取所有任务
        
        Args:
            limit (int, optional): 最大返回数量
            
        Returns:
            list: 任务列表
        """
        conn = None
        try:
            # 获取连接和游标
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # 执行查询
            cursor.execute("SELECT * FROM tasks ORDER BY created_at DESC LIMIT %s", (limit,))
            tasks = cursor.fetchall()
            
            # 处理结果
            for task in tasks:
                if task['params']:
                    task['params'] = json.loads(task['params'])
                if task['result']:
                    task['result'] = json.loads(task['result'])
            
            return tasks
        
        except Exception as e:
            print(f"获取所有任务失败: {str(e)}")
            traceback.print_exc()
            return []
        finally:
            # 确保关闭连接
            self._close_connection()
    
    def delete_task(self, task_id):
        """
        删除任务
        
        Args:
            task_id (str): 任务ID
            
        Returns:
            bool: 是否删除成功
        """
        try:
            # 获取连接和游标
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # 删除任务历史记录
            cursor.execute("DELETE FROM task_history WHERE task_id = %s", (task_id,))
            
            # 删除通知
            cursor.execute("DELETE FROM notifications WHERE task_id = %s", (task_id,))
            
            # 删除任务
            cursor.execute("DELETE FROM tasks WHERE task_id = %s", (task_id,))
            
            # 提交事务
            conn.commit()
            
            return True
        
        except Exception as e:
            # 回滚事务
            if conn:
                conn.rollback()
            print(f"删除任务失败: {str(e)}")
            traceback.print_exc()
            return False
    
    def add_notification(self, task_id, message, status="unread"):
        """
        添加任务通知
        
        Args:
            task_id (str): 任务ID
            message (str): 通知消息
            status (str, optional): 通知状态，默认为"unread"
            
        Returns:
            bool: 是否添加成功
        """
        try:
            # 获取连接和游标
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # 执行插入
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute('''
            INSERT INTO notifications (task_id, message, status, created_at)
            VALUES (%s, %s, %s, %s)
            ''', (task_id, message, status, now))
            
            # 更新任务的通知计数
            cursor.execute('''
            UPDATE tasks SET notifications_sent = notifications_sent + 1
            WHERE task_id = %s
            ''', (task_id,))
            
            # 提交事务
            conn.commit()
            
            return True
        
        except Exception as e:
            # 回滚事务
            if conn:
                conn.rollback()
            print(f"添加通知失败: {str(e)}")
            traceback.print_exc()
            return False

# 创建单例实例
_instance = None

def get_task_repository():
    """获取任务仓库单例实例"""
    global _instance
    if _instance is None:
        _instance = TaskRepository()
    return _instance

# 简单测试
if __name__ == "__main__":
    repo = get_task_repository()
    
    # 测试添加任务
    try:
        task_id = repo.add_task("test_task", {"param1": "value1", "param2": 123})
        print(f"添加任务成功，ID: {task_id}")
        
        # 测试获取任务
        task = repo.get_task(task_id)
        print(f"获取任务: {task}")
        
        # 测试更新任务状态
        repo.update_task_status(task_id, "running", by="测试程序")
        task = repo.get_task(task_id)
        print(f"更新任务状态为running: {task}")
        
        # 测试完成任务
        repo.update_task_status(
            task_id, 
            "completed", 
            result={"success": True, "data": {"result1": "value1"}}, 
            by="测试程序"
        )
        task = repo.get_task(task_id)
        print(f"更新任务状态为completed: {task}")
        
        # 测试添加通知
        repo.add_notification(task_id, "任务已完成")
        print("已添加通知")
        
        print("\n测试通过！")
    except Exception as e:
        print(f"测试失败: {str(e)}")
        traceback.print_exc() 