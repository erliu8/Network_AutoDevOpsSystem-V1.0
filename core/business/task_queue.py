# task_queue.py
import queue
import threading
import time
import json
import uuid
from datetime import datetime
from PyQt5.QtCore import QObject, pyqtSignal
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
    
    @classmethod
    def from_dict(cls, data):
        """从字典创建任务"""
        task = cls(data["task_type"], data["params"], data["task_id"])
        task.status = data["status"]
        task.result = data["result"]
        task.error = data["error"]
        task.created_at = datetime.fromisoformat(data["created_at"]) if data["created_at"] else None
        task.started_at = datetime.fromisoformat(data["started_at"]) if data["started_at"] else None
        task.completed_at = datetime.fromisoformat(data["completed_at"]) if data["completed_at"] else None
        return task

class TaskQueue(QObject):
    """任务队列类，管理任务的添加、执行和状态更新"""
    
    # 定义信号
    task_added = pyqtSignal(object)  # 任务添加信号
    task_started = pyqtSignal(object)  # 任务开始执行信号
    task_completed = pyqtSignal(object)  # 任务完成信号
    task_failed = pyqtSignal(object, str)  # 任务失败信号
    
    def __init__(self):
        super().__init__()
        self.queue = queue.Queue()
        self.tasks = {}  # 存储所有任务 {task_id: Task}
        self.running = False
        
        # 获取线程工厂实例
        self.thread_factory = ThreadFactory.get_instance()
        
        # 任务处理器映射
        self.task_handlers = {
            # 示例: "device_config": self._handle_device_config,
        }
    
    def register_handler(self, task_type, handler_func):
        """注册任务处理器"""
        self.task_handlers[task_type] = handler_func
    
    def add_task(self, task):
        """添加任务到队列"""
        self.tasks[task.task_id] = task
        self.queue.put(task)
        self.task_added.emit(task)
        return task.task_id
    
    def get_task(self, task_id):
        """获取任务信息"""
        return self.tasks.get(task_id)
    
    def get_all_tasks(self):
        """获取所有任务"""
        return list(self.tasks.values())
    
    def start_processing(self):
        """开始处理任务队列"""
        if self.running:
            return
        
        self.running = True
        # 使用线程工厂创建工作线程
        self.thread_factory.start_thread(
            target=self._process_queue,
            name="TaskQueueWorker",
            module="核心业务服务"
        )
    
    def stop_processing(self):
        """停止处理任务队列"""
        self.running = False
    
    def _process_queue(self):
        """处理任务队列的工作线程"""
        while self.running:
            try:
                # 尝试从队列获取任务，等待1秒
                try:
                    task = self.queue.get(timeout=1.0)
                except queue.Empty:
                    continue
                
                # 更新任务状态
                task.status = "running"
                task.started_at = datetime.now()
                self.task_started.emit(task)
                
                # 查找并执行对应的任务处理器
                if task.task_type in self.task_handlers:
                    handler = self.task_handlers[task.task_type]
                    try:
                        result = handler(task.params)
                        task.result = result
                        task.status = "completed"
                        task.completed_at = datetime.now()
                        self.task_completed.emit(task)
                    except Exception as e:
                        task.error = str(e)
                        task.status = "failed"
                        task.completed_at = datetime.now()
                        self.task_failed.emit(task, str(e))
                else:
                    task.error = f"未知的任务类型: {task.task_type}"
                    task.status = "failed"
                    task.completed_at = datetime.now()
                    self.task_failed.emit(task, task.error)
                
                # 标记队列任务完成
                self.queue.task_done()
                
            except Exception as e:
                print(f"任务处理错误: {str(e)}")
                time.sleep(1)  # 避免CPU占用过高