#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
集成启动脚本
同时启动Flask Web应用和任务管理服务
"""

import sys
import os
import signal
import traceback
from pathlib import Path
import time
import json
import socket

# 应用DHCP连接补丁
try:
    from dhcp_connector_patch import fix_dhcp_configurator
    fix_result = fix_dhcp_configurator()
    print(f"DHCP连接补丁应用结果: {'成功' if fix_result else '失败'}")
except Exception as e:
    print(f"应用DHCP连接补丁失败: {str(e)}")

# 添加获取IP地址的函数
def get_ip_addresses():
    """获取本机所有IP地址"""
    ip_list = []
    try:
        # 获取主机名
        hostname = socket.gethostname()
        # 获取主机名对应的IP地址
        host_ip = socket.gethostbyname(hostname)
        ip_list.append(("主机名IP", host_ip))
        
        # 尝试获取所有网络接口
        for interface_name in socket.if_nameindex():
            try:
                # 这里使用一个技巧，创建一个临时socket连接到外网，获取本地出口IP
                if interface_name[1] != 'lo':  # 跳过本地环回接口
                    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                        # 这里不会真正建立连接，只是获取本地IP
                        s.connect(('8.8.8.8', 1))
                        local_ip = s.getsockname()[0]
                        ip_list.append((interface_name[1], local_ip))
            except:
                pass
    except Exception as e:
        print(f"获取IP地址时出错: {e}")
    
    return ip_list

# 添加项目根目录到系统路径
sys.path.append(str(Path(__file__).parent))

# 设置Flask应用默认配置
os.environ["FLASK_APP"] = "api.app"
os.environ["FLASK_ENV"] = "development"
# 禁用调试模式，避免自动重载
os.environ["FLASK_DEBUG"] = "0"

print("="*80)
print(" 启动集成了任务管理服务的Web应用 ")
print(f" 端口: 5000 | 调试模式: 禁用")
print("="*80)

# 获取并显示所有IP地址
ip_addresses = get_ip_addresses()
print("\n" + "="*30 + " 服务器IP地址 " + "="*30)
for name, ip in ip_addresses:
    print(f"网络接口: {name:<10} | IP地址: {ip:<15}")
    
if ip_addresses:
    print("\n您可以通过以下地址访问Web界面:")
    for name, ip in ip_addresses:
        if ip != '127.0.0.1':  # 排除本地环回地址
            print(f"http://{ip}:5000")
    print("="*80)
else:
    print("\n警告: 未找到有效的网络接口IP地址，您可能无法通过网络访问该服务")
    print("您仍然可以尝试通过 http://localhost:5000 或 http://127.0.0.1:5000 在本机访问")
    print("="*80)

# 启动WebSocket服务器
def start_websocket_server():
    """启动WebSocket服务器，用于任务通知"""
    try:
        from shared.websocket.server import get_server
        from shared.websocket.handlers import init_websocket_handlers, DashboardDataHandler
        
        # 获取WebSocket服务器实例
        server = get_server()
        
        # 启动WebSocket服务器
        print("\n=== 启动WebSocket服务器 ===")
        server.start()
        print(f"WebSocket服务器已启动在 ws://{server.host}:{server.port}")
        
        # 初始化WebSocket处理程序
        print("\n=== 初始化WebSocket处理程序 ===")
        init_websocket_handlers()
        
        # 启动定期数据更新
        print("\n=== 启动WebSocket数据更新线程 ===")
        update_thread = DashboardDataHandler.start_periodic_updates()
        print("WebSocket数据更新线程已启动")
        
        return server
    except Exception as e:
        print(f"启动WebSocket服务器失败: {str(e)}")
        traceback.print_exc()
        return None

# 全局WebSocket服务器实例
websocket_server = start_websocket_server()

# 导入Flask应用和任务管理器
try:
    from api.app import app, socketio, has_websocket, start_task_manager
except ImportError as e:
    print(f"导入Flask应用失败: {str(e)}")
    traceback.print_exc()
    sys.exit(1)

# 启动任务管理服务
try:
    from tasks.task_manager import TaskManager
    from core.business.db_task_queue import get_db_task_queue
    from shared.db.task_repository import get_task_repository
    from shared.websocket.handlers import broadcast_task_notification
    
    # 确保任务管理器初始化数据库连接
    task_manager = TaskManager(poll_interval=10.0)
    
    # 启动任务管理器
    task_manager.start()
    
    # 添加通知函数用于主动通知任务状态变化
    def notify_task_status_change(task_id, new_status=None):
        """通知所有客户端任务状态变化
        
        Args:
            task_id: 任务ID
            new_status: 新状态，如果为None，会自动从数据库获取
        """
        try:
            print(f"[INFO] 主动通知任务 {task_id} 状态变化...")
            
            # 如果未提供状态，从数据库获取
            if new_status is None:
                task_repo = get_task_repository()
                task_data = task_repo.get_task(task_id)
                if task_data:
                    new_status = task_data.get('status')
                else:
                    print(f"[WARNING] 找不到任务 {task_id}，无法通知状态变化")
                    return
            
            print(f"[INFO] 任务 {task_id} 新状态: {new_status}")
            
            # 使用WebSocket广播任务状态变化
            if websocket_server:
                # 构建通知消息
                message = {
                    "type": "task_status_change",
                    "task_id": task_id,
                    "status": new_status,
                    "timestamp": time.time()
                }
                
                # 使用WebSocket广播
                websocket_server.broadcast_sync(message)
                print(f"[INFO] 已通过WebSocket广播任务状态变化: {task_id} -> {new_status}")
            else:
                # 使用专用的广播函数
                result = broadcast_task_notification(task_id, new_status)
                if result:
                    print(f"[INFO] 已通过广播函数发送任务状态变化: {task_id} -> {new_status}")
                else:
                    print(f"[WARNING] 通过广播函数发送任务状态变化失败")
                    
            # 尝试通过数据库轮询通知 - 兼容旧的轮询机制
            try:
                # 确保任务队列正在轮询
                db_task_queue = get_db_task_queue()
                if hasattr(db_task_queue, 'poll_task_status_changes'):
                    db_task_queue.poll_task_status_changes()
                    print("[INFO] 已触发任务队列轮询以兼容旧客户端")
            except Exception as poll_error:
                print(f"[WARNING] 触发任务轮询失败: {str(poll_error)}")
                
        except Exception as e:
            print(f"[ERROR] 通知任务状态变化时出错: {str(e)}")
            traceback.print_exc()
    
    # 修改dhcp_config_adapter函数，增强调试日志级别
    def dhcp_config_adapter(params):
        """DBTaskQueue处理函数适配器，将单参数转换为任务管理器需要的双参数格式"""
        # 为了调试，记录实际参数
        print(f"[DEBUG] DHCP适配器收到参数: {type(params)} - {json.dumps(params, ensure_ascii=False)[:1000] if isinstance(params, dict) else str(params)[:1000]}")
        
        # 从仓库中获取任务ID和完整任务数据
        try:
            task_repo = get_task_repository()
            
            # 如果参数已经是字典且包含task_id，则直接使用
            if isinstance(params, dict) and 'task_id' in params:
                task_id = params['task_id']
                task_data = task_repo.get_task(task_id)
                
                if not task_data:
                    print(f"[ERROR] 找不到任务 {task_id}")
                    return {
                        "status": "error",
                        "message": f"找不到任务 {task_id}"
                    }
                
                # 检查任务状态
                task_status = task_data.get('status', 'unknown')
                print(f"[DEBUG] 任务 {task_id} 当前状态: {task_status}")
                
                # 只有approved状态的任务才能执行
                if task_status != 'approved':
                    print(f"[WARNING] 任务 {task_id} 状态为 {task_status}，尚未被批准，跳过执行")
                    return {
                        "status": task_status,
                        "message": "任务尚未被批准，请等待审批"
                    }
                
                print(f"[INFO] Web服务开始执行已批准的任务 {task_id}")
                
                # 执行任务前先将状态更新为running
                task_repo.update_task_status(
                    task_id,
                    "running",
                    by="Web服务"
                )
                
                # 立即通知任务状态变化
                notify_task_status_change(task_id, "running")
                
                # 执行任务 - 确保传递正确的参数格式
                print(f"[INFO] 开始执行任务 {task_id}，参数: {json.dumps(task_data.get('params', {}), ensure_ascii=False)[:500]}")
                result = task_manager._handle_dhcp_config(task_id, task_data)
                print(f"[DEBUG] 任务 {task_id} 原始执行结果: {json.dumps(result, ensure_ascii=False)[:1000] if result else 'None'}")
                
                # 增加详细日志 - 记录所有执行的命令
                if isinstance(result, dict) and 'executed_commands' in result:
                    cmd_count = len(result.get('executed_commands', []))
                    print(f"[DEBUG] ===== 任务 {task_id} 执行了 {cmd_count} 条命令 =====")
                    for i, cmd in enumerate(result.get('executed_commands', [])):
                        print(f"[DEBUG] 命令 {i+1}: {cmd}")
                    print(f"[DEBUG] ============== 命令列表结束 ==============")
                else:
                    print(f"[WARNING] 任务 {task_id} 执行后没有返回任何命令记录!")
                    
                # 更新任务状态为完成或失败
                if isinstance(result, dict) and (result.get('status') == 'error' or 'error' in result):
                    # 处理错误情况
                    error_msg = result.get('error', '未知错误')
                    print(f"[ERROR] 任务 {task_id} 执行失败: {error_msg}")
                    task_repo.update_task_status(
                        task_id,
                        "failed",
                        error=error_msg,
                        by="Web服务"
                    )
                    # 立即通知任务状态变化
                    notify_task_status_change(task_id, "failed")
                    return result
                else:
                    # 处理成功情况
                    # 检查结果中是否包含命令执行的详细信息
                    if isinstance(result, dict) and 'executed_commands' in result:
                        executed = result.get('executed_commands', [])
                        print(f"[INFO] 任务 {task_id} 成功执行了 {len(executed)} 条命令:")
                        for idx, cmd in enumerate(executed[:20]):  # 显示更多命令
                            print(f"  {idx+1}. {cmd}")
                        if len(executed) > 20:
                            print(f"  ... 共 {len(executed)} 条命令")
                    else:
                        print(f"[WARNING] 任务 {task_id} 执行成功，但未返回具体执行的命令")
                    
                    task_repo.update_task_status(
                        task_id,
                        "completed",
                        result=result,
                        by="Web服务"
                    )
                    # 立即通知任务状态变化
                    notify_task_status_change(task_id, "completed")
                
                return result
            
            # 否则查找与参数匹配的任务
            print("[DEBUG] 参数中没有任务ID，尝试在数据库中匹配任务")
            tasks = task_repo.get_all_tasks(limit=20)
            matched_task = None
            
            for task in tasks:
                if task['task_type'] == 'dhcp_config':
                    # 尝试进行更精确的匹配
                    task_params = task['params']
                    if isinstance(params, dict) and isinstance(task_params, dict):
                        # 比较关键字段
                        key_fields = ['pool_name', 'network', 'mask', 'device_ids']
                        matches = all(
                            params.get(key) == task_params.get(key) 
                            for key in key_fields if key in params and key in task_params
                        )
                        if matches:
                            matched_task = task
                            break
                    elif str(task_params) == str(params):
                        matched_task = task
                        break
            
            if matched_task:
                task_id = matched_task['task_id']
                task_status = matched_task['status']
                
                print(f"[INFO] 已找到匹配的任务 {task_id}，状态: {task_status}")
                
                # 只有approved状态的任务才能执行
                if task_status != 'approved':
                    print(f"[WARNING] 匹配任务 {task_id} 状态为 {task_status}，尚未被批准，跳过执行")
                    return {
                        "status": task_status,
                        "message": "任务尚未被批准，请等待审批"
                    }
                
                print(f"[INFO] Web服务开始执行已批准的匹配任务 {task_id}")
                
                # 执行任务前先将状态更新为running
                task_repo.update_task_status(
                    task_id,
                    "running",
                    by="Web服务"
                )
                
                # 立即通知任务状态变化
                notify_task_status_change(task_id, "running")
                
                # 执行任务
                print(f"[INFO] 开始执行任务 {task_id}，参数: {json.dumps(matched_task.get('params', {}), ensure_ascii=False)[:200]}")
                result = task_manager._handle_dhcp_config(task_id, matched_task)
                print(f"[DEBUG] 任务 {task_id} 原始执行结果: {json.dumps(result, ensure_ascii=False)[:500] if result else 'None'}")
                
                # 更新任务状态为完成或失败
                if isinstance(result, dict) and (result.get('status') == 'error' or 'error' in result):
                    # 处理错误情况
                    error_msg = result.get('error', '未知错误')
                    print(f"[ERROR] 任务 {task_id} 执行失败: {error_msg}")
                    task_repo.update_task_status(
                        task_id,
                        "failed",
                        error=error_msg,
                        by="Web服务"
                    )
                    # 立即通知任务状态变化
                    notify_task_status_change(task_id, "failed")
                else:
                    # 处理成功情况
                    # 检查结果中是否包含命令执行的详细信息
                    if isinstance(result, dict) and 'executed_commands' in result:
                        executed = result.get('executed_commands', [])
                        print(f"[INFO] 任务 {task_id} 成功执行了 {len(executed)} 条命令:")
                        for idx, cmd in enumerate(executed[:10]):  # 只显示前10条命令
                            print(f"  {idx+1}. {cmd}")
                        if len(executed) > 10:
                            print(f"  ... 共 {len(executed)} 条命令")
                    else:
                        print(f"[WARNING] 任务 {task_id} 执行成功，但未返回具体执行的命令")
                    
                    task_repo.update_task_status(
                        task_id,
                        "completed",
                        result=result,
                        by="Web服务"
                    )
                    # 立即通知任务状态变化
                    notify_task_status_change(task_id, "completed")
                
                return result
            
            # 如果无法找到匹配的任务，创建详细的错误消息
            print(f"[ERROR] 无法找到匹配参数的DHCP任务: {params}")
            return {
                "status": "error",
                "error": "无法将参数匹配到任务",
                "params": str(params)
            }
            
        except Exception as e:
            print(f"[ERROR] DHCP适配器错误: {str(e)}")
            import traceback
            traceback.print_exc()
            return {"status": "error", "error": str(e)}
    
    # 初始化任务队列（为了保持PyQt事件处理正常）
    db_task_queue = get_db_task_queue()
    
    # 使用适配器函数注册任务处理器
    db_task_queue.register_handler("dhcp_config", dhcp_config_adapter)
    
    # 确保启动状态轮询和任务处理
    print("启动任务管理服务...")
    print("1. 启动任务状态轮询")
    db_task_queue.start_polling()  # 启动轮询线程

    print("2. 启动任务处理")
    db_task_queue.start_processing()  # 启动任务处理线程
    
    # 显示服务启动信息，方便访问网页端
    print("\n" + "="*50)
    print("AutoDevOps系统已启动!")
    print("="*50)
    print(f"Web界面访问地址:")
    print(f"- 本地访问: http://127.0.0.1:{app.config.get('PORT', 5000)}")

    # 尝试获取本机IP以便远程访问
    try:
        import socket
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        print(f"- 网络访问: http://{local_ip}:{app.config.get('PORT', 5000)}")
    except:
        print("- 无法获取本机IP地址")

    print("="*50 + "\n")
    
    print("===== 任务管理服务启动成功 =====")
    print("任务管理服务已启动，将自动处理已批准的任务")
except ImportError as e:
    print(f"警告: 无法导入任务管理器模块: {str(e)}")
    task_manager = None
except Exception as e:
    print(f"警告: 启动任务管理服务时出错: {str(e)}")
    import traceback
    traceback.print_exc()
    task_manager = None

# 设置信号处理器
def signal_handler(sig, frame):
    """处理信号（用于优雅地关闭应用程序）"""
    print("\n收到关闭信号，正在关闭应用...")
    
    # 停止任务管理器
    if 'task_manager' in globals() and task_manager:
        task_manager.stop()
        print("任务管理器已停止")
    
    # 停止WebSocket服务器
    if 'websocket_server' in globals() and websocket_server:
        websocket_server.stop()
        print("WebSocket服务器已停止")
    
    # 停止Flask应用
    sys.exit(0)

# 注册信号处理程序
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# 启动Flask应用
if __name__ == "__main__":
    try:
        print("\n=== 启动Flask应用 ===")
        socketio.run(app, host='0.0.0.0', port=5000, debug=False)  # 添加host参数以允许外部访问
    except Exception as e:
        print(f"启动Flask应用出错: {str(e)}")
        traceback.print_exc()
        
        # 也需要关闭WebSocket服务器
        if 'websocket_server' in globals() and websocket_server:
            websocket_server.stop()
            print("WebSocket服务器已停止")
            
        sys.exit(1) 