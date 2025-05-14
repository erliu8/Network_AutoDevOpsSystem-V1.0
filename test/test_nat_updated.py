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

def test_nat_static(config_op):
    """测试静态NAT配置"""
    print("\n2. 测试静态NAT配置...")
    
    result = config_op.configure_nat(
        nat_type="static",
        nat_params={
            "inside_ip": "192.168.10.100",
            "outside_ip": "192.168.30.100"
        }
    )
    
    print(f"静态NAT配置结果: {'成功' if result else '失败'}")
    return result

def test_nat_outbound(config_op):
    """测试出接口NAT配置"""
    print("\n3. 测试出接口NAT配置...")
    
    # 先配置ACL和内部网络
    result = config_op.add_acl_rule(
        acl_number=2000,
        rule_number=5,
        action="permit",
        source="192.168.10.0 0.0.0.255"
    )
    
    if not result:
        print("ACL配置失败，无法继续测试出接口NAT")
        return False
    
    # 配置出接口NAT
    result = config_op.configure_nat(
        nat_type="dynamic",
        outside_interface="GigabitEthernet0/0/1",
        nat_params={
            "acl_number": 2000
        }
    )
    
    print(f"出接口NAT配置结果: {'成功' if result else '失败'}")
    return result

def test_nat_get_config(config_op):
    """测试获取NAT配置"""
    print("\n4. 测试获取NAT配置...")
    
    nat_config = config_op.get_nat_config()
    if nat_config is None:
        print("获取NAT配置失败")
        return False
        
    print("获取NAT配置成功")
    return True

def main():
    """主函数"""
    app = QCoreApplication(sys.argv)
    
    # 测试设备连接
    connection_result, config_op = test_connection()
    if not connection_result:
        print("设备连接测试失败，终止测试")
        return
    
    # 测试静态NAT
    static_result = test_nat_static(config_op)
    
    # 测试出接口NAT
    outbound_result = test_nat_outbound(config_op)
    
    # 测试获取NAT配置
    get_config_result = test_nat_get_config(config_op)
    
    # 总结
    print("\n==== NAT测试总结 ====")
    print(f"静态NAT配置: {'通过' if static_result else '失败'}")
    print(f"出接口NAT配置: {'通过' if outbound_result else '失败'}")
    print(f"获取NAT配置: {'通过' if get_config_result else '失败'}")
    print(f"整体测试: {'通过' if (static_result and outbound_result and get_config_result) else '失败'}")
    
    # 给信号处理留时间
    QCoreApplication.processEvents()
    time.sleep(1)

if __name__ == "__main__":
    main() 