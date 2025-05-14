#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
from pathlib import Path
import shutil
import subprocess

# 添加项目根目录到系统路径
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

def ensure_directory_exists(directory_path):
    """确保目录存在，如果不存在则创建"""
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)
        print(f"已创建目录: {directory_path}")
    else:
        print(f"目录已存在: {directory_path}")

def check_and_fix_static_files():
    """检查和修复静态文件"""
    # 确保静态文件目录存在
    static_dir = project_root / "api" / "static"
    css_dir = static_dir / "css"
    js_dir = static_dir / "js"
    
    ensure_directory_exists(static_dir)
    ensure_directory_exists(css_dir)
    ensure_directory_exists(js_dir)
    
    # 检查CSS文件
    css_file = css_dir / "style.css"
    if not css_file.exists():
        print(f"CSS文件不存在: {css_file}")
        print("创建基本CSS文件...")
        with open(css_file, 'w', encoding='utf-8') as f:
            f.write("""/* 基础样式 */
body {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    background-color: #f8f9fa;
}

/* 导航栏样式 */
.navbar {
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

/* 侧边栏样式 */
.sidebar {
    position: fixed;
    top: 56px;
    bottom: 0;
    left: 0;
    z-index: 100;
    padding: 48px 0 0;
    box-shadow: inset -1px 0 0 rgba(0, 0, 0, 0.1);
}

.sidebar .nav-link {
    font-weight: 500;
    color: #333;
}

.sidebar .nav-link.active {
    color: #007bff;
}

/* 卡片样式 */
.card {
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    transition: transform 0.3s ease-in-out;
}

.card:hover {
    transform: translateY(-5px);
}

/* 按钮样式 */
.btn {
    border-radius: 3px;
}

/* 页脚样式 */
.footer {
    margin-top: 50px;
    box-shadow: 0 -2px 4px rgba(0, 0, 0, 0.05);
}
""")
        print("CSS文件已创建")
    else:
        print(f"CSS文件已存在: {css_file}")
    
    # 检查JS文件
    js_file = js_dir / "main.js"
    if not js_file.exists():
        print(f"JS文件不存在: {js_file}")
        print("创建基本JS文件...")
        with open(js_file, 'w', encoding='utf-8') as f:
            f.write("""// 文档加载完成后执行
$(document).ready(function() {
    console.log("应用已加载");
    
    // 初始化所有提示工具
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // 初始化所有弹出框
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function(popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
    
    // 初始化数据表格
    if ($.fn.DataTable) {
        $('.datatable').DataTable({
            language: {
                url: "//cdn.datatables.net/plug-ins/1.11.5/i18n/zh.json"
            }
        });
    }
    
    // 侧边栏切换
    $('.sidebar-toggle').on('click', function() {
        $('.sidebar').toggleClass('show');
    });
});
""")
        print("JS文件已创建")
    else:
        print(f"JS文件已存在: {js_file}")

def check_and_fix_template_issues():
    """检查和修复模板问题"""
    templates_dir = project_root / "api" / "templates"
    
    # 检查错误页面目录
    errors_dir = templates_dir / "errors"
    ensure_directory_exists(errors_dir)
    
    # 创建404错误页面
    error_404_file = errors_dir / "404.html"
    if not error_404_file.exists():
        print(f"404错误页面不存在: {error_404_file}")
        print("创建404错误页面...")
        with open(error_404_file, 'w', encoding='utf-8') as f:
            f.write("""{% extends 'base.html' %}

{% block title %}404 - 页面未找到{% endblock %}

{% block content %}
<div class="container mt-5 text-center">
    <div class="row">
        <div class="col-md-8 offset-md-2">
            <h1 class="display-1 text-danger">404</h1>
            <h2 class="mb-4">页面未找到</h2>
            <p class="lead">您请求的页面不存在或已被移动。</p>
            <a href="{{ url_for('index') }}" class="btn btn-primary mt-3">
                <i class="fas fa-home me-2"></i>返回首页
            </a>
        </div>
    </div>
</div>
{% endblock %}""")
        print("404错误页面已创建")
    else:
        print(f"404错误页面已存在: {error_404_file}")
    
    # 创建500错误页面
    error_500_file = errors_dir / "500.html"
    if not error_500_file.exists():
        print(f"500错误页面不存在: {error_500_file}")
        print("创建500错误页面...")
        with open(error_500_file, 'w', encoding='utf-8') as f:
            f.write("""{% extends 'base.html' %}

{% block title %}500 - 服务器错误{% endblock %}

{% block content %}
<div class="container mt-5 text-center">
    <div class="row">
        <div class="col-md-8 offset-md-2">
            <h1 class="display-1 text-danger">500</h1>
            <h2 class="mb-4">服务器内部错误</h2>
            <p class="lead">抱歉，服务器遇到了一个错误。</p>
            <a href="{{ url_for('index') }}" class="btn btn-primary mt-3">
                <i class="fas fa-home me-2"></i>返回首页
            </a>
        </div>
    </div>
</div>
{% endblock %}""")
        print("500错误页面已创建")
    else:
        print(f"500错误页面已存在: {error_500_file}")

def check_dependencies():
    """检查依赖项是否已安装"""
    required_packages = [
        "flask",
        "flask-cors",
        "beautifulsoup4",
        "requests",
    ]
    
    print("检查Python依赖项...")
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
            print(f"✓ {package} 已安装")
        except ImportError:
            print(f"✗ {package} 未安装")
            print(f"  尝试安装 {package}...")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", package])
                print(f"  {package} 安装成功")
            except subprocess.CalledProcessError as e:
                print(f"  {package} 安装失败: {e}")

def main():
    """主函数"""
    print("开始修复Flask应用问题...")
    
    # 检查依赖项
    check_dependencies()
    
    # 检查和修复静态文件
    check_and_fix_static_files()
    
    # 检查和修复模板问题
    check_and_fix_template_issues()
    
    print("\n修复完成。请尝试重新启动Flask应用:")
    print("python run_api.py")

if __name__ == "__main__":
    main()