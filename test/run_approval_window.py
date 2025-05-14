#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
from pathlib import Path
import requests
import json
import time
from PyQt5.QtWidgets import QApplication, QMessageBox

# 添加项目根目录到系统路径
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

def check_api_server():
    """检查API服务器是否运行"""
    try:
        response = requests.get("http://localhost:5000/", timeout=3)
        return response.status_code == 200
    except:
        return False

def submit_dhcp_request():
    """提交DHCP配置请求"""
    dhcp_data = {
        'device_ids': ['1', '2'],
        'pool_name': 'TEST_POOL',
        'network': '192.168.1.0',
        'mask': '255.255.255.0',
        'gateway': '192.168.1.1',
        'dns': '8.8.8.8',
        'lease_days': 3
    }
    
    try:
        response = requests.post(
            "http://localhost:5000/dhcp/submit",
            json=dhcp_data,
            headers={'Content-Type': 'application/json'},
            timeout=5
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"DHCP配置请求已提交，任务ID: {result.get('task_id')}")
            print(f"状态: {result.get('status')}")
            print(f"消息: {result.get('message')}")
            return result.get('task_id')
        else:
            print(f"提交DHCP配置请求失败，状态码: {response.status_code}")
            print(f"错误: {response.text}")
            return None
    except Exception as e:
        print(f"提交请求时出错: {str(e)}")
        return None

def main():
    """启动审批窗口"""
    print("启动任务审批窗口...")
    
    # 检查API服务器是否运行
    if not check_api_server():
        print("错误: API服务器未运行，请先启动API服务器")
        print("提示: 运行 python test/run_api_test.py")
        return
    
    # 提交DHCP配置请求
    print("提交DHCP配置请求...")
    task_id = submit_dhcp_request()
    
    if not task_id:
        print("错误: 无法提交DHCP配置请求")
        return
    
    # 启动PyQt应用
    app = QApplication(sys.argv)
    
    # 创建审批窗口
    from modules.final_approval.gui import ApprovalWindow
    approval_window = ApprovalWindow()
    
    # 显示窗口
    approval_window.show()
    
    # 显示提示消息
    QMessageBox.information(
        None,
        "测试说明",
        f"请在审批窗口中找到并批准任务ID为 {task_id} 的DHCP配置任务。\n\n"
        "批准后，系统将尝试执行DHCP配置。\n\n"
        "请注意: 由于测试环境没有实际设备，审批后的任务可能会执行失败，这是正常的。"
    )
    
    # 启动应用主循环
    sys.exit(app.exec_())

if __name__ == "__main__":
    main() 