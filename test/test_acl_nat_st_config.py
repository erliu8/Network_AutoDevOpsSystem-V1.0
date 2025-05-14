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
    return result

def test_acl_config():
    """测试ACL配置"""
    print("\n2. 测试ACL配置...")
    config_op = ConfigOperator("10.1.200.1")
    
    # 连接信号
    config_op.command_output.connect(lambda msg: print(f"输出: {msg}"))
    config_op.config_status.connect(lambda success, msg: print(f"状态: {'成功' if success else '失败'} - {msg}"))
    
    # 添加基本ACL规则
    print("\n2.1 添加基本ACL规则...")
    basic_result = config_op.add_acl_rule(
        acl_number=2000,
        rule_number=5,
        action="permit",
        source="192.168.10.0 0.0.0.255"
    )
    print(f"基本ACL规则添加结果: {'成功' if basic_result else '失败'}")
    
    # 添加高级ACL规则
    print("\n2.2 添加高级ACL规则...")
    advanced_result = config_op.add_acl_rule(
        acl_number=3000,
        rule_number=10,
        action="deny",
        protocol="ip",
        source="192.168.10.0 0.0.0.255",
        dest="192.168.20.0 0.0.0.255",
        port="destination-port eq 80"
    )
    print(f"高级ACL规则添加结果: {'成功' if advanced_result else '失败'}")
    
    # 获取ACL配置
    print("\n2.3 获取ACL配置...")
    acl_config = config_op.get_acl_config()
    
    # 应用ACL到接口
    print("\n2.4 应用ACL到接口...")
    apply_result = config_op.apply_acl_to_interface(
        acl_number=2000,
        interface="GigabitEthernet0/0/1",
        direction="inbound"
    )
    print(f"应用ACL到接口结果: {'成功' if apply_result else '失败'}")
    
    return basic_result and advanced_result and (acl_config is not None) and apply_result

def main():
    """主函数"""
    app = QCoreApplication(sys.argv)
    
    # 测试设备连接
    connection_result = test_connection()
    if not connection_result:
        print("设备连接测试失败，终止测试")
        return
    
    # 测试ACL配置
    acl_result = test_acl_config()
    print(f"\nACL测试总结: {'成功' if acl_result else '失败'}")
    
    # 总结
    print("\n==== 测试总结 ====")
    print(f"ACL配置测试: {'通过' if acl_result else '失败'}")
    print(f"整体测试: {'通过' if acl_result else '失败'}")
    
    # 给信号处理留时间
    QCoreApplication.processEvents()
    time.sleep(1)

if __name__ == "__main__":
    main() 