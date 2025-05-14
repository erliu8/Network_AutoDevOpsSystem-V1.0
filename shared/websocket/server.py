import asyncio
import json
import websockets
from datetime import datetime
import threading
import logging
import socket
import uuid

# 配置基本的日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('WebSocketServer')

class WebSocketServer:
    def __init__(self, host='0.0.0.0', port=8765):
        self.host = host
        self.port = port
        self.clients = {}  # {client_id: websocket}
        self.data_cache = {
            'device_status': {},
            'online_count': 0,
            'offline_count': 0,
            'device_count': 0,
            'last_update': ''
        }
        self.lock = threading.Lock()
        self.server = None
        self._running = False
        self._event_loop = None
        self._broadcast_count = 0
        # 添加线程本地存储，用于保存当前线程的事件循环
        self._thread_local = threading.local()
        # 消息处理器映射
        self.message_handlers = {}
    
    def register_message_handler(self, message_type, handler_func):
        """注册消息处理器
        
        Args:
            message_type (str): 消息类型
            handler_func (callable): 处理函数，接收两个参数 (client_id, message)
        """
        self.message_handlers[message_type] = handler_func
        print(f"注册了消息处理器: {message_type}")
    
    async def register(self, websocket):
        """注册新的WebSocket客户端连接"""
        client_id = str(uuid.uuid4())
        self.clients[client_id] = websocket
        print(f"WS: 客户端连接 [ID:{client_id}, 总数:{len(self.clients)}]")
        # 立即发送当前缓存数据给新客户端
        await self.send_data_to_client(client_id)
        return client_id
    
    async def unregister(self, client_id):
        """移除WebSocket客户端连接"""
        if client_id in self.clients:
            del self.clients[client_id]
            print(f"WS: 客户端断开 [ID:{client_id}, 总数:{len(self.clients)}]")
    
    async def handle_client(self, websocket, path):
        """处理客户端连接"""
        client_id = await self.register(websocket)
        try:
            async for message in websocket:
                # 处理来自客户端的消息
                try:
                    data = json.loads(message)
                    message_type = data.get("type")
                    
                    # 如果有注册的处理器，调用处理器
                    if message_type and message_type in self.message_handlers:
                        handler = self.message_handlers[message_type]
                        result = handler(client_id, data)
                        print(f"WS: 处理消息 {message_type} 结果: {result}")
                    else:
                        print(f"WS: 收到未处理的消息类型: {message_type}")
                        
                except json.JSONDecodeError:
                    print(f"WS: 无效的JSON消息: {message[:50]}...")
                except Exception as msg_error:
                    print(f"WS: 处理消息时出错: {str(msg_error)}")
        except websockets.ConnectionClosed:
            pass
        except Exception as e:
            print(f"WS: 客户端处理错误: {str(e)[:100]}")
        finally:
            await self.unregister(client_id)
    
    async def send_data_to_client(self, client_id):
        """发送当前缓存数据给指定客户端"""
        try:
            if client_id not in self.clients:
                print(f"WS: 客户端 {client_id} 不存在，无法发送数据")
                return
                
            websocket = self.clients[client_id]
            
            # 获取当前缓存数据的副本
            with self.lock:
                data_copy = self.data_cache.copy()
            
            # 添加时间戳
            data_copy['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # 发送数据
            await websocket.send(json.dumps(data_copy))
            print(f"WS: 已发送数据给客户端 {client_id}")
        except Exception as e:
            print(f"WS: 发送数据错误: {str(e)[:100]}")
    
    async def send_to_client(self, client_id, message):
        """发送消息给指定客户端
        
        Args:
            client_id (str): 客户端ID
            message (str): 要发送的消息（JSON字符串）
        """
        try:
            if client_id not in self.clients:
                print(f"WS: 客户端 {client_id} 不存在，无法发送消息")
                return False
                
            websocket = self.clients[client_id]
            await websocket.send(message)
            return True
        except Exception as e:
            print(f"WS: 发送消息给客户端 {client_id} 失败: {str(e)}")
            return False
    
    def send_to_client_sync(self, client_id, message):
        """同步方式发送消息给指定客户端
        
        Args:
            client_id (str): 客户端ID
            message (str): 要发送的消息（JSON字符串）
            
        Returns:
            bool: 是否成功发送
        """
        if not self._running or not self._event_loop:
            print("WS: 服务器未运行，无法发送消息")
            return False
            
        async def _send():
            return await self.send_to_client(client_id, message)
            
        # 在事件循环中执行发送
        try:
            loop = self.get_event_loop()
            if loop.is_running():
                future = asyncio.run_coroutine_threadsafe(_send(), loop)
                return future.result(timeout=5)
            else:
                print("WS: 事件循环未运行，无法发送消息")
                return False
        except Exception as e:
            print(f"WS: 同步发送消息失败: {str(e)}")
            return False
    
    async def broadcast(self, data):
        """广播数据给所有连接的客户端"""
        if not self.clients:  # 如果没有连接的客户端，直接返回
            print("WS: 没有连接的客户端，跳过广播")
            return
        
        try:
            # 如果是字典，添加时间戳并转换为JSON字符串
            if isinstance(data, dict):
                data['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                message = json.dumps(data)
            else:
                # 假设已经是JSON字符串
                message = data
            
            # 广播消息
            clients_to_remove = []
            send_tasks = []
            
            for client_id, websocket in self.clients.items():
                try:
                    send_tasks.append(asyncio.create_task(websocket.send(message)))
                except websockets.ConnectionClosed:
                    clients_to_remove.append(client_id)
                except Exception as e:
                    print(f"WS: 准备广播时出错 (客户端 {client_id}): {str(e)[:100]}")
                    clients_to_remove.append(client_id)
            
            # 等待所有发送任务完成
            if send_tasks:
                await asyncio.gather(*send_tasks, return_exceptions=True)
            
            # 移除断开连接的客户端
            for client_id in clients_to_remove:
                await self.unregister(client_id)
            
            # 更新广播计数
            self._broadcast_count += 1
            if self._broadcast_count % 10 == 0:  # 每10次广播打印一次日志
                print(f"WS: 已广播数据 [总次数:{self._broadcast_count}, 客户端:{len(self.clients)}]")
        except Exception as e:
            print(f"WS: 广播操作失败: {str(e)[:100]}")
    
    def broadcast_sync(self, data):
        """同步方式广播数据给所有连接的客户端
        
        Args:
            data (dict or str): 要广播的数据（字典或JSON字符串）
            
        Returns:
            bool: 是否成功广播
        """
        if not self._running or not self._event_loop:
            print("WS: 服务器未运行，无法广播")
            return False
            
        async def _broadcast():
            await self.broadcast(data)
            return True
            
        # 在事件循环中执行广播
        try:
            loop = self.get_event_loop()
            if loop.is_running():
                future = asyncio.run_coroutine_threadsafe(_broadcast(), loop)
                return future.result(timeout=5)
            else:
                print("WS: 事件循环未运行，无法广播")
                return False
        except Exception as e:
            print(f"WS: 同步广播失败: {str(e)}")
            return False
    
    def get_event_loop(self):
        """获取当前线程的事件循环，如果不存在则创建一个新的"""
        # 尝试获取线程本地存储的事件循环
        if not hasattr(self._thread_local, 'loop'):
            try:
                # 获取当前线程的事件循环
                loop = asyncio.get_event_loop()
            except RuntimeError:
                # 如果当前线程没有事件循环，创建一个新的
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            self._thread_local.loop = loop
        return self._thread_local.loop
    
    def update_data(self, new_data):
        """更新缓存的数据并广播"""
        # 更新缓存
        with self.lock:
            self.data_cache.update(new_data)
        
        # 在主WebSocket线程的事件循环中广播数据
        if self._event_loop and self._running:
            # 确保使用主WebSocket线程的事件循环
            try:
                # 获取当前事件循环
                loop = self.get_event_loop()
                if loop.is_running():
                    asyncio.run_coroutine_threadsafe(self.broadcast(new_data), loop)
                else:
                    print("WS: 事件循环未运行，创建新的事件循环处理广播")
                    asyncio.run(self.broadcast(new_data))
            except Exception as e:
                print(f"WS: 广播数据时出错: {str(e)}")
    
    async def _cleanup(self):
        """清理资源"""
        # 关闭所有WebSocket连接
        close_tasks = []
        for client_id, websocket in list(self.clients.items()):
            close_tasks.append(asyncio.create_task(websocket.close()))
        
        if close_tasks:
            await asyncio.gather(*close_tasks, return_exceptions=True)
        
        self.clients.clear()
        self._running = False

    def is_port_in_use(self):
        """检查端口是否已在使用中"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind((self.host, self.port))
                return False
            except socket.error:
                return True
    
    async def _start_server(self):
        """启动WebSocket服务器"""
        print(f"WS: 服务器启动于 {self.host}:{self.port}")
        try:
            async with websockets.serve(self.handle_client, self.host, self.port, ping_interval=30, ping_timeout=10):
                self._running = True
                # 保持服务器运行
                while self._running:
                    await asyncio.sleep(1)
        except Exception as e:
            print(f"WS: 服务器运行错误: {str(e)}")
            self._running = False
    
    def start(self):
        """在新线程中启动WebSocket服务器"""
        # 检查服务器是否已在运行
        if self._running:
            print("WS: 服务器已经在运行")
            return
        
        # 检查端口是否已被占用
        if self.is_port_in_use():
            print(f"WS: 端口 {self.port} 已被占用，服务器无法启动")
            return
        
        def run_server():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                self._event_loop = loop
                # 设置线程本地存储的事件循环
                self._thread_local.loop = loop
                loop.run_until_complete(self._start_server())
            except Exception as e:
                print(f"WS: 服务器线程错误: {str(e)}")
                self._running = False
            finally:
                if loop.is_running():
                    loop.close()
        
        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()
        print(f"WS: 服务器线程已启动 (ID: {server_thread.ident})")
    
    def stop(self):
        """停止WebSocket服务器"""
        self._running = False
        print("WS: 服务器已停止")
        # 关闭事件循环
        if self._event_loop and self._event_loop.is_running():
            future = asyncio.run_coroutine_threadsafe(
                self._cleanup(), 
                self._event_loop
            )
            try:
                future.result(timeout=5)  # 等待最多5秒
            except Exception:
                pass

# 单例模式
_server_instance = None

def get_server():
    """获取WebSocket服务器实例"""
    global _server_instance
    if _server_instance is None:
        _server_instance = WebSocketServer()
    return _server_instance
