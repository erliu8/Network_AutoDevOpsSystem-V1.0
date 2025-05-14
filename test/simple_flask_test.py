#!/usr/bin/env python
# -*- coding: utf-8 -*-

from flask import Flask, render_template
import sys
import os
from pathlib import Path

# 添加项目根目录到系统路径
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

# 创建应用
app = Flask(__name__, 
            template_folder=os.path.join(parent_dir, 'api', 'templates'),
            static_folder=os.path.join(parent_dir, 'api', 'static'))

# 路由
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dhcp')
def dhcp():
    return render_template('dhcp.html', devices=[])

# 错误处理
@app.errorhandler(404)
def page_not_found(e):
    return f"页面未找到: {str(e)}", 404

@app.errorhandler(500)
def server_error(e):
    return f"服务器错误: {str(e)}", 500

# 启动
if __name__ == '__main__':
    print(f"模板目录: {app.template_folder}")
    print(f"静态文件目录: {app.static_folder}")
    app.run(host='0.0.0.0', port=5000, debug=True) 