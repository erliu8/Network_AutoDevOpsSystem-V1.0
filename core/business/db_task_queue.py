#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
基于数据库的任务队列实现
使用数据库存储任务，支持跨进程访问
"""

import time
import json
import uuid
import threading
import sys
import os
from pathlib import Path
from datetime import datetime
import traceback
from PyQt5.QtCore import QObject, pyqtSignal, QTimer

# 添加项目根目录到系统路径
sys.path.append(str(Path(__file__).parent.parent.parent))

# 导入任务仓库
from shared.db.task_repository import get_task_repository
from core.business.thread_factory import ThreadFactory

class Task:
    """任务类，表示一个待执行的任务"""
    def __init__(self, task_type, params, task_id=None):
        self.task_id = task_id or str(uuid.uuid4())
        self.task_type = task_type
        self.params = params
        self.status = "pending"  # pending, running, completed, failed
        self.result = None
        self.error = None
        self.created_at = datetime.now()
        self.started_at = None
        self.completed_at = None
    
    def to_dict(self):
        """将任务转换为字典"""
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "params": self.params,
            "status": self.status,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }
    
    @staticmethod
    def from_dict(data):
        """从字典创建任务"""
        task = Task(data["task_type"], data["params"], data["task_id"])
        task.status = data["status"]
        task.result = data["result"]
        task.error = data["error"]
        
        # 处理日期时间
        if isinstance(data["created_at"], str):
            task.created_at = datetime.fromisoformat(data["created_at"].replace("Z", "+00:00"))
        elif isinstance(data["created_at"], datetime):
            task.created_at = data["created_at"]
            
        if "started_at" in data and data["started_at"]:
            if isinstance(data["started_at"], str):
                task.started_at = datetime.fromisoformat(data["started_at"].replace("Z", "+00:00"))
            elif isinstance(data["started_at"], datetime):
                task.started_at = data["started_at"]
                
        if "completed_at" in data and data["completed_at"]:
            if isinstance(data["completed_at"], str):
                task.completed_at = datetime.fromisoformat(data["completed_at"].replace("Z", "+00:00"))
            elif isinstance(data["completed_at"], datetime):
                task.completed_at = data["completed_at"]
                
        return task
    
    @staticmethod
    def from_db_row(row):
        """从数据库行创建任务对象
        
        Args:
            row (dict): 数据库行数据
            
        Returns:
            Task: 任务对象
        """
        # 创建任务对象
        task = Task(
            task_type=row["task_type"],
            params=row["params"] if isinstance(row["params"], dict) else json.loads(row["params"]),
            task_id=row["task_id"]
        )
        
        # 设置任务状态
        task.status = row["status"]
        
        # 设置结果和错误
        if row.get("result"):
            task.result = row["result"] if isinstance(row["result"], dict) else json.loads(row["result"])
        task.error = row.get("error")
        
        # 设置时间戳
        if row.get("created_at"):
            if isinstance(row["created_at"], str):
                task.created_at = datetime.fromisoformat(row["created_at"].replace(" ", "T"))
            else:
                task.created_at = row["created_at"]
                
        if row.get("started_at"):
            if isinstance(row["started_at"], str):
                task.started_at = datetime.fromisoformat(row["started_at"].replace(" ", "T"))
            else:
                task.started_at = row["started_at"]
                
        if row.get("completed_at"):
            if isinstance(row["completed_at"], str):
                task.completed_at = datetime.fromisoformat(row["completed_at"].replace(" ", "T"))
            else:
                task.completed_at = row["completed_at"]
        
        return task

class DBTaskQueue(QObject):
    """
    基于数据库的任务队列类
    使用数据库存储任务，支持跨进程访问
    """
    
    # 定义信号
    task_added = pyqtSignal(object)  # 任务添加信号
    task_started = pyqtSignal(object)  # 任务开始执行信号
    task_completed = pyqtSignal(object)  # 任务完成信号
    task_failed = pyqtSignal(object, str)  # 任务失败信号
    task_status_changed = pyqtSignal(object, str, str)  # 任务状态变化信号 (task, old_status, new_status)
    
    def __init__(self, poll_interval=5.0):
        """
        初始化任务队列
        
        Args:
            poll_interval (float): 轮询间隔（秒）
        """
        super().__init__()
        
        # 获取任务仓库
        self.task_repository = get_task_repository()
        
        # 设置轮询间隔
        self.poll_interval = poll_interval
        
        # 运行状态
        self.running = False
        
        # 任务处理器映射 {task_type: handler_func}
        self.task_handlers = {}
        
        # 获取线程工厂
        self.thread_factory = ThreadFactory.get_instance()
        
        # 上次轮询时间
        self.last_poll_time = 0
        
        # 用于跟踪任务状态变化
        self._tracked_tasks = {}
        
        # 添加轮询定时器
        self._poll_timer = None
        
        # 初始化状态
        print("基于数据库的任务队列已初始化")
    
    def register_handler(self, task_type, handler_func):
        """
        注册任务处理器
        
        Args:
            task_type (str): 任务类型
            handler_func (callable): 处理函数，接收一个参数(task_params)
        """
        self.task_handlers[task_type] = handler_func
        print(f"已注册任务处理器: {task_type}")
    
    def add_task(self, task):
        """
        添加任务到队列
        
        Args:
            task (Task): 任务对象
            
        Returns:
            str: 任务ID
        """
        try:
            # 将任务添加到数据库
            task_id = self.task_repository.add_task(
                task.task_type,
                task.params,
                task.task_id
            )
            
            # 发出任务添加信号
            task.task_id = task_id  # 确保任务ID一致
            self.task_added.emit(task)
            
            return task_id
            
        except Exception as e:
            print(f"添加任务失败: {str(e)}")
            traceback.print_exc()
            raise
    
    def get_task(self, task_id):
        """
        获取任务信息
        
        Args:
            task_id (str): 任务ID
            
        Returns:
            Task: 任务对象，如果任务不存在则返回None
        """
        try:
            # 从数据库获取任务
            task_data = self.task_repository.get_task(task_id)
            if not task_data:
                return None
                
            # 转换为Task对象
            return Task.from_db_row(task_data)
            
        except Exception as e:
            print(f"获取任务失败: {str(e)}")
            traceback.print_exc()
            return None
    
    def get_all_tasks(self, limit=100):
        """
        获取所有任务
        
        Args:
            limit (int): 最大返回数量
            
        Returns:
            list: 任务对象列表
        """
        try:
            # 从数据库获取所有任务
            tasks_data = self.task_repository.get_all_tasks(limit)
            
            # 转换为Task对象列表
            return [Task.from_db_row(task_data) for task_data in tasks_data]
            
        except Exception as e:
            print(f"获取所有任务失败: {str(e)}")
            traceback.print_exc()
            return []
    
    def start_processing(self):
        """开始处理任务队列"""
        if self.running:
            return
            
        self.running = True
        
        # 使用线程工厂创建工作线程
        self.thread_factory.start_thread(
            target=self._process_queue,
            name="DBTaskQueueWorker",
            module="核心业务服务"
        )
        
        # 启动轮询定时器
        self._start_poll_timer()
        
        print("任务队列处理已启动")
    
    def _start_poll_timer(self):
        """启动轮询定时器"""
        try:
            # 创建定时器
            self._poll_timer = QTimer()
            self._poll_timer.timeout.connect(self.poll_task_status_changes)
            # 更加频繁地轮询 - 每0.5秒轮询一次
            self._poll_timer.start(500)  # 转换为毫秒
            
            print(f"[INFO] 任务状态变化轮询定时器已启动，间隔: 0.5秒")
            
            # 立即进行一次轮询
            self.poll_task_status_changes()
            
        except Exception as e:
            print(f"[ERROR] 启动轮询定时器失败: {str(e)}")
            traceback.print_exc()
    
    def stop_processing(self):
        """停止处理任务队列"""
        self.running = False
        
        # 停止轮询定时器
        if self._poll_timer:
            self._poll_timer.stop()
            self._poll_timer = None
            
        print("任务队列处理已停止")
    
    def _process_queue(self):
        """处理任务队列的工作线程"""
        print("任务队列处理线程已启动")
        
        while self.running:
            try:
                # 控制轮询频率
                current_time = time.time()
                if current_time - self.last_poll_time < self.poll_interval:
                    time.sleep(0.5)  # 短暂休眠
                    continue
                    
                self.last_poll_time = current_time
                
                # 获取待处理的任务
                pending_tasks = self.task_repository.get_pending_tasks(limit=5)
                
                if not pending_tasks:
                    # 没有待处理的任务，休眠一段时间
                    time.sleep(self.poll_interval)
                    continue
                
                # 处理每个任务
                for task_data in pending_tasks:
                    task_id = task_data["task_id"]
                    task_type = task_data["task_type"]
                    
                    # 检查是否有对应的处理器
                    if task_type not in self.task_handlers:
                        # 没有处理器，标记为失败
                        self.task_repository.update_task_status(
                            task_id,
                            "failed",
                            error=f"未找到任务处理器: {task_type}",
                            by="任务队列系统"
                        )
                        continue
                    
                    # 将任务状态更新为运行中
                    self.task_repository.update_task_status(
                        task_id,
                        "running",
                        by="任务队列系统"
                    )
                    
                    # 获取更新后的任务
                    task = Task.from_db_row(self.task_repository.get_task(task_id))
                    
                    # 发送任务开始信号
                    self.task_started.emit(task)
                    
                    try:
                        # 执行任务处理器
                        handler = self.task_handlers[task_type]
                        result = handler(task.params)
                        
                        # 更新任务状态为完成
                        self.task_repository.update_task_status(
                            task_id,
                            "completed",
                            result=result,
                            by="任务队列系统"
                        )
                        
                        # 获取更新后的任务
                        task = Task.from_db_row(self.task_repository.get_task(task_id))
                        
                        # 发送任务完成信号
                        self.task_completed.emit(task)
                        
                    except Exception as e:
                        error_msg = str(e)
                        traceback.print_exc()
                        
                        # 更新任务状态为失败
                        self.task_repository.update_task_status(
                            task_id,
                            "failed",
                            error=error_msg,
                            by="任务队列系统"
                        )
                        
                        # 获取更新后的任务
                        task = Task.from_db_row(self.task_repository.get_task(task_id))
                        
                        # 发送任务失败信号
                        self.task_failed.emit(task, error_msg)
                
            except Exception as e:
                print(f"任务处理错误: {str(e)}")
                traceback.print_exc()
                time.sleep(5)  # 发生错误时等待一段时间
    
    def poll_task_status_changes(self):
        """轮询任务状态变化"""
        try:
            # 记录轮询开始
            print(f"[POLL] 开始任务状态轮询 - {time.strftime('%H:%M:%S')}")
            
            # 获取所有任务 - 不再限制状态，以便捕获所有新任务
            all_tasks = self.task_repository.get_all_tasks(100)
            
            # 没有任务时记录信息并返回
            if not all_tasks:
                print("[POLL] 数据库中没有任务")
                return False
                
            print(f"[POLL] 获取到 {len(all_tasks)} 个任务")
            
            # 跟踪新任务和状态变化
            new_tasks = []
            status_changes = []
            
            for task_data in all_tasks:
                task_id = task_data.get("task_id")
                
                # 检查是否是新任务
                if task_id not in self._tracked_tasks:
                    # 创建新任务对象
                    task = Task.from_db_row(task_data)
                    
                    # 添加到跟踪列表
                    self._tracked_tasks[task_id] = task
                    
                    # 记录新任务
                    new_tasks.append(task)
                    print(f"[POLL] 发现新任务: {task_id} - {task.task_type} ({task.status})")
                    
                    # 发出任务添加信号
                    self.task_added.emit(task)
                    
                    # 如果状态不是pending，还需要发出相应的状态信号
                    if task.status == "running":
                        self.task_started.emit(task)
                    elif task.status == "completed":
                        self.task_completed.emit(task)
                    elif task.status == "failed":
                        self.task_failed.emit(task, task.error or "未知错误")
                    continue
                
                # 获取现有任务
                existing_task = self._tracked_tasks[task_id]
                
                # 检查状态是否改变
                if existing_task.status != task_data.get("status"):
                    old_status = existing_task.status
                    new_status = task_data.get("status")
                    
                    # 更新任务对象
                    task = Task.from_db_row(task_data)
                    self._tracked_tasks[task_id] = task
                    
                    # 记录状态变化
                    status_changes.append((task, old_status, new_status))
                    print(f"[POLL] 任务状态变化: {task_id} - {old_status} -> {new_status}")
                    
                    # 发出状态变化信号
                    self.task_status_changed.emit(task, old_status, new_status)
                    
                    # 发出特定状态信号
                    if new_status == "running":
                        self.task_started.emit(task)
                    elif new_status == "completed":
                        self.task_completed.emit(task)
                    elif new_status == "failed":
                        self.task_failed.emit(task, task.error or "未知错误")
                else:
                    # 即使状态未变，也更新任务对象以获取最新信息
                    task = Task.from_db_row(task_data)
                    self._tracked_tasks[task_id] = task
            
            # 汇总轮询结果
            print(f"[POLL] 轮询结果: {len(new_tasks)} 个新任务, {len(status_changes)} 个状态变化")
            return True
            
        except Exception as e:
            print(f"[ERROR] 轮询任务状态变化时出错: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def connect_to_signal(self, signal_name, slot):
        """连接信号到槽函数
        
        这个方法允许外部代码直接连接到任务队列的信号
        
        Args:
            signal_name (str): 信号名称，如 'task_added', 'task_status_changed' 等
            slot (callable): 要连接的槽函数
        """
        try:
            if signal_name == 'task_added':
                self.task_added.connect(slot)
                print(f"[INFO] 已连接task_added信号")
            elif signal_name == 'task_started':
                self.task_started.connect(slot)
                print(f"[INFO] 已连接task_started信号")
            elif signal_name == 'task_completed':
                self.task_completed.connect(slot)
                print(f"[INFO] 已连接task_completed信号")
            elif signal_name == 'task_failed':
                self.task_failed.connect(slot)
                print(f"[INFO] 已连接task_failed信号")
            elif signal_name == 'task_status_changed':
                self.task_status_changed.connect(slot)
                print(f"[INFO] 已连接task_status_changed信号")
            else:
                print(f"[WARNING] 未知的信号名称: {signal_name}")
        except Exception as e:
            print(f"[ERROR] 连接信号 {signal_name} 失败: {str(e)}")
            traceback.print_exc()
    
    def start_polling(self):
        """只启动状态轮询，不处理任务
        
        这个方法用于Flask应用程序启动时，只监控任务状态变化，
        而不实际处理任务，确保任务只能由PyQt应用处理
        """
        if self._poll_timer:
            # 如果已经有定时器，更新轮询频率
            self._poll_timer.stop()
            self._poll_timer.start(500)  # 每0.5秒轮询一次
            print("[INFO] 更新轮询频率为0.5秒一次")
            return
            
        # 启动轮询定时器
        self._start_poll_timer()
        
        # 立即进行一次轮询
        self.poll_task_status_changes()
        
        # 设置多次延迟轮询，确保捕获任务状态变化
        import threading
        def delayed_poll():
            import time
            intervals = [0.3, 0.7, 1.5, 3.0]  # 多次延迟轮询间隔（秒）
            
            for i, interval in enumerate(intervals):
                time.sleep(interval)
                try:
                    print(f"[INFO] 执行第{i+1}次延迟轮询...")
                    # 每次轮询前重置任务跟踪列表
                    if i > 1:  # 从第三次轮询开始重置
                        self._tracked_tasks = {}
                    self.poll_task_status_changes()
                    print(f"[INFO] 第{i+1}次延迟轮询完成")
                except Exception as e:
                    print(f"[ERROR] 第{i+1}次延迟轮询出错: {str(e)}")
                    traceback.print_exc()
                    
            # 清除跟踪列表并再次轮询，确保获取最新状态
            try:
                print("[INFO] 清空任务跟踪列表并执行最终轮询...")
                self._tracked_tasks = {}
                self.poll_task_status_changes()
                print("[INFO] 最终轮询完成")
            except Exception as e:
                print(f"[ERROR] 最终轮询出错: {str(e)}")
                traceback.print_exc()
                
            # 设置永久轮询线程，确保持续检测任务状态
            def permanent_poll():
                print("[INFO] 启动永久轮询线程")
                while True:
                    try:
                        time.sleep(2.0)
                        self._tracked_tasks = {}  # 清空缓存，确保获取最新状态
                        self.poll_task_status_changes()
                    except Exception as e:
                        print(f"[ERROR] 永久轮询出错: {str(e)}")
                        time.sleep(1.0)  # 出错后短暂等待
                        
            # 启动永久轮询线程
            permanent_thread = threading.Thread(target=permanent_poll, daemon=True)
            permanent_thread.start()
            print("[INFO] 永久轮询线程已启动")
        
        threading.Thread(target=delayed_poll, daemon=True).start()
        
        print("[INFO] 任务状态轮询已启动（不处理任务）- 0.5秒轮询间隔，多次延迟轮询机制已激活")

# 创建单例实例
_db_task_queue_instance = None

def get_db_task_queue():
    """获取基于数据库的任务队列单例实例"""
    global _db_task_queue_instance
    if _db_task_queue_instance is None:
        _db_task_queue_instance = DBTaskQueue()
    return _db_task_queue_instance 