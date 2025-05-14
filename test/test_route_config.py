#!/usr/bin/env python
# test_route_config.py - 测试路由配置模块

import sys
import os
import time
from PyQt5.QtWidgets import QApplication
from modules.route_configuration.gui import RouteConfigWindow

def main():
    print("============================================")
    print("          路由配置模块测试程序")
    print("============================================")
    print("启动界面...")
    print("该测试将展示路由配置功能，包括:")
    print("- 静态路由配置")
    print("- RIP路由配置")
    print("- OSPF路由配置")
    print("- BGP路由配置")
    print("- VPN实例配置")
    print("============================================")
    
    # 创建QApplication实例
    app = QApplication(sys.argv)
    
    # 创建路由配置窗口
    window = RouteConfigWindow()
    
    # 显示窗口
    window.show()
    
    # 打印提示
    print("测试界面已准备就绪。")
    print("请依次测试以下功能:")
    print("1. 选择一台路由器设备并点击\"连接测试\"")
    print("2. 在\"静态路由\"选项卡中配置一条静态路由")
    print("3. 在\"RIP\"选项卡中配置RIP路由协议")
    print("4. 在\"OSPF\"选项卡中配置OSPF路由协议")
    print("5. 在\"BGP\"选项卡中配置BGP路由协议（仅用于出口路由器）")
    print("6. 在\"VPN实例\"选项卡中配置VPN实例")
    
    # 执行应用程序主循环
    sys.exit(app.exec_())

if __name__ == "__main__":
    main() 