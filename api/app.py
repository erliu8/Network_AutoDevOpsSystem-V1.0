# app.py
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import sys
import os
import threading
import traceback
from pathlib import Path

# 添加项目根目录到系统路径
sys.path.append(str(Path(__file__).parent.parent))

# 导入任务管理器
try:
    # 修改导入路径指向正确位置
    from tasks.task_manager import TaskManager
    task_manager = None
except ImportError as e:
    print(f"警告: 导入任务管理器时出错: {str(e)}")
    task_manager = None

# 创建Flask应用
app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app)  # 启用CORS

# 导入任务适配器
try:
    from api.task_adapter import get_task_adapter
    task_adapter = get_task_adapter()
    print("已初始化任务适配器")
except ImportError as e:
    print(f"警告: 导入任务适配器时出错: {str(e)}")
    task_adapter = None

# 获取任务适配器实例（供路由模块使用）
def get_flask_task_adapter():
    return task_adapter

# 导入蓝图 - 移到task_adapter导入后，避免循环导入
try:
    from api.routes.devices import devices_bp
    from api.routes.dashboard import dashboard_bp
    from api.routes.tasks import tasks_bp
    from api.routes.dhcp import dhcp_bp
except ImportError as e:
    print(f"警告: 导入蓝图时出错: {str(e)}")

# 全局任务队列（为了兼容性保留）
task_queue = None

# 设置任务队列（为了兼容性保留旧的API）
def set_task_queue(queue_instance):
    global task_queue
    task_queue = queue_instance
    print("已设置全局任务队列")

# 尝试导入WebSocket支持
try:
    from flask_socketio import SocketIO
    socketio = SocketIO(app, cors_allowed_origins="*")
    has_websocket = True
except ImportError:
    print("警告: 未安装Flask-SocketIO，WebSocket功能将不可用")
    # 创建一个模拟的SocketIO对象，以便在没有Flask-SocketIO的情况下也能运行
    class MockSocketIO:
        def __init__(self, app):
            self.app = app
        
        def run(self, host='0.0.0.0', port=5000, debug=False):
            """模拟SocketIO的run方法，实际上调用Flask的run方法"""
            print("使用Flask内置服务器 (没有WebSocket支持)")
            self.app.run(host=host, port=port, debug=debug)
        
        def on(self, *args, **kwargs):
            """模拟on装饰器"""
            def decorator(f):
                return f
            return decorator
    
    socketio = MockSocketIO(app)
    has_websocket = False

# 注册蓝图
try:
    app.register_blueprint(devices_bp, url_prefix='/api/devices')
except NameError:
    print("警告: devices_bp 未定义，跳过注册")

try:
    app.register_blueprint(dashboard_bp, url_prefix='/dashboard')
except NameError:
    print("警告: dashboard_bp 未定义，跳过注册")

try:
    app.register_blueprint(tasks_bp, url_prefix='/api/tasks')
except NameError:
    print("警告: tasks_bp 未定义，跳过注册")

try:
    app.register_blueprint(dhcp_bp, url_prefix='/dhcp')
except NameError:
    print("警告: dhcp_bp 未定义，跳过注册")

# 引入事件处理器（如果启用WebSocket）
if has_websocket:
    try:
        import api.events.dashboard_events
        print("已加载WebSocket事件处理模块")
    except ImportError as e:
        print(f"警告: 加载WebSocket事件处理模块时出错: {str(e)}")

# 主页
@app.route('/')
def index():
    return render_template('index.html')

# 禁用直接路由，避免与正式的DHCP蓝图路由冲突
# @app.route('/dhcp_direct')
# def dhcp_direct():
#     """直接的DHCP配置路由，绕过蓝图"""
#     try:
#         # 使用演示设备数据
#         devices = [
#             {"id": 1, "name": "核心交换机1", "ip": "10.1.1.1", "device_type": "交换机"},
#             {"id": 2, "name": "核心路由器1", "ip": "10.1.1.254", "device_type": "路由器"},
#             {"id": 3, "name": "接入交换机1", "ip": "10.1.2.1", "device_type": "交换机"},
#             {"id": 4, "name": "接入交换机2", "ip": "10.1.2.2", "device_type": "交换机"},
#             {"id": 5, "name": "防火墙1", "ip": "10.1.1.2", "device_type": "防火墙"}
#         ]
        
#         # 返回简单HTML
#         return f"""
#         <!DOCTYPE html>
#         <html>
#         <head>
#             <title>DHCP配置（直接路由）</title>
#             <style>
#                 body {{ font-family: Arial, sans-serif; margin: 20px; }}
#                 ul {{ list-style-type: none; padding: 0; }}
#                 li {{ margin-bottom: 10px; padding: 10px; border: 1px solid #ddd; }}
#             </style>
#         </head>
#         <body>
#             <h1>DHCP配置页面（直接路由）</h1>
#             <p>找到 {len(devices)} 个设备</p>
#             <ul>
#                 {"".join([f"<li>{device['name']} ({device['ip']}) - {device['device_type']}</li>" for device in devices])}
#             </ul>
#             <a href="/">返回首页</a>
#         </body>
#         </html>
#         """
#     except Exception as e:
#         import traceback
#         print(f"直接DHCP路由出错: {str(e)}")
#         traceback.print_exc()
#         return f"直接DHCP路由错误: {str(e)}", 500

# 错误处理
@app.errorhandler(404)
def page_not_found(e):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    """提供更多调试信息的500错误处理"""
    import traceback
    error_trace = traceback.format_exc()
    
    print(f"500错误: {str(e)}\n{error_trace}")
    
    # 直接返回简单HTML，不使用模板（避免模板循环错误）
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>服务器错误</title>
        <style>
            pre {{ white-space: pre-wrap; background: #f5f5f5; padding: 15px; }}
            .error {{ color: red; }}
        </style>
    </head>
    <body>
        <h1>服务器错误</h1>
        <p class="error">{str(e)}</p>
        <h3>错误详情：</h3>
        <pre>{error_trace}</pre>
        <p><a href="/">返回首页</a></p>
    </body>
    </html>
    """, 500

# 启动任务管理服务（作为线程）
def start_task_manager():
    """启动任务管理服务作为后台线程"""
    global task_manager
    
    try:
        if task_manager is None:
            print("正在初始化任务管理器...")
            task_manager = TaskManager(poll_interval=10.0)
        
        # 启动任务管理器
        print("启动任务管理服务...")
        task_manager.start()
        print("任务管理服务已启动")
        
        return True
    except Exception as e:
        print(f"启动任务管理服务失败: {str(e)}")
        traceback.print_exc()
        return False

# 停止任务管理服务
def stop_task_manager():
    """停止任务管理服务"""
    global task_manager
    
    if task_manager and task_manager.running:
        print("正在停止任务管理服务...")
        task_manager.stop()
        print("任务管理服务已停止")

# 启动应用
if __name__ == '__main__':
    # 启动任务管理服务
    success = start_task_manager()
    if success:
        print("任务管理服务启动成功，现在可以在同一进程中处理任务")
    
    # WebSocket服务器已在run_web.py中启动，这里不再重复启动
    # try:
    #     from shared.websocket.server import get_server
    #     websocket_server = get_server()
    #     websocket_server.start()
    #     print("已启动WebSocket服务器")
    # except ImportError:
    #     print("警告: WebSocket服务器模块未找到，跳过启动")
    # except Exception as e:
    #     print(f"启动WebSocket服务器失败: {str(e)}")
    
    try:
        # 使用WebSocket启动（如果可用）
        if has_websocket:
            socketio.run(app, host='0.0.0.0', port=5000, debug=True)
        else:
            app.run(host='0.0.0.0', port=5000, debug=True)
    finally:
        # 在应用关闭时停止任务管理服务
        stop_task_manager()