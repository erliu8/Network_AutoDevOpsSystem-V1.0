#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import time
from PyQt5.QtCore import QCoreApplication
from modules.acl_nat_spanning_tree_configuration.acl_nat_spanning_tree_configuration import ConfigOperator

def test_connection():
    """测试设备连接"""
    print("1. 测试设备连接...")
    # ENSP设备IP地址
    config_op = ConfigOperator("10.1.200.1")
    
    # 连接信号
    config_op.command_output.connect(lambda msg: print(f"输出: {msg}"))
    config_op.config_status.connect(lambda success, msg: print(f"状态: {'成功' if success else '失败'} - {msg}"))
    
    # 测试连接
    result = config_op.test_connection()
    print(f"连接测试结果: {'成功' if result else '失败'}")
    return result, config_op

def test_nat_config_updated(config_op):
    """测试NAT配置 - 更新版本"""
    print("\n2. 测试NAT配置...")
    
    # 测试静态NAT
    print("\n2.1 测试静态NAT...")
    # 直接使用nat static命令，不使用nat enable
    commands = [
        "system-view",
        # 静态NAT配置：内部地址192.168.10.100映射到外部地址192.168.30.100
        "nat static global 192.168.30.100 inside 192.168.10.100",
        "quit"
    ]
    
    output = config_op._execute_commands(commands)
    success = output is not None and "Error" not in output
    print(f"静态NAT配置结果: {'成功' if success else '失败'}")
    
    # 配置NAT地址组
    print("\n2.2 测试NAT地址组...")
    commands = [
        "system-view",
        "nat address-group test-pool",
        "address 192.168.30.100 192.168.30.150",
        "quit",
        "quit"
    ]
    
    output = config_op._execute_commands(commands)
    address_group_success = output is not None and "Error" not in output
    print(f"NAT地址组配置结果: {'成功' if address_group_success else '失败'}")
    
    # 配置动态NAT
    print("\n2.3 测试动态NAT(接口级)...")
    commands = [
        "system-view",
        "interface GigabitEthernet0/0/1",
        "nat outbound 2000",  # 使用ACL 2000进行源NAT
        "quit",
        "quit"
    ]
    
    output = config_op._execute_commands(commands)
    outbound_success = output is not None and "Error" not in output
    print(f"动态NAT配置结果: {'成功' if outbound_success else '失败'}")
    
    # 查看NAT配置
    print("\n2.4 查看NAT配置...")
    commands = [
        "display nat static",
        "display nat address-group"
    ]
    
    success = True
    for cmd in commands:
        output = config_op.connection.send_command(cmd)
        print(f"命令'{cmd}'输出:\n{output}\n")
        if "Error" in output:
            success = False
    
    return success and address_group_success and outbound_success

def test_stp_config_updated(config_op):
    """测试STP配置 - 更新版本"""
    print("\n3. 测试STP配置...")
    
    # 全局STP配置
    print("\n3.1 测试全局STP配置...")
    commands = [
        "system-view",
        "stp mode mstp",
        "stp priority 4096",
        "stp timer forward-delay 15",
        # 不使用stp timer hello和max-age，改用正确的命令格式
        "stp timer root-hello 2", 
        "stp timer max-age 20",
        "stp region-configuration",
        "region-name REGION1",
        "revision-level 1",
        "instance 1 vlan 10 20",
        "active region-configuration",
        "quit",
        "quit"
    ]
    
    output = config_op._execute_commands(commands)
    stp_global_success = output is not None and "Error" not in output
    print(f"全局STP配置结果: {'成功' if stp_global_success else '失败'}")
    
    # 查看STP配置
    print("\n3.2 查看STP状态...")
    commands = [
        "display stp brief",
        "display stp global"
    ]
    
    success = True
    for cmd in commands:
        output = config_op.connection.send_command(cmd)
        print(f"命令'{cmd}'输出:\n{output}\n")
        if "Error" in output:
            success = False
    
    return success and stp_global_success

def main():
    """主函数"""
    app = QCoreApplication(sys.argv)
    
    # 测试设备连接
    connection_result, config_op = test_connection()
    if not connection_result:
        print("设备连接测试失败，终止测试")
        return
    
    # 测试NAT配置(更新版本)
    nat_result = test_nat_config_updated(config_op)
    print(f"\nNAT测试总结: {'成功' if nat_result else '失败'}")
    
    # 测试STP配置(更新版本)
    stp_result = test_stp_config_updated(config_op)
    print(f"\nSTP测试总结: {'成功' if stp_result else '失败'}")
    
    # 总结
    print("\n==== 测试总结 ====")
    print(f"NAT配置测试(更新版): {'通过' if nat_result else '失败'}")
    print(f"STP配置测试(更新版): {'通过' if stp_result else '失败'}")
    print(f"整体测试: {'通过' if (nat_result and stp_result) else '失败'}")
    
    # 给信号处理留时间
    QCoreApplication.processEvents()
    time.sleep(1)

if __name__ == "__main__":
    main() 