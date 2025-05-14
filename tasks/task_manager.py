#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
任务管理器类
负责轮询数据库中的任务并执行它们
"""

import threading
import time
import traceback
import sys
import os
from pathlib import Path
import json

# 添加项目根目录到系统路径
sys.path.append(str(Path(__file__).parent.parent))

# 导入数据库任务仓库
from shared.db.task_repository import get_task_repository
from shared.db.device_repository import get_device_repository

class TaskManager:
    """任务管理器类，负责轮询数据库中的任务并执行它们"""
    
    def __init__(self, poll_interval=5.0):
        """
        初始化任务管理器
        
        Args:
            poll_interval (float): 轮询间隔，单位为秒
        """
        self.poll_interval = poll_interval
        self.running = False
        self.thread = None
        self.task_repository = get_task_repository()
        self.handlers = {}
        
        # 注册默认任务处理器
        self._register_default_handlers()
    
    def _register_default_handlers(self):
        """注册默认任务处理器"""
        # DHCP配置任务处理器
        self.register_handler("dhcp_config", self._handle_dhcp_config)
    
    def register_handler(self, task_type, handler_func):
        """
        注册任务处理器
        
        Args:
            task_type (str): 任务类型
            handler_func (callable): 处理函数，接受task_id和task_data作为参数
        """
        self.handlers[task_type] = handler_func
    
    def start(self):
        """启动任务管理器线程"""
        if self.running:
            print("任务管理器已经在运行中")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        print(f"任务管理器启动成功，轮询间隔: {self.poll_interval}秒")
    
    def stop(self):
        """停止任务管理器线程"""
        if not self.running:
            print("任务管理器已经停止")
            return
        
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)
        print("任务管理器已停止")
    
    def _run(self):
        """任务管理器主循环"""
        print("任务管理器线程启动")
        
        while self.running:
            try:
                # 处理待执行任务
                self._process_approved_tasks()
                
                # 等待下一次轮询
                for _ in range(int(self.poll_interval * 2)):
                    if not self.running:
                        break
                    time.sleep(0.5)
                
            except Exception as e:
                print(f"任务管理器出错: {str(e)}")
                traceback.print_exc()
                # 短暂暂停后继续
                time.sleep(1.0)
        
        print("任务管理器线程退出")
    
    def _process_approved_tasks(self):
        """处理已审核的任务"""
        try:
            # 获取已审核的任务
            tasks = self.task_repository.get_tasks_by_status("approved")
            
            if not tasks:
                return
            
            print(f"找到 {len(tasks)} 个已审核待执行任务")
            
            for task in tasks:
                task_id = task.get("task_id")
                task_type = task.get("task_type")
                
                try:
                    print(f"开始处理任务 {task_id} (类型: {task_type})")
                    
                    # 获取任务处理器
                    handler = self.handlers.get(task_type)
                    if not handler:
                        error_msg = f"未找到处理器: {task_type}"
                        print(f"[ERROR] {error_msg}")
                        
                        # 更新任务状态为失败
                        self.task_repository.update_task_status(
                            task_id, "failed", error=error_msg, by="TaskManager"
                        )
                        continue
                    
                    # 更新任务状态为进行中
                    print(f"[INFO] 更新任务 {task_id} 状态为 running")
                    update_result = self.task_repository.update_task_status(
                        task_id, "running", by="TaskManager"
                    )
                    
                    if not update_result:
                        print(f"[WARNING] 更新任务 {task_id} 状态失败，可能已被其他进程处理")
                        continue
                    
                    # 添加WebSocket通知
                    try:
                        from shared.websocket.handlers import broadcast_task_notification
                        broadcast_task_notification(task_id, "running", {"message": "开始执行任务"})
                        print(f"[INFO] 已通过WebSocket广播任务 {task_id} 的状态变更为 running")
                    except Exception as ws_error:
                        print(f"[WARNING] WebSocket通知失败: {str(ws_error)}")
                    
                    # 处理任务
                    try:
                        print(f"[INFO] 执行任务 {task_id} 处理器")
                        result = handler(task_id, task)
                        
                        # 更新任务状态为已完成
                        self.task_repository.update_task_status(
                            task_id, "completed", result=result, by="TaskManager"
                        )
                        
                        print(f"[INFO] 任务 {task_id} 处理成功")
                        
                        # 通过WebSocket广播状态变更
                        try:
                            broadcast_task_notification(task_id, "completed", {"message": "任务执行完成"})
                        except Exception as ws_error:
                            print(f"[WARNING] WebSocket通知任务完成失败: {str(ws_error)}")
                            
                    except Exception as handler_error:
                        # 更新任务状态为失败
                        error_msg = f"任务执行失败: {str(handler_error)}"
                        print(f"[ERROR] {error_msg}")
                        traceback.print_exc()
                        
                        self.task_repository.update_task_status(
                            task_id, "failed", error=error_msg, by="TaskManager"
                        )
                        
                        # 通过WebSocket广播状态变更
                        try:
                            broadcast_task_notification(task_id, "failed", {"message": error_msg})
                        except Exception as ws_error:
                            print(f"[WARNING] WebSocket通知任务失败状态变更失败: {str(ws_error)}")
                    
                except Exception as task_error:
                    # 捕获处理单个任务的所有异常
                    error_msg = f"处理任务时出错: {str(task_error)}"
                    print(f"[ERROR] {error_msg}")
                    traceback.print_exc()
                    
                    # 尝试更新任务状态
                    try:
                        self.task_repository.update_task_status(
                            task_id, "failed", error=error_msg, by="TaskManager"
                        )
                    except Exception as update_error:
                        print(f"[ERROR] 更新任务状态失败: {str(update_error)}")
        
        except Exception as e:
            # 捕获整个处理过程的异常
            print(f"[ERROR] 处理审批任务时出现严重错误: {str(e)}")
            traceback.print_exc()
    
    def _handle_dhcp_config(self, task_id, task_data):
        """
        处理DHCP配置任务
        
        Args:
            task_id (str): 任务ID
            task_data (dict): 任务数据
            
        Returns:
            dict: 任务结果
        """
        from shared.websocket.handlers import broadcast_task_notification
        
        print(f"处理DHCP配置任务: {task_id}")
        print(f"任务数据: {json.dumps(task_data, ensure_ascii=False)}")
        
        # 获取任务参数
        params = task_data.get("params", {})
        
        # 记录任务详情
        print(f"DHCP配置: {params.get('pool_name')} - 网络: {params.get('network')}/{params.get('mask')}")
        
        try:
            # 获取设备ID列表，确保正确格式
            device_ids = params.get("device_ids", [])
            
            # 确保device_ids是列表
            if isinstance(device_ids, str):
                # 如果是逗号分隔的字符串，拆分为列表
                if ',' in device_ids:
                    device_ids = [id.strip() for id in device_ids.split(',')]
                else:
                    device_ids = [device_ids]
            
            # 通知任务状态更改
            broadcast_task_notification(task_id, "running", {"message": "开始执行DHCP配置"})
            
            if not device_ids:
                return {
                    "status": "error",
                    "message": "没有指定设备"
                }
                
            print(f"将在设备上执行DHCP配置: {device_ids}")
            
            # 从设备仓库获取设备信息
            device_repo = get_device_repository()
            
            # 准备DHCP配置器
            from modules.dhcp_configuration.dhcp_configuration import DHCPConfigurator
            
            # 记录结果
            results = {}
            successful_devices = []
            failed_devices = []
            executed_commands = []
            
            # 处理每个设备
            for device_id in device_ids:
                try:
                    # 获取设备信息
                    device = device_repo.get_device_by_id(device_id)
                    if not device:
                        error_msg = f"找不到设备: {device_id}"
                        print(f"错误: {error_msg}")
                        failed_devices.append({"id": device_id, "error": error_msg})
                        continue
                    
                    # 获取设备连接信息
                    device_ip = device.get("ip")
                    device_username = device.get("username", "")
                    device_password = device.get("password", "")
                    device_type = device.get("type", "")
                    
                    # 确定适当的连接类型
                    connect_type = None
                    
                    # 基于设备类型确定连接类型
                    if "huawei" in device_type.lower():
                        # 首选Telnet连接方式
                        connect_type = "huawei_telnet"
                    elif "cisco" in device_type.lower():
                        connect_type = "cisco_ios_telnet"
                    else:
                        # 默认使用华为Telnet
                        connect_type = "huawei_telnet"
                    
                    print(f"设备 {device_id} ({device_ip}) 使用连接类型: {connect_type}")
                    
                    # 创建DHCP配置器
                    dhcp_config = DHCPConfigurator(
                        connect_type, 
                        device_ip,
                        device_username, 
                        device_password
                    )
                    
                    # 从参数中获取配置信息
                    pool_name = params.get("pool_name", "")
                    network = params.get("network", "")
                    mask = params.get("mask", "")
                    dns = params.get("dns")
                    gateway = params.get("gateway")
                    excluded = params.get("excluded")
                    
                    # 确保网络地址格式正确
                    network_with_mask = f"{network} {mask}"
                    
                    # 调整DNS服务器格式
                    if dns and isinstance(dns, list):
                        dns = dns[0]  # 使用第一个DNS服务器
                        
                    print(f"DHCP配置参数: 池名称={pool_name}, 网络={network_with_mask}, 网关={gateway}, DNS={dns}")
                    
                    # 执行配置
                    start_time = time.time()
                    debug_mode = params.get("debug", False)
                    
                    # 调用实际的DHCP配置器
                    config_result = dhcp_config.configure_dhcp(
                        pool_name=pool_name,
                        network=network_with_mask,
                        excluded=excluded,
                        dns=dns,
                        gateway=gateway,
                        debug=debug_mode
                    )
                    
                    # 保存执行的命令
                    device_commands = dhcp_config.last_commands
                    executed_commands.extend([f"设备 {device_ip}: {cmd}" for cmd in device_commands])
                    
                    # 记录结果
                    duration = time.time() - start_time
                    result_status = "成功" if config_result else "失败"
                    print(f"设备 {device_id} ({device_ip}) DHCP配置{result_status}，耗时: {duration:.2f}秒")
                    
                    if config_result:
                        successful_devices.append(device_id)
                        results[device_id] = {
                            "status": "success",
                            "message": f"DHCP配置成功 ({device_ip})",
                            "commands": device_commands,
                            "duration": f"{duration:.2f}秒"
                        }
                    else:
                        failed_devices.append({"id": device_id, "error": "配置失败"})
                        results[device_id] = {
                            "status": "error",
                            "message": f"DHCP配置失败 ({device_ip})",
                            "commands": device_commands,
                            "duration": f"{duration:.2f}秒"
                        }
                    
                except Exception as e:
                    error_msg = f"配置设备 {device_id} 时出错: {str(e)}"
                    print(f"错误: {error_msg}")
                    traceback.print_exc()
                    failed_devices.append({"id": device_id, "error": str(e)})
                    results[device_id] = {
                        "status": "error",
                        "message": error_msg
                    }
            
            # 发送完成通知
            if not failed_devices:
                broadcast_task_notification(task_id, "success", {
                    "message": f"DHCP配置完成，成功配置 {len(successful_devices)} 台设备", 
                    "commands": executed_commands
                })
                return {
                    "status": "success",
                    "message": f"DHCP配置完成，成功配置 {len(successful_devices)} 台设备",
                    "device_results": results,
                    "commands": executed_commands
                }
            elif not successful_devices:
                broadcast_task_notification(task_id, "error", {
                    "message": f"DHCP配置失败，所有 {len(failed_devices)} 台设备配置失败", 
                    "failures": failed_devices,
                    "commands": executed_commands
                })
                return {
                    "status": "error",
                    "message": f"DHCP配置失败，所有 {len(failed_devices)} 台设备配置失败",
                    "failures": failed_devices,
                    "device_results": results,
                    "commands": executed_commands
                }
            else:
                broadcast_task_notification(task_id, "warning", {
                    "message": f"DHCP配置部分完成，{len(successful_devices)} 成功，{len(failed_devices)} 失败",
                    "failures": failed_devices,
                    "commands": executed_commands
                })
                return {
                    "status": "warning",
                    "message": f"DHCP配置部分完成，{len(successful_devices)} 成功，{len(failed_devices)} 失败",
                    "failures": failed_devices,
                    "device_results": results,
                    "commands": executed_commands
                }
                
        except Exception as e:
            error_message = f"处理DHCP配置任务失败: {str(e)}"
            print(f"错误: {error_message}")
            traceback.print_exc()
            broadcast_task_notification(task_id, "error", {"message": error_message})
            return {
                "status": "error",
                "message": error_message
            }
