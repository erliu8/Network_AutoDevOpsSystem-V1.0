#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
from pathlib import Path

# 添加项目根目录到系统路径
sys.path.append(str(Path(__file__).parent.parent))

# 导入Flask应用
from api.app import app

if __name__ == "__main__":
    # 设置Flask应用为测试模式
    app.config['TESTING'] = True
    app.config['DEBUG'] = True
    
    # 打印路由信息
    print("应用路由信息:")
    for rule in app.url_map.iter_rules():
        print(f"{rule.endpoint}: {rule.rule} {rule.methods}")
    
    # 获取端口，默认5050（避免与主应用端口冲突）
    port = int(os.environ.get("TEST_PORT", 5050))
    
    # 启动测试应用
    print(f"\n启动测试Flask应用在 http://localhost:{port}")
    print("请在浏览器中访问以验证应用是否正常运行")
    app.run(host="0.0.0.0", port=port) 