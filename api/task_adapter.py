#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
任务适配器
为Flask API提供基于数据库的任务队列接口
"""

import sys
import os
from pathlib import Path
import traceback

# 添加项目根目录到系统路径
sys.path.append(str(Path(__file__).parent.parent))

# 导入任务仓库
from shared.db.task_repository import get_task_repository, TaskRepository
from core.business.db_task_queue import Task

class TaskAdapter:
    """任务适配器类，为Flask API提供任务队列接口"""
    
    def __init__(self):
        """初始化任务适配器"""
        # 获取任务仓库
        self.task_repository = get_task_repository()
        print("任务适配器已初始化")
    
    def add_task(self, task_type, params):
        """
        添加任务
        
        Args:
            task_type (str): 任务类型
            params (dict): 任务参数
            
        Returns:
            str: 任务ID
        """
        try:
            # 创建任务
            task_id = self.task_repository.add_task(task_type, params)
            print(f"添加任务成功: {task_id}")
            return task_id
        except Exception as e:
            print(f"添加任务失败: {str(e)}")
            traceback.print_exc()
            raise
    
    def get_task(self, task_id):
        """
        获取任务
        
        Args:
            task_id (str): 任务ID
            
        Returns:
            dict: 任务信息，如果任务不存在则返回None
        """
        try:
            # 从数据库获取任务
            return self.task_repository.get_task(task_id)
        except Exception as e:
            print(f"获取任务失败: {str(e)}")
            traceback.print_exc()
            return None
    
    def update_task_status(self, task_id, status, result=None, error=None):
        """
        更新任务状态
        
        Args:
            task_id (str): 任务ID
            status (str): 任务状态
            result (dict, optional): 任务结果
            error (str, optional): 错误信息
            
        Returns:
            bool: 是否更新成功
        """
        try:
            # 更新任务状态
            return self.task_repository.update_task_status(
                task_id, status, result, error, by="Flask API"
            )
        except Exception as e:
            print(f"更新任务状态失败: {str(e)}")
            traceback.print_exc()
            return False
    
    def get_pending_tasks(self, task_type=None, limit=10):
        """
        获取待处理的任务
        
        Args:
            task_type (str, optional): 任务类型过滤
            limit (int, optional): 最大返回数量
            
        Returns:
            list: 任务列表
        """
        try:
            # 从数据库获取待处理任务
            return self.task_repository.get_pending_tasks(task_type, limit)
        except Exception as e:
            print(f"获取待处理任务失败: {str(e)}")
            traceback.print_exc()
            return []
    
    def get_tasks_by_status(self, status, task_type=None, limit=10):
        """
        获取指定状态的任务
        
        Args:
            status (str): 任务状态
            task_type (str, optional): 任务类型过滤
            limit (int, optional): 最大返回数量
            
        Returns:
            list: 任务列表
        """
        try:
            # 从数据库获取指定状态的任务
            return self.task_repository.get_tasks_by_status(status, task_type, limit)
        except Exception as e:
            print(f"获取任务失败: {str(e)}")
            traceback.print_exc()
            return []
    
    def get_all_tasks(self, limit=100):
        """
        获取所有任务
        
        Args:
            limit (int, optional): 最大返回数量
            
        Returns:
            list: 任务列表
        """
        try:
            # 从数据库获取所有任务
            return self.task_repository.get_all_tasks(limit)
        except Exception as e:
            print(f"获取所有任务失败: {str(e)}")
            traceback.print_exc()
            return []

# 创建单例实例
_task_adapter_instance = None

def get_task_adapter():
    """获取任务适配器单例实例"""
    global _task_adapter_instance
    if _task_adapter_instance is None:
        _task_adapter_instance = TaskAdapter()
    return _task_adapter_instance 