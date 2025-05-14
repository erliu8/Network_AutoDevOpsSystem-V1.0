# devices.py
from flask import Blueprint, request, jsonify
import sys
from pathlib import Path

# 添加项目根目录到系统路径
sys.path.append(str(Path(__file__).parent.parent.parent))
from core.repositories.device_repository import DeviceRepository

# 创建蓝图
devices_bp = Blueprint('devices', __name__)

# 设备仓库实例
device_repository = DeviceRepository()

@devices_bp.route('', methods=['GET'])
def get_devices():
    """获取所有设备"""
    devices = device_repository.get_all_devices()
    return jsonify(devices)

@devices_bp.route('/<int:device_id>', methods=['GET'])
def get_device(device_id):
    """获取单个设备"""
    device = device_repository.get_device_by_id(device_id)
    if not device:
        return jsonify({"error": "设备不存在"}), 404
    return jsonify(device)

@devices_bp.route('', methods=['POST'])
def create_device():
    """创建设备"""
    data = request.json
    if not data:
        return jsonify({"error": "无效的请求数据"}), 400
    
    # 验证必要字段
    required_fields = ['name', 'ip', 'username', 'password', 'device_type']
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"缺少必要字段: {field}"}), 400
    
    try:
        device = device_repository.create_device(data)
        return jsonify(device), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@devices_bp.route('/<int:device_id>', methods=['PUT'])
def update_device(device_id):
    """更新设备"""
    data = request.json
    if not data:
        return jsonify({"error": "无效的请求数据"}), 400
    
    try:
        device = device_repository.update_device(device_id, data)
        if not device:
            return jsonify({"error": "设备不存在"}), 404
        return jsonify(device)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@devices_bp.route('/<int:device_id>', methods=['DELETE'])
def delete_device(device_id):
    """删除设备"""
    try:
        success = device_repository.delete_device(device_id)
        if not success:
            return jsonify({"error": "设备不存在"}), 404
        return jsonify({"message": "设备已删除"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
from core.business.task_queue import Task

@devices_bp.route('/api/devices/config', methods=['POST'])
def configure_device():
    """配置设备"""
    data = request.json
    if not data:
        return jsonify({"error": "无效的请求数据"}), 400
    
    # 创建设备配置任务
    task = Task("device_config", data)
    
    # 添加到任务队列
    from api.app import task_queue
    task_id = task_queue.add_task(task)
    
    return jsonify({
        "task_id": task_id,
        "status": "pending"
    })

@devices_bp.route('/api/devices/status', methods=['GET'])
def get_devices_status():
    """获取所有设备状态"""
    # 这里可以从设备管理服务获取设备状态
    # 简化示例，实际应该从设备管理服务获取
    devices = [
        {"ip": "10.1.0.3", "name": "LSW1", "type": "地域1核心交换机", "status": "online"},
        {"ip": "10.1.200.1", "name": "AR5", "type": "地域1出口路由器", "status": "online"},
        {"ip": "10.1.18.1", "name": "AR1", "type": "地域2出口路由器", "status": "offline"},
    ]
    
    return jsonify(devices)