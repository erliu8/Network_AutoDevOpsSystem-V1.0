# websocket_service.py
import asyncio
import json
import websockets
import threading
import time
from PyQt5.QtCore import QObject, pyqtSignal

# 导入线程工厂
from core.business.thread_factory import ThreadFactory
# 导入监控服务
from core.business.monitor_service import MonitorService

class WebSocketService(QObject):
    """
    WebSocket服务类
    负责通过WebSocket向Web客户端推送监控数据
    """
    # 定义信号
    client_connected = pyqtSignal(str)  # 客户端连接信号：客户端ID
    client_disconnected = pyqtSignal(str)  # 客户端断开信号：客户端ID
    data_pushed = pyqtSignal(str, str)  # 数据推送信号：客户端ID, 数据类型
    
    def __init__(self, host='0.0.0.0', port=8765):
        super().__init__()
        self.host = host
        self.port = port
        self.clients = set()  # 存储连接的客户端
        self.running = False
        self.server = None
        self.loop = None
        
        # 获取线程工厂实例
        self.thread_factory = ThreadFactory.get_instance()
        
        # 获取监控服务实例
        self.monitor_service = MonitorService()
        
        # 连接监控服务信号
        self.monitor_service.device_status_updated.connect(self.on_device_status_updated)
        self.monitor_service.traffic_data_updated.connect(self.on_traffic_data_updated)
    
    def start(self):
        """启动WebSocket服务器"""
        if self.running:
            print("WebSocket服务已经在运行")
            return False
        
        # 使用线程工厂创建线程运行WebSocket服务器
        self.thread_factory.start_thread(
            target=self._run_server,
            name="WebSocketServer",
            module="core.business.websocket_service"
        )
        
        print(f"WebSocket服务器启动中，监听地址: {self.host}:{self.port}")
        return True
    
    def stop(self):
        """停止WebSocket服务器"""
        if not self.running:
            return False
        
        self.running = False
        
        # 关闭所有客户端连接
        if self.loop and self.clients:
            for client in self.clients:
                asyncio.run_coroutine_threadsafe(client.close(), self.loop)
        
        # 关闭服务器
        if self.server:
            self.server.close()
        
        print("WebSocket服务器已停止")
        return True
    
    def _run_server(self):
        """在线程中运行WebSocket服务器"""
        try:
            # 创建新的事件循环
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            
            # 启动服务器
            self.running = True
            start_server = websockets.serve(self._handle_client, self.host, self.port)
            self.server = self.loop.run_until_complete(start_server)
            
            print(f"WebSocket服务器已启动，监听地址: {self.host}:{self.port}")
            
            # 运行事件循环
            self.loop.run_forever()
        except Exception as e:
            print(f"WebSocket服务器运行出错: {str(e)}")
            import traceback
            print(traceback.format_exc())
        finally:
            self.running = False
            if self.loop:
                self.loop.close()
    
    async def _handle_client(self, websocket, path):
        """处理客户端连接"""
        # 添加到客户端集合
        self.clients.add(websocket)
        client_id = id(websocket)
        print(f"客户端连接: {client_id}, 路径: {path}")
        self.client_connected.emit(str(client_id))
        
        try:
            # 发送初始数据
            await self._send_initial_data(websocket)
            
            # 处理客户端消息
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self._process_client_message(websocket, data)
                except json.JSONDecodeError:
                    print(f"收到无效的JSON消息: {message}")
        except websockets.exceptions.ConnectionClosed:
            print(f"客户端连接关闭: {client_id}")
        finally:
            # 从客户端集合中移除
            self.clients.remove(websocket)
            self.client_disconnected.emit(str(client_id))
    
    async def _send_initial_data(self, websocket):
        """发送初始数据给新连接的客户端"""
        # 获取当前所有设备状态
        devices = self.monitor_service.default_devices
        device_status = {}
        
        for device in devices:
            device_ip = device.get("ip")
            device_status[device_ip] = {
                "name": device.get("name", "未命名"),
                "type": device.get("type", "未知设备"),
                "status": "unknown",
                "last_update": time.time()
            }
        
        # 发送设备状态数据
        await websocket.send(json.dumps({
            "type": "device_status",
            "data": device_status
        }))
    
    async def _process_client_message(self, websocket, data):
        """处理客户端发送的消息"""
        message_type = data.get("type")
        
        if message_type == "start_monitoring":
            # 客户端请求开始监控
            device_ip = data.get("device_ip")
            if device_ip:
                # 启动设备监控
                self.monitor_service.check_device_status(device_ip)
                await websocket.send(json.dumps({
                    "type": "monitoring_started",
                    "device_ip": device_ip
                }))
        
        elif message_type == "start_traffic_monitor":
            # 客户端请求开始流量监控
            device_ip = data.get("device_ip")
            if device_ip:
                # 启动流量监控
                username = data.get("username", "1")
                password = data.get("password", "1")
                self.monitor_service.start_traffic_monitor(device_ip, username, password)
                await websocket.send(json.dumps({
                    "type": "traffic_monitoring_started",
                    "device_ip": device_ip
                }))
    
    def on_device_status_updated(self, ip, status, details):
        """处理设备状态更新信号"""
        if not self.running or not self.clients:
            return
        
        # 准备要发送的数据
        data = {
            "type": "device_status_update",
            "device_ip": ip,
            "status": status,
            "details": details,
            "timestamp": time.time()
        }
        
        # 在事件循环中发送数据
        if self.loop:
            for client in self.clients:
                asyncio.run_coroutine_threadsafe(
                    client.send(json.dumps(data)),
                    self.loop
                )
            
            self.data_pushed.emit(str(len(self.clients)), "device_status")
    
    def on_traffic_data_updated(self, traffic_data):
        """处理流量数据更新信号"""
        if not self.running or not self.clients:
            return
        
        # 准备要发送的数据
        data = {
            "type": "traffic_data_update",
            "data": traffic_data,
            "timestamp": time.time()
        }
        
        # 在事件循环中发送数据
        if self.loop:
            for client in self.clients:
                asyncio.run_coroutine_threadsafe(
                    client.send(json.dumps(data)),
                    self.loop
                )
            
            self.data_pushed.emit(str(len(self.clients)), "traffic_data")
    
    def broadcast_message(self, message_type, data):
        """广播消息给所有连接的客户端"""
        if not self.running or not self.clients:
            return
        
        # 准备要发送的数据
        message = {
            "type": message_type,
            "data": data,
            "timestamp": time.time()
        }
        
        # 在事件循环中发送数据
        if self.loop:
            for client in self.clients:
                asyncio.run_coroutine_threadsafe(
                    client.send(json.dumps(message)),
                    self.loop
                )
            
            self.data_pushed.emit(str(len(self.clients)), message_type)