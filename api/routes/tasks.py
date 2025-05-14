from flask import Blueprint, request, jsonify
from core.business.task_queue import Task
import time
import json

# 创建蓝图
tasks_bp = Blueprint('tasks', __name__)

@tasks_bp.route('/dhcp', methods=['POST'])
def create_dhcp_task():
    """创建DHCP配置任务"""
    # 获取全局任务队列
    from api.app import task_queue
    if not task_queue:
        return jsonify({"error": "任务队列未初始化"}), 500
    
    # 解析请求数据
    data = request.json
    if not data:
        return jsonify({"error": "无效的请求数据"}), 400
    
    # 验证必要字段
    required_fields = ['device_ids', 'pool_name', 'network', 'mask']
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        return jsonify({"error": f"缺少必要字段: {', '.join(missing_fields)}"}), 400
    
    # 创建任务参数
    task_params = {
        'device_ids': data['device_ids'],
        'pool_name': data['pool_name'],
        'network': data['network'],
        'mask': data['mask'],
        'gateway': data.get('gateway'),
        'dns': data.get('dns'),
        'domain': data.get('domain'),
        'lease_days': data.get('lease_days', 1),
        'status': 'pending_approval',  # 初始状态为待审核
        'requested_at': time.time(),
        'requested_by': request.remote_addr
    }
    
    # 创建任务
    task = Task("dhcp_config", task_params)
    
    # 添加到队列
    task_id = task_queue.add_task(task)
    
    return jsonify({
        "task_id": task_id,
        "status": "pending_approval",
        "message": "DHCP配置任务已创建，等待管理员审核"
    })

@tasks_bp.route('/status/<task_id>', methods=['GET'])
def get_task_status(task_id):
    """获取任务状态"""
    from api.app import task_queue
    if not task_queue:
        return jsonify({"error": "任务队列未初始化"}), 500
    
    task = task_queue.get_task(task_id)
    if not task:
        return jsonify({"error": "任务不存在"}), 404
    
    return jsonify({
        "task_id": task.task_id,
        "status": task.status,
        "result": task.result,
        "error": task.error
    })

@tasks_bp.route('/pending', methods=['GET'])
def get_pending_tasks():
    """获取所有待审核的任务"""
    from api.app import task_queue
    if not task_queue:
        return jsonify({"error": "任务队列未初始化"}), 500
    
    tasks = task_queue.get_all_tasks()
    pending_tasks = [task.to_dict() for task in tasks 
                    if task.status == "pending_approval" 
                    and task.task_type == "dhcp_config"]
    
    return jsonify(pending_tasks)
