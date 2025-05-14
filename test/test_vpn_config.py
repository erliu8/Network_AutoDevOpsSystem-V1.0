#!/usr/bin/env python
# test_vpn_config.py - 测试VPN配置模块

import sys
import os
import time
from PyQt5.QtWidgets import QApplication
from modules.vpn_deploy.gui import VPNConfigApp

def main():
    print("============================================")
    print("          VPN配置模块测试程序")
    print("============================================")
    print("启动界面...")
    print("注意: 由于测试环境无法连接到真实网络设备，")
    print("     因此配置操作为模拟过程，将在短暂延迟后")
    print("     显示成功提示。")
    print("============================================")
    
    # 创建QApplication实例
    app = QApplication(sys.argv)
    
    # 创建VPN配置窗口
    window = VPNConfigApp()
    
    # 预填测试数据（可选）
    window.vpn_name_input.setText("TestVPN")
    window.vlan_input.setText("100")
    window.rt_input.setText("100:1")
    window.rd_input.setText("200:1")
    window.ip_input.setText("192.168.10.1")
    window.mask_input.setText("255.255.255.0")
    
    print("测试界面已准备就绪，请点击\"提交配置\"按钮测试配置流程")
    
    # 显示窗口
    window.show()
    
    # 执行应用程序主循环
    sys.exit(app.exec_())

if __name__ == "__main__":
    main() 