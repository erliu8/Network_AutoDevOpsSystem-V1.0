#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
from pathlib import Path

# 添加项目根目录到系统路径
sys.path.append(str(Path(__file__).parent))

# 导入app模块
from api.app import create_app, app

if __name__ == "__main__":
    # 创建应用实例
    app = create_app()
    
    # 运行Flask应用
    print("启动Flask应用服务器...")
    app.run(host='0.0.0.0', port=5000, debug=True) 