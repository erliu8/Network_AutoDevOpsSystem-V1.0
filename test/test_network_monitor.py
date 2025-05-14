#!/usr/bin/env python
# test_network_monitor.py - 网络监控测试脚本

import sys
import os
import time
from PyQt5.QtWidgets import QApplication
from modules.network_monitor.gui import AutoMaintainGUI

def main():
    print("============================================")
    print("          网络监控模块测试程序")
    print("============================================")
    print("启动界面...")
    print("该测试将展示网络监控功能，包括:")
    print("- 设备状态监控")
    print("- 设备性能数据采集（CPU和内存使用率）")
    print("- 接口状态监控")
    print("- 故障设备自动修复")
    print("============================================")
    
    # 创建QApplication实例
    app = QApplication(sys.argv)
    
    # 创建网络监控窗口
    window = AutoMaintainGUI()
    
    # 显示窗口
    window.show()
    
    # 打印提示
    print("测试界面已准备就绪。")
    print("请依次测试以下功能:")
    print("1. 点击\"刷新状态\"按钮获取所有设备状态")
    print("2. 查看设备CPU和内存使用情况")
    print("3. 点击设备查看详细信息")
    print("4. 双击设备查看接口状态")
    print("5. 测试故障设备修复功能")
    print("6. 测试自动刷新设置")
    
    # 执行应用程序主循环
    sys.exit(app.exec_())

if __name__ == "__main__":
    main() 