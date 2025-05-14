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

def test_dynamic_nat(config_op):
    """测试动态NAT配置"""
    print("\n2. 测试动态NAT配置...")
    
    # 先配置ACL
    print("\n2.1 配置ACL...")
    acl_result = config_op.add_acl_rule(
        acl_number=2000,
        rule_number=5,
        action="permit",
        source="192.168.10.0 0.0.0.255"
    )
    
    print(f"ACL配置结果: {'成功' if acl_result else '失败'}")
    
    if not acl_result:
        return False
    
    # 测试动态NAT带force_clear参数
    print("\n2.2 配置动态NAT(带force_clear参数)...")
    result = config_op.configure_nat(
        nat_type="dynamic",
        outside_interface="GigabitEthernet0/0/1",
        nat_params={
            "acl_number": 2000
        },
        force_clear=True  # 强制清除接口现有NAT配置
    )
    
    print(f"动态NAT配置结果: {'成功' if result else '失败'}")
    
    return result

def verify_nat_config(config_op):
    """验证NAT配置"""
    print("\n3. 验证NAT配置...")
    
    # 连接设备
    if not config_op.connect_device():
        print("连接设备失败，无法验证NAT配置")
        return False
    
    # 检查接口配置
    print("\n3.1 检查接口配置...")
    try:
        # 进入系统视图
        config_op.connection.send_command("system-view", expect_string=r"\[.*\]")
        
        # 进入接口
        config_op.connection.send_command("interface GigabitEthernet0/0/1", expect_string=r"\[.*\]")
        
        # 查看接口配置
        output = config_op.connection.send_command("display this", expect_string=r"\[.*\]")
        print(f"接口配置:\n{output}")
        
        # 检查是否包含NAT配置
        if "nat outbound 2000" in output:
            print("成功验证NAT配置存在于接口")
            return True
        else:
            print("接口中未找到NAT配置")
            return False
            
    except Exception as e:
        print(f"验证过程出错: {str(e)}")
        return False
    finally:
        # 关闭连接
        if config_op.connection:
            try:
                config_op.connection.disconnect()
            except:
                pass
            config_op.connection = None

def main():
    """主函数"""
    app = QCoreApplication(sys.argv)
    
    # 测试设备连接
    connection_result, config_op = test_connection()
    if not connection_result:
        print("设备连接测试失败，终止测试")
        return
    
    # 测试动态NAT配置
    nat_result = test_dynamic_nat(config_op)
    
    # 验证NAT配置
    verify_result = verify_nat_config(config_op)
    
    # 总结
    print("\n==== 动态NAT测试总结 ====")
    print(f"动态NAT配置: {'通过' if nat_result else '失败'}")
    print(f"NAT配置验证: {'通过' if verify_result else '失败'}")
    print(f"整体测试: {'通过' if (nat_result and verify_result) else '失败'}")
    
    # 给信号处理留时间
    QCoreApplication.processEvents()
    time.sleep(1)

if __name__ == "__main__":
    main() 