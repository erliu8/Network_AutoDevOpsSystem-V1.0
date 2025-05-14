#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
任务同步工具
在Web和PyQt客户端之间同步任务状态
"""

import sys
import os
import time
import traceback
import threading
from pathlib import Path

# 添加项目根目录到系统路径
sys.path.append(str(Path(__file__).parent.parent))

def check_database_connection():
    """检查数据库连接是否正常"""
    try:
        from config.database import test_database_connection
        result = test_database_connection()
        if result:
            print("✓ 数据库连接正常")
        else:
            print("✗ 数据库连接失败")
        return result
    except Exception as e:
        print(f"✗ 数据库连接检查出错: {str(e)}")
        traceback.print_exc()
        return False

def sync_tasks():
    """确保任务状态同步"""
    try:
        # 初始化任务仓库
        from shared.db.task_repository import get_task_repository
        repo = get_task_repository()
        
        # 获取所有任务
        tasks = repo.get_all_tasks(limit=100)
        print(f"发现 {len(tasks)} 个任务")
        
        # 分析任务状态
        status_count = {}
        for task in tasks:
            status = task['status']
            if status not in status_count:
                status_count[status] = 0
            status_count[status] += 1
        
        print("任务状态统计:")
        for status, count in status_count.items():
            print(f"  - {status}: {count}")
        
        # 检测是否存在可能卡住的任务
        pending_tasks = repo.get_tasks_by_status("pending")
        pending_approval_tasks = repo.get_tasks_by_status("pending_approval")
        
        if pending_tasks:
            print(f"警告: 发现 {len(pending_tasks)} 个待处理任务")
            for task in pending_tasks:
                print(f"  - {task['task_id'][:8]} (类型: {task['task_type']})")
        
        if pending_approval_tasks:
            print(f"提示: 发现 {len(pending_approval_tasks)} 个待审核任务")
            for task in pending_approval_tasks:
                print(f"  - {task['task_id'][:8]} (类型: {task['task_type']})")
        
        # 触发任务队列轮询
        from core.business.db_task_queue import get_db_task_queue
        task_queue = get_db_task_queue()
        
        # 清空任务缓存并重新轮询
        if hasattr(task_queue, '_tracked_tasks'):
            task_queue._tracked_tasks = {}
        
        # 强制轮询
        if hasattr(task_queue, 'poll_task_status_changes'):
            print("触发任务队列轮询...")
            task_queue.poll_task_status_changes()
            print("任务队列轮询完成")
        
        return True
    except Exception as e:
        print(f"同步任务失败: {str(e)}")
        traceback.print_exc()
        return False

def start_task_monitor():
    """启动任务监控线程"""
    def monitor_thread():
        print("启动任务监控线程")
        while True:
            try:
                sync_tasks()
                # 每2秒同步一次
                time.sleep(2)
            except Exception as e:
                print(f"任务监控出错: {str(e)}")
                traceback.print_exc()
                time.sleep(5)
    
    print("启动任务监控...")
    thread = threading.Thread(target=monitor_thread, daemon=True)
    thread.start()
    print("任务监控已启动")
    return thread

def main():
    """主函数"""
    print("="*60)
    print(" 任务同步工具")
    print("="*60)
    
    # 检查数据库连接
    if not check_database_connection():
        print("无法连接到数据库，退出")
        return 1
    
    # 同步任务
    print("\n--- 同步任务 ---")
    if not sync_tasks():
        print("任务同步失败，退出")
        return 1
    
    # 启动监控线程
    monitor_thread = start_task_monitor()
    
    # 等待按下Ctrl+C
    print("\n任务同步器已启动，按Ctrl+C停止")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n接收到停止信号，正在停止...")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 