#!/usr/bin/env python
# test_approval.py - 测试任务审批模块

import sys
import os
import time
from PyQt5.QtWidgets import QApplication

# 添加项目根目录到系统路径
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

def main():
    """测试任务审批模块"""
    print("启动任务审批模块测试...")
    
    app = QApplication(sys.argv)
    
    # 创建任务队列
    from core.business.task_queue import TaskQueue
    task_queue = TaskQueue()
    
    # 创建一些测试任务
    create_test_tasks(task_queue)
    
    # 启动任务处理
    task_queue.start_processing()
    
    # 创建审批窗口
    from modules.final_approval.gui import ApprovalWindow
    approval_window = ApprovalWindow()
    approval_window.show()
    
    print("已创建任务审批窗口")
    
    # 执行应用程序主循环
    sys.exit(app.exec_())

def create_test_tasks(task_queue):
    """创建测试任务"""
    from core.business.task_queue import Task
    from datetime import datetime
    import uuid
    
    print("创建测试任务...")
    
    # DHCP配置任务1
    dhcp_task1 = Task("dhcp_config", {
        'device_ids': ['1', '2'],
        'pool_name': 'TEST_POOL_1',
        'network': '192.168.1.0',
        'mask': '255.255.255.0',
        'gateway': '192.168.1.1',
        'dns': '8.8.8.8',
        'lease_days': 3,
        'status': 'pending_approval',
        'requested_at': time.time(),
        'requested_by': '127.0.0.1'
    })
    dhcp_task1.created_at = datetime.now()
    task_queue.add_task(dhcp_task1)
    
    # DHCP配置任务2
    dhcp_task2 = Task("dhcp_config", {
        'device_ids': ['3'],
        'pool_name': 'TEST_POOL_2',
        'network': '10.0.0.0',
        'mask': '255.255.0.0',
        'gateway': '10.0.0.1',
        'dns': '114.114.114.114',
        'lease_days': 7,
        'status': 'pending_approval',
        'requested_at': time.time(),
        'requested_by': '192.168.0.100'
    })
    dhcp_task2.created_at = datetime.now()
    task_queue.add_task(dhcp_task2)
    
    # 路由配置任务
    route_task = Task("route_config", {
        'device_ids': ['1'],
        'routes': [
            {'dest': '10.0.0.0/24', 'next_hop': '192.168.1.254'},
            {'dest': '172.16.0.0/16', 'next_hop': '192.168.1.253'}
        ],
        'status': 'pending_approval',
        'requested_at': time.time(),
        'requested_by': '192.168.0.101'
    })
    route_task.created_at = datetime.now()
    task_queue.add_task(route_task)
    
    # 已完成的任务
    completed_task = Task("dhcp_config", {
        'device_ids': ['4'],
        'pool_name': 'COMPLETED_POOL',
        'network': '172.16.0.0',
        'mask': '255.255.0.0',
        'status': 'completed',
        'requested_at': time.time() - 3600,
        'requested_by': '10.0.0.1'
    })
    completed_task.created_at = datetime.now()
    completed_task.status = "completed"
    completed_task.result = {"success": True, "message": "配置成功"}
    completed_task.completed_at = datetime.now()
    task_queue.add_task(completed_task)
    
    # 已拒绝的任务
    rejected_task = Task("dhcp_config", {
        'device_ids': ['5'],
        'pool_name': 'REJECTED_POOL',
        'network': '192.168.100.0',
        'mask': '255.255.255.0',
        'status': 'rejected',
        'requested_at': time.time() - 7200,
        'requested_by': '10.0.0.2'
    })
    rejected_task.created_at = datetime.now()
    rejected_task.status = "rejected"
    rejected_task.error = "配置参数无效"
    rejected_task.completed_at = datetime.now()
    task_queue.add_task(rejected_task)
    
    print(f"已创建 {task_queue.queue.qsize()} 个测试任务")

if __name__ == "__main__":
    main() 