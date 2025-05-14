#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
WebSocket客户端模块
提供与WebSocket服务器通信的客户端实现
"""

import asyncio
import json
import threading
import time
import traceback
import websockets
from PyQt5.QtCore import QObject, pyqtSignal

# 单例客户端实例
_client_instance = None

class WebSocketClient(QObject):
    """WebSocket客户端类，负责与WebSocket服务器通信"""
    
    # 定义信号
    connected = pyqtSignal()
    disconnected = pyqtSignal()
    reconnected = pyqtSignal()
    message_received = pyqtSignal(dict)
    task_notification = pyqtSignal(dict)
    
    def __init__(self, host='localhost', port=8765):
        """初始化WebSocket客户端
        
        Args:
            host (str): WebSocket服务器主机名或IP地址
            port (int): WebSocket服务器端口
        """
        super().__init__()
        self.host = host
        self.port = port
        self.uri = f"ws://{host}:{port}"
        self.running = False
        self.websocket = None
        self.loop = None
        self.thread = None
        self.client_id = None
        self.client_type = "pyqt-app"
        self.last_reconnect_attempt = 0
        self.reconnect_interval = 5  # 重连间隔（秒）
        self.max_reconnect_attempts = 10  # 最大重连尝试次数
        self.reconnect_attempts = 0
        
    def start(self):
        """启动WebSocket客户端"""
        if self.running:
            print("WebSocket客户端已经在运行")
            return False
        
        # 创建并启动客户端线程
        self.thread = threading.Thread(target=self._run_client, daemon=True)
        self.thread.start()
        print(f"WebSocket客户端正在连接到 {self.uri}")
        return True
    
    def stop(self):
        """停止WebSocket客户端"""
        if not self.running:
            return False
        
        self.running = False
        print("WebSocket客户端已停止")
        return True
    
    def _run_client(self):
        """在线程中运行WebSocket客户端"""
        try:
            # 创建新事件循环
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            
            # 启动客户端
            self.running = True
            self.loop.run_until_complete(self._connect_and_process())
        except Exception as e:
            print(f"WebSocket客户端运行出错: {str(e)}")
            traceback.print_exc()
        finally:
            self.running = False
            if self.loop:
                self.loop.close()
            print("WebSocket客户端线程已退出")
    
    async def _connect_and_process(self):
        """连接到WebSocket服务器并处理消息"""
        while self.running:
            try:
                # 连接到WebSocket服务器
                print(f"正在连接到WebSocket服务器: {self.uri}")
                async with websockets.connect(self.uri) as websocket:
                    self.websocket = websocket
                    print("已连接到WebSocket服务器")
                    
                    # 重置重连计数
                    self.reconnect_attempts = 0
                    
                    # 发出连接信号
                    self.connected.emit()
                    
                    # 注册客户端
                    await self._register_client()
                    
                    # 处理消息
                    while self.running:
                        try:
                            # 等待服务器消息
                            message = await websocket.recv()
                            
                            # 解析消息
                            try:
                                data = json.loads(message)
                                # 发出消息信号
                                self.message_received.emit(data)
                                
                                # 处理特定类型的消息
                                message_type = data.get("type")
                                if message_type == "task_status_change":
                                    # 发出任务通知信号
                                    self.task_notification.emit(data)
                            except json.JSONDecodeError:
                                print(f"收到无效的JSON消息: {message[:50]}...")
                        except websockets.exceptions.ConnectionClosed:
                            print("与WebSocket服务器的连接已关闭")
                            break
            except (websockets.exceptions.WebSocketException, ConnectionRefusedError) as e:
                if isinstance(e, ConnectionRefusedError):
                    error_message = "WebSocket服务器连接被拒绝，服务器可能未启动"
                else:
                    error_message = f"WebSocket连接错误: {str(e)}"
                
                print(error_message)
                
                # 发出断开连接信号
                self.disconnected.emit()
                
                # 增加重连计数
                self.reconnect_attempts += 1
                
                # 检查是否已超过最大重连次数
                if self.max_reconnect_attempts > 0 and self.reconnect_attempts > self.max_reconnect_attempts:
                    print(f"已达到最大重连尝试次数 ({self.max_reconnect_attempts})，停止重连")
                    break
                
                # 等待重连间隔
                await asyncio.sleep(self.reconnect_interval)
            except Exception as e:
                print(f"WebSocket客户端处理消息出错: {str(e)}")
                traceback.print_exc()
                
                # 等待重连间隔
                await asyncio.sleep(self.reconnect_interval)
    
    async def _register_client(self):
        """向服务器注册客户端"""
        if not self.websocket:
            return False
        
        try:
            # 构建注册消息
            register_message = {
                "type": "register_client",
                "client_type": self.client_type,
                "timestamp": time.time()
            }
            
            # 发送注册消息
            await self.websocket.send(json.dumps(register_message))
            print(f"已向服务器注册客户端 (类型: {self.client_type})")
            return True
        except Exception as e:
            print(f"向服务器注册客户端失败: {str(e)}")
            return False
    
    def send_message(self, message_type, data):
        """发送消息到WebSocket服务器
        
        Args:
            message_type (str): 消息类型
            data (dict): 消息数据
            
        Returns:
            bool: 是否成功发送
        """
        if not self.running or not self.websocket or not self.loop:
            print("WebSocket客户端未连接，无法发送消息")
            return False
        
        # 构建消息
        message = {
            "type": message_type,
            **data,
            "timestamp": time.time()
        }
        
        # 在事件循环中发送消息
        async def _send():
            try:
                await self.websocket.send(json.dumps(message))
                return True
            except Exception as e:
                print(f"发送消息失败: {str(e)}")
                return False
        
        try:
            future = asyncio.run_coroutine_threadsafe(_send(), self.loop)
            return future.result(timeout=5)
        except Exception as e:
            print(f"发送消息失败: {str(e)}")
            return False

def get_client():
    """获取WebSocket客户端实例（单例模式）
    
    Returns:
        WebSocketClient: WebSocket客户端实例
    """
    global _client_instance
    if _client_instance is None:
        _client_instance = WebSocketClient()
    return _client_instance 