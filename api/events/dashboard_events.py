# dashboard_events.py
"""
处理仪表盘相关的WebSocket事件
"""

from flask_socketio import emit
from api.app import socketio

@socketio.on('connect')
def handle_connect():
    """处理客户端连接事件"""
    print("Client connected")
    # 发送初始数据
    emit('connection_status', {'status': 'connected', 'message': '连接成功'})

@socketio.on('disconnect')
def handle_disconnect():
    """处理客户端断开连接事件"""
    print("Client disconnected")

@socketio.on('request_device_status')
def handle_request_device_status():
    """处理请求设备状态的事件"""
    try:
        # 这里应该从监控服务获取最新的设备状态数据
        # 由于没有实际的数据源，这里模拟一些数据
        device_status_data = {
            'type': 'device_status',
            'summary': {
                'online': 3,
                'offline': 1,
                'unknown': 2,
                'total': 6
            },
            'devices': [
                {'id': 1, 'name': '路由器1', 'ip_address': '192.168.1.1', 'status': 'online', 'last_checked': '2023-07-30 10:30:00'},
                {'id': 2, 'name': '交换机1', 'ip_address': '192.168.1.2', 'status': 'online', 'last_checked': '2023-07-30 10:30:00'},
                {'id': 3, 'name': '交换机2', 'ip_address': '192.168.1.3', 'status': 'offline', 'last_checked': '2023-07-30 10:30:00'},
                {'id': 4, 'name': '防火墙', 'ip_address': '192.168.1.4', 'status': 'online', 'last_checked': '2023-07-30 10:30:00'},
                {'id': 5, 'name': '接入点1', 'ip_address': '192.168.1.5', 'status': 'unknown', 'last_checked': '2023-07-30 10:30:00'},
                {'id': 6, 'name': '接入点2', 'ip_address': '192.168.1.6', 'status': 'unknown', 'last_checked': '2023-07-30 10:30:00'}
            ]
        }
        emit('device_status_update', device_status_data)
    except Exception as e:
        print(f"处理设备状态请求时出错: {str(e)}")
        emit('error', {'message': f'获取设备状态失败: {str(e)}'})

@socketio.on('request_traffic_data')
def handle_request_traffic_data():
    """处理请求流量数据的事件"""
    try:
        # 模拟流量数据
        traffic_data = {
            'type': 'traffic_data',
            'timestamp': '2023-07-30 10:45:00',
            'data': {
                'inbound': [10, 15, 20, 25, 30, 28, 25, 20, 15, 10],
                'outbound': [5, 10, 15, 20, 25, 23, 20, 15, 10, 5]
            },
            'labels': ['10:35', '10:36', '10:37', '10:38', '10:39', '10:40', '10:41', '10:42', '10:43', '10:44']
        }
        emit('traffic_data_update', traffic_data)
    except Exception as e:
        print(f"处理流量数据请求时出错: {str(e)}")
        emit('error', {'message': f'获取流量数据失败: {str(e)}'})

# 计划任务：定期推送设备状态更新
def broadcast_device_status():
    """广播设备状态更新"""
    # 模拟设备状态数据
    device_status_data = {
        'type': 'device_status',
        'summary': {
            'online': 4,
            'offline': 1,
            'unknown': 1,
            'total': 6
        },
        'timestamp': '2023-07-30 10:50:00'
    }
    socketio.emit('device_status_update', device_status_data)

# 注册计划任务（如果需要）
try:
    from flask_apscheduler import APScheduler
    
    # 创建调度器
    scheduler = APScheduler()
    
    # 添加任务
    @scheduler.task('interval', id='broadcast_device_status', seconds=30)
    def schedule_broadcast_device_status():
        broadcast_device_status()
    
    # 注意：调度器应在主应用中初始化和启动
except ImportError:
    print("警告: flask_apscheduler 未安装，定时任务将不可用") 