#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
启动PyQt应用程序
"""

import sys
import os
import traceback
import time
from pathlib import Path

# 添加项目根目录到系统路径
sys.path.append(str(Path(__file__).parent))

# 设置环境变量 - 防止潜在冲突
os.environ["FLASK_APP"] = ""
os.environ["FLASK_ENV"] = ""
os.environ["FLASK_DEBUG"] = "0"

# 打印启动信息
print("="*80)
print(" 启动PyQt运维自动化应用程序 ")
print("="*80)

# 初始化任务处理系统，使用WebSocket而不是数据库轮询
def init_task_system():
    """初始化任务处理系统，使用WebSocket连接到服务器接收任务通知"""
    try:
        print("初始化WebSocket任务通知系统...")
        
        # 导入WebSocket客户端
        from shared.websocket.client import get_client
        
        # 导入任务队列，用于处理已通知的任务
        from core.business.db_task_queue import get_db_task_queue, Task
        
        # 获取WebSocket客户端实例
        websocket_client = get_client()
        
        # 获取任务队列实例
        task_queue = get_db_task_queue()
        
        # 定义任务处理函数
        def on_task_added(task):
            print(f"[TASK] 新任务添加: ID={task.task_id}, 类型={task.task_type}, 状态={task.status}")
            
        def on_task_status_changed(task, old_status, new_status):
            print(f"[TASK] 任务状态变化: ID={task.task_id}, {old_status} -> {new_status}")
        
        # 连接任务队列信号
        print("连接任务队列信号...")
        task_queue.connect_to_signal('task_added', on_task_added)
        task_queue.connect_to_signal('task_status_changed', on_task_status_changed)
        
        # 定义WebSocket消息处理函数
        def on_websocket_message(message):
            print(f"[WS] 收到WebSocket消息: {message}")
            
            # 处理通用消息
            message_type = message.get('type')
            if not message_type:
                return
                
            # 处理连接确认消息
            if message_type == 'register_response':
                print(f"[WS] 连接确认: {message.get('message')}")
                
        # 定义任务通知处理函数
        def on_task_notification(message):
            print(f"[WS] 收到任务状态变化通知: {message}")
            
            # 解析任务通知
            task_id = message.get('task_id')
            status = message.get('status')
            
            if not task_id or not status:
                print("[WS] 任务通知缺少必要信息")
                return
                
            # 获取数据库中的任务信息并更新本地缓存
            from shared.db.task_repository import get_task_repository
            task_repo = get_task_repository()
            task_data = task_repo.get_task(task_id)
            
            if not task_data:
                print(f"[WS] 无法从数据库获取任务 {task_id}")
                return
                
            # 转换为任务对象
            task = Task.from_db_row(task_data)
            
            # 更新任务队列中的任务状态缓存
            if task_id in task_queue._tracked_tasks:
                old_status = task_queue._tracked_tasks[task_id].status
                task_queue._tracked_tasks[task_id] = task
                
                # 发出任务状态变化信号
                if old_status != status:
                    task_queue.task_status_changed.emit(task, old_status, status)
                    
                    # 对应特定状态发出特定信号
                    if status == "running":
                        task_queue.task_started.emit(task)
                    elif status == "completed":
                        task_queue.task_completed.emit(task)
                    elif status == "failed":
                        task_queue.task_failed.emit(task, task.error or "未知错误")
            else:
                # 新任务，添加到跟踪列表
                task_queue._tracked_tasks[task_id] = task
                task_queue.task_added.emit(task)
                
                # 如果状态不是pending，还需要发出相应的状态信号
                if status == "running":
                    task_queue.task_started.emit(task)
                elif status == "completed":
                    task_queue.task_completed.emit(task)
                elif status == "failed":
                    task_queue.task_failed.emit(task, task.error or "未知错误")
        
        # 连接WebSocket信号
        print("连接WebSocket客户端信号...")
        websocket_client.message_received.connect(on_websocket_message)
        websocket_client.task_notification.connect(on_task_notification)
        
        # 连接WebSocket服务器
        print("启动WebSocket客户端...")
        websocket_client.start()
        
        # 执行一次数据库同步，获取已存在的任务
        print("从数据库同步任务状态...")
        task_queue.poll_task_status_changes()
        
        # 启动任务队列处理线程，但不启动轮询线程
        print("启动任务队列处理线程...")
        task_queue.start_processing()
        
        return True
    except Exception as e:
        print(f"初始化任务系统失败: {str(e)}")
        traceback.print_exc()
        return False

def main():
    """主程序入口"""
    try:
        # 初始化任务处理系统
        init_task_system()
        
        # 导入PyQt和主程序模块
        print("导入PyQt和主程序模块...")
        from PyQt5.QtWidgets import QApplication
        from main import MainApp
        
        # 创建应用程序
        print("创建应用程序...")
        app = QApplication(sys.argv)
        app.setApplicationName("自动运维平台")
        app.setStyle("Fusion")  # 使用Fusion风格
        
        # 确保数据库连接正常
        from config.database import test_database_connection
        if not test_database_connection():
            print("数据库连接失败，请检查数据库配置")
            return 1
        
        # 创建主窗口
        print("创建主窗口...")
        main_app = MainApp()
        
        # 显示主窗口
        print("显示主窗口...")
        main_app.show()
        
        # 启动应用程序主循环
        print("启动应用程序主循环...")
        return app.exec_()
        
    except Exception as e:
        print(f"启动应用程序出错: {str(e)}")
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main()) 