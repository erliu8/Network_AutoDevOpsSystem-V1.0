#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import webbrowser
import time
import sys
import os
import subprocess

def test_flask_app():
    """测试Flask应用是否正常运行"""
    url = "http://localhost:5000/dashboard"
    
    print(f"正在测试Flask应用，尝试访问: {url}")
    
    try:
        # 尝试发送请求
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            print(f"成功! 状态码: {response.status_code}")
            print("仪表板页面访问正常")
            
            # 检查WebSocket支持
            if "WebSocket: 正在连接" in response.text:
                print("WebSocket支持已正确配置在页面中")
            else:
                print("警告: 未在页面中找到WebSocket连接代码")
            
            # 检查设备状态表格
            if "设备状态" in response.text and "device-status-table" in response.text:
                print("设备状态表格已正确配置")
            else:
                print("警告: 未找到设备状态表格")
            
            return True
        else:
            print(f"错误! 状态码: {response.status_code}")
            return False
    
    except requests.exceptions.ConnectionError:
        print("错误: 无法连接到Flask应用服务器，请确保它正在运行")
        return False
    except requests.exceptions.Timeout:
        print("错误: 请求超时")
        return False
    except Exception as e:
        print(f"错误: {e}")
        return False

def open_dashboard_in_browser():
    """在浏览器中打开仪表板页面"""
    url = "http://localhost:5000/dashboard"
    print(f"正在浏览器中打开仪表板: {url}")
    webbrowser.open(url)

def launch_websocket_client():
    """启动WebSocket测试客户端"""
    try:
        # 检查websocket_test_client.py是否存在
        if not os.path.exists("websocket_test_client.py"):
            # 如果不存在，打印错误信息
            print("错误: websocket_test_client.py不存在")
            return
        
        # 在新进程中启动WebSocket测试客户端
        print("正在启动WebSocket测试客户端...")
        process = subprocess.Popen([sys.executable, "websocket_test_client.py"])
        
        print("WebSocket测试客户端已启动")
        
        # 让客户端运行一段时间
        time.sleep(10)
        
        # 终止客户端进程
        print("正在停止WebSocket测试客户端...")
        process.terminate()
        
    except Exception as e:
        print(f"启动WebSocket测试客户端时出错: {e}")

if __name__ == "__main__":
    # 首先测试Flask应用
    if test_flask_app():
        # 如果Flask应用正常运行，打开浏览器
        open_dashboard_in_browser()
        
        # 等待用户查看仪表板
        print("\n请检查浏览器中的仪表板页面...")
        print("设备状态是否实时更新?")
        print("WebSocket连接状态是否显示为已连接?")
        
        # 启动WebSocket测试客户端
        launch_websocket_client()
        
    else:
        print("测试失败，请检查Flask应用是否正在运行") 