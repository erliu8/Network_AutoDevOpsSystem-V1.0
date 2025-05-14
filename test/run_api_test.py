#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
from pathlib import Path
import subprocess
import time

# 添加项目根目录到系统路径
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

def main():
    """启动API服务器进行测试"""
    print("启动API服务器测试...")
    
    # 确定Python解释器路径
    python_exec = sys.executable
    print(f"使用Python解释器: {python_exec}")
    
    # 启动Flask服务器
    api_script = os.path.join(parent_dir, "run_api.py")
    print(f"启动API服务器: {api_script}")
    
    try:
        # 使用subprocess启动API服务器
        api_process = subprocess.Popen(
            [python_exec, api_script],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=parent_dir
        )
        
        # 等待服务器启动
        print("等待API服务器启动...")
        time.sleep(3)
        
        # 检查进程是否仍在运行
        if api_process.poll() is not None:
            print("API服务器启动失败!")
            stdout, stderr = api_process.communicate()
            print(f"标准输出: {stdout}")
            print(f"错误输出: {stderr}")
            return
        
        print("API服务器已启动，可以在浏览器中访问 http://localhost:5000 进行测试")
        print("按Ctrl+C停止服务器")
        
        # 等待用户按Ctrl+C
        try:
            while True:
                # 检查子进程是否还在运行
                if api_process.poll() is not None:
                    stdout, stderr = api_process.communicate()
                    print(f"API服务器已停止，退出代码: {api_process.returncode}")
                    print(f"标准输出: {stdout}")
                    print(f"错误输出: {stderr}")
                    break
                time.sleep(1)
        except KeyboardInterrupt:
            print("收到中断信号，正在停止API服务器...")
    
    finally:
        # 确保子进程被终止
        if api_process and api_process.poll() is None:
            api_process.terminate()
            try:
                api_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                api_process.kill()
            print("API服务器已停止")

if __name__ == "__main__":
    main() 