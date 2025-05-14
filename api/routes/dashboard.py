#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Blueprint, render_template, jsonify
from core.services.device_service import DeviceService
from datetime import datetime, timedelta

# 创建蓝图
dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/', methods=['GET'])
def index():
    """仪表盘主页"""
    
    # 获取设备数据
    devices = DeviceService.get_all_devices()
    
    # 统计在线和离线设备
    device_count = len(devices)
    online_count = 0
    offline_count = 0
    
    # 准备给模板的数据
    context = {
        'device_count': device_count,
        'online_count': online_count,
        'offline_count': offline_count,
        'device_status': {},
        'recent_logs': []  # 最近任务日志
    }
    
    # 设置WebSocket支持状态
    try:
        from shared.websocket.handlers import DashboardDataHandler
        context['websocket_enabled'] = True
    except ImportError:
        context['websocket_enabled'] = False
    
    return render_template('dashboard.html', **context)

@dashboard_bp.route('/api/status', methods=['GET'])
def device_status():
    """获取设备状态API接口"""
    
    # 获取设备数据
    devices = DeviceService.get_all_devices()
    
    # 统计在线和离线设备
    device_count = len(devices)
    online_count = 0
    offline_count = device_count
    
    # 构建响应数据
    response = {
        'device_count': device_count,
        'online_count': online_count,
        'offline_count': offline_count,
        'devices': [],
        'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    return jsonify(response)
