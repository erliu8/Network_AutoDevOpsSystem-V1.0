# events/__init__.py
"""
WebSocket事件处理模块
处理实时数据推送和事件通知
"""

# 导入所有事件处理器
try:
    from api.events.dashboard_events import *
except ImportError:
    print("警告: dashboard_events 模块未找到")

try:
    from api.events.monitor_events import *
except ImportError:
    print("警告: monitor_events 模块未找到")

try:
    from api.events.task_events import *
except ImportError:
    print("警告: task_events 模块未找到") 