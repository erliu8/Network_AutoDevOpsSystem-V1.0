from flask import Blueprint, request, jsonify, render_template
import json
import time
import traceback
from core.business.task_queue import Task  # 保留任务类用于兼容性
from core.repositories.device_repository import DeviceRepository  # 导入设备仓库

# 移除直接导入，避免循环导入
# from api.app import get_flask_task_adapter

# 创建蓝图
dhcp_bp = Blueprint('dhcp', __name__, template_folder='templates')

# 动态获取任务适配器函数
def get_task_adapter():
    """动态导入任务适配器，避免循环导入"""
    from api.app import get_flask_task_adapter
    return get_flask_task_adapter()

@dhcp_bp.route('/')
@dhcp_bp.route('/config')
def dhcp_config_view():
    """DHCP配置页面"""
    try:
        print("[INFO] ******************************************")
        print("[INFO] 开始处理DHCP页面请求 - 使用修改后的dhcp.html模板!")
        print("[INFO] ******************************************")
        
        try:
            # 尝试从设备仓库获取设备
            device_repository = DeviceRepository()
            devices = device_repository.get_all_devices()
            print(f"[INFO] 从设备仓库获取到 {len(devices)} 个设备")
        except Exception as device_error:
            print(f"[ERROR] 设备仓库出错: {str(device_error)}")
            traceback.print_exc()
            # 如果设备仓库出错，使用演示设备
            devices = [
                {"id": 1, "name": "核心交换机1", "ip": "10.1.1.1", "type": "交换机"},
                {"id": 2, "name": "核心路由器1", "ip": "10.1.1.254", "type": "路由器"},
                {"id": 3, "name": "接入交换机1", "ip": "10.1.2.1", "type": "交换机"},
                {"id": 4, "name": "接入交换机2", "ip": "10.1.2.2", "type": "交换机"},
                {"id": 5, "name": "防火墙1", "ip": "10.1.1.2", "type": "防火墙"}
            ]
            print(f"[INFO] 使用 {len(devices)} 个演示设备")
        
        # 使用标准模板渲染页面
        return render_template('dhcp.html', devices=devices)
                
    except Exception as e:
        import traceback
        print(f"[ERROR] 处理DHCP页面请求时出错: {str(e)}")
        traceback.print_exc()
        return f"服务器错误: {str(e)}", 500

@dhcp_bp.route('/submit', methods=['POST'])
def submit_dhcp_config():
    """提交DHCP配置任务"""
    # 获取任务适配器
    task_adapter = get_task_adapter()
    if not task_adapter:
        return jsonify({"error": "任务适配器未初始化"}), 500
    
    # 解析请求数据
    data = request.json
    if not data:
        return jsonify({"error": "无效的请求数据"}), 400
    
    # 验证必要字段
    required_fields = ['device_ids', 'pool_name', 'network', 'mask']
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        return jsonify({"error": f"缺少必要字段: {', '.join(missing_fields)}"}), 400
    
    # 增加详细日志记录原始数据
    print(f"[DEBUG] 原始提交数据: {json.dumps(data, ensure_ascii=False)}")
    
    # 设备ID格式标准化处理 - 确保是字符串列表
    device_ids = data['device_ids']
    if isinstance(device_ids, str):
        if ',' in device_ids:
            device_ids = [id.strip() for id in device_ids.split(',')]
        else:
            device_ids = [device_ids]
    elif not isinstance(device_ids, list):
        device_ids = [str(device_ids)]
    
    # 网络地址格式化处理
    network = data['network'].strip() if data.get('network') else ''
    mask = data['mask'].strip() if data.get('mask') else ''
    
    # DNS服务器格式化处理
    dns = None
    if data.get('dns'):
        if isinstance(data['dns'], list):
            dns = data['dns'][0]  # 使用第一个DNS服务器
        else:
            dns_value = data['dns'].strip()
            if ',' in dns_value:
                # 如果是逗号分隔的多个DNS，只取第一个
                dns = dns_value.split(',')[0].strip()
            else:
                dns = dns_value
    
    # 网关格式化处理
    gateway = data.get('gateway', '').strip() if data.get('gateway') else None
    
    # 创建任务参数 - 不再设置状态，状态由数据库控制
    task_params = {
        'device_ids': device_ids,
        'pool_name': data['pool_name'].strip(),
        'network': network,
        'mask': mask,
        'gateway': gateway,
        'dns': dns,
        'domain': data.get('domain', '').strip() if data.get('domain') else None,
        'lease_days': int(data.get('lease_days', 1)) if data.get('lease_days') else 1,
        'requested_at': time.time(),
        'requested_by': data.get('requested_by', request.remote_addr)
    }
    
    print(f"[INFO] 正在提交DHCP配置任务: {task_params['pool_name']} - {task_params['network']}/{task_params['mask']}")
    print(f"[DEBUG] 设备ID列表: {task_params['device_ids']}")
    print(f"[DEBUG] 格式化后的参数: {json.dumps(task_params, ensure_ascii=False)}")
    
    # 添加任务到数据库
    try:
        # 使用任务适配器添加任务 - 此时状态为pending
        task_id = task_adapter.add_task("dhcp_config", task_params)
        print(f"[INFO] DHCP配置任务已创建 (ID: {task_id})")
        
        # 立即将任务状态改为pending_approval
        try:
            # 直接使用任务仓库更新状态，确保状态立即变更
            from shared.db.task_repository import get_task_repository
            task_repo = get_task_repository()
            
            update_success = task_repo.update_task_status(
                task_id, 
                "pending_approval", 
                by=f"Web提交({request.remote_addr})"
            )
            
            if update_success:
                print(f"[INFO] 任务 {task_id} 状态已立即设置为pending_approval")
            else:
                print(f"[WARNING] 无法设置任务 {task_id} 状态为pending_approval")
        except Exception as status_err:
            print(f"[ERROR] 更新任务状态时出错: {str(status_err)}")
            traceback.print_exc()
        
        # 返回成功响应，明确指出任务需要审批
        return jsonify({
            "task_id": task_id,
            "status": "pending_approval",
            "message": "DHCP配置任务已创建，等待管理员审核",
            "requires_approval": True,  # 明确指出需要审批
            "formatted_params": task_params  # 返回格式化后的参数，方便调试
        })
    except Exception as e:
        print(f"[ERROR] 创建DHCP配置任务失败: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": f"创建任务失败: {str(e)}"}), 500

@dhcp_bp.route('/status/<task_id>', methods=['GET'])
def get_dhcp_task_status(task_id):
    """获取DHCP任务状态"""
    # 获取任务适配器
    task_adapter = get_task_adapter()
    if not task_adapter:
        return jsonify({"error": "任务适配器未初始化"}), 500
    
    # 获取任务
    task = task_adapter.get_task(task_id)
    if not task:
        return jsonify({"error": "任务不存在"}), 404
    
    # 确保这是一个DHCP配置任务
    if task.get("task_type") != "dhcp_config":
        return jsonify({"error": "不是DHCP配置任务"}), 400
    
    # 构建状态响应
    status_map = {
        "pending": "等待中",
        "pending_approval": "等待审核",
        "approved": "已审核",
        "rejected": "已拒绝",
        "running": "执行中",
        "completed": "已完成",
        "failed": "失败"
    }
    
    response = {
        "task_id": task.get("task_id"),
        "status": task.get("status"),
        "status_text": status_map.get(task.get("status"), task.get("status")),
        "created_at": task.get("created_at"),
        "completed_at": task.get("completed_at")
    }
    
    # 添加结果或错误信息
    if task.get("result"):
        response["result"] = task.get("result")
    if task.get("error"):
        response["error"] = task.get("error")
    
    return jsonify(response)

@dhcp_bp.route('/approve/<task_id>', methods=['POST'])
def approve_dhcp_task(task_id):
    """审批DHCP任务"""
    # 获取任务适配器
    task_adapter = get_task_adapter()
    if not task_adapter:
        return jsonify({"error": "任务适配器未初始化"}), 500
    
    # 获取任务
    task = task_adapter.get_task(task_id)
    if not task:
        return jsonify({"error": "任务不存在"}), 404
    
    # 确保这是一个DHCP配置任务
    if task.get("task_type") != "dhcp_config":
        return jsonify({"error": "不是DHCP配置任务"}), 400
    
    # 确保任务处于待审核状态
    if task.get("status") != "pending_approval":
        return jsonify({"error": "任务不在待审核状态"}), 400
    
    # 更新任务状态为已审核
    success = task_adapter.update_task_status(
        task_id, 
        "approved", 
        result={"message": "任务已通过审核，等待执行"}
    )
    
    if not success:
        return jsonify({"error": "更新任务状态失败"}), 500
    
    return jsonify({
        "success": True,
        "message": "任务已审核通过，等待执行"
    })

@dhcp_bp.route('/reject/<task_id>', methods=['POST'])
def reject_dhcp_task(task_id):
    """拒绝DHCP任务"""
    # 获取任务适配器
    task_adapter = get_task_adapter()
    if not task_adapter:
        return jsonify({"error": "任务适配器未初始化"}), 500
    
    # 获取任务
    task = task_adapter.get_task(task_id)
    if not task:
        return jsonify({"error": "任务不存在"}), 404
    
    # 确保这是一个DHCP配置任务
    if task.get("task_type") != "dhcp_config":
        return jsonify({"error": "不是DHCP配置任务"}), 400
    
    # 确保任务处于待审核状态
    if task.get("status") != "pending_approval":
        return jsonify({"error": "任务不在待审核状态"}), 400
    
    # 获取拒绝原因
    data = request.json or {}
    reason = data.get("reason", "未提供拒绝原因")
    
    # 更新任务状态为已拒绝
    success = task_adapter.update_task_status(
        task_id, 
        "rejected", 
        result={"message": f"任务被拒绝: {reason}"}
    )
    
    if not success:
        return jsonify({"error": "更新任务状态失败"}), 500
    
    return jsonify({
        "success": True,
        "message": f"任务已被拒绝: {reason}"
    })

@dhcp_bp.route('/pending', methods=['GET'])
def get_pending_dhcp_tasks():
    """获取待审核的DHCP任务"""
    # 获取任务适配器
    task_adapter = get_task_adapter()
    if not task_adapter:
        return jsonify({"error": "任务适配器未初始化"}), 500
    
    # 获取待审核任务
    pending_tasks = task_adapter.get_tasks_by_status("pending_approval", "dhcp_config")
    
    # 返回任务列表
    return jsonify(pending_tasks) 